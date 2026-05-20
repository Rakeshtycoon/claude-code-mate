"""Marker-aware JPEG stream carver.

The .adv container stores every scan slice and preview as a complete JFIF
stream concatenated back-to-back (no length prefix). A naive
``find(b"\\xff\\xd8")`` / ``find(b"\\xff\\xd9")`` carver fails here because
``FF D8`` and ``FF D9`` byte pairs occur naturally inside entropy-coded
data. This module walks the JPEG marker grammar so each stream's exact
end is known.

Marker grammar implemented:
  * SOI (FFD8) / EOI (FFD9)             - standalone
  * TEM (FF01), RST0-7 (FFD0-D7)        - standalone
  * fill bytes (FF FF)                  - skipped
  * everything else                    - 2-byte big-endian segment length
  * SOS (FFDA)                          - header length, then entropy data
    scanned byte-wise (FF00 = stuffing, FFDn = restart, else next marker)
"""
from __future__ import annotations

from dataclasses import dataclass

SOI = b"\xff\xd8\xff"  # include the third byte: a valid SOI is always followed
                       # by another marker, which cuts most false positives.

# A real JFIF frame has exactly one SOF with sane geometry. These bounds
# reject FF-D8-FF byte pairs that occur by chance inside binary/voxel data.
_MAX_DIM = 16384
_VALID_COMPONENTS = (1, 3, 4)


@dataclass(frozen=True)
class JpegStream:
    """A located JPEG stream and whatever metadata could be decoded."""

    index: int
    offset: int
    length: int
    width: int | None = None
    height: int | None = None
    components: int | None = None
    valid: bool = True

    @property
    def end(self) -> int:
        return self.offset + self.length

    @property
    def kind(self) -> str:
        """Heuristic classification used by the .adv container parser."""
        if self.components == 1:
            return "grayscale"
        if self.components == 3:
            return "color"
        return "unknown"


def _segment_length(buf, p: int, end: int) -> int | None:
    if p + 4 > end:
        return None
    return (buf[p + 2] << 8) | buf[p + 3]


def scan_jpeg(buf, start: int, end: int | None = None) -> tuple[int, dict] | None:
    """Measure the JPEG stream beginning at ``start``.

    Returns ``(length, meta)`` where ``meta`` carries SOF dimensions, or
    ``None`` if ``start`` is not a real SOI. Never reads past ``end``.
    """
    if end is None:
        end = len(buf)
    if start + 2 > end or buf[start] != 0xFF or buf[start + 1] != 0xD8:
        return None

    meta: dict = {"width": None, "height": None, "components": None}
    p = start + 2
    while p + 1 < end:
        if buf[p] != 0xFF:
            # Re-sync: skip bytes until the next marker prefix.
            p += 1
            continue
        # Collapse runs of fill bytes (FF FF ... FF).
        while p + 1 < end and buf[p + 1] == 0xFF:
            p += 1
        if p + 1 >= end:
            break
        marker = buf[p + 1]

        if marker == 0xD9:  # EOI
            return p + 2 - start, meta
        if marker == 0x00:  # stuffed FF outside a scan: treat as data
            p += 2
            continue
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:  # TEM / RSTn
            p += 2
            continue

        seglen = _segment_length(buf, p, end)
        if seglen is None or seglen < 2:
            return None

        # SOFn frame headers carry the image geometry.
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            if p + 9 <= end:
                meta["height"] = (buf[p + 5] << 8) | buf[p + 6]
                meta["width"] = (buf[p + 7] << 8) | buf[p + 8]
                meta["components"] = buf[p + 9] if p + 9 < end else None

        if marker == 0xDA:  # SOS: header, then entropy-coded data
            p += 2 + seglen
            while p + 1 < end:
                if buf[p] == 0xFF:
                    nb = buf[p + 1]
                    if nb == 0x00 or 0xD0 <= nb <= 0xD7:
                        p += 2  # byte stuffing or restart marker -> still data
                        continue
                    if nb == 0xFF:
                        p += 1  # fill byte
                        continue
                    break  # a real marker terminates the scan
                p += 1
            continue

        p += 2 + seglen

    return None


def _sof_is_sane(meta: dict) -> bool:
    w, h, c = meta["width"], meta["height"], meta["components"]
    if w is None or h is None or c is None:
        return False
    if not (0 < w <= _MAX_DIM and 0 < h <= _MAX_DIM):
        return False
    return c in _VALID_COMPONENTS


def carve_all(buf, start: int = 0, end: int | None = None) -> list[JpegStream]:
    """Locate every well-formed JPEG stream in ``buf[start:end]``.

    Streams are returned in file order. A candidate is accepted only if the
    marker walk reaches an EOI *and* the frame carries a single sane SOF.
    ``FF D8 FF`` byte pairs that occur by chance inside voxel/binary data
    parse to garbage geometry and are skipped.
    """
    if end is None:
        end = len(buf)
    out: list[JpegStream] = []
    cursor = start
    idx = 0
    while True:
        soi = buf.find(SOI, cursor)
        if soi < 0 or soi >= end:
            break
        result = scan_jpeg(buf, soi, end)
        if result is None or not _sof_is_sane(result[1]):
            cursor = soi + 3  # false positive: step past this SOI marker
            continue
        length, meta = result
        out.append(
            JpegStream(
                index=idx,
                offset=soi,
                length=length,
                width=meta["width"],
                height=meta["height"],
                components=meta["components"],
            )
        )
        idx += 1
        cursor = soi + length
    return out
