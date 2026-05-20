"""High-level parser for the proprietary ``.adv`` diamond-scan container.

Reverse-engineered layout (see ``docs/FORMAT.md`` for the full write-up).
The file is a serialised object graph produced by a diamond "galaxy"
scanner; it has no public spec. Verified structure:

  offset 0    16-byte class GUID
  offset 16   u32 version (observed: 2)
  offset 20   u32 filesize - 24
  offset 24   u32 filesize - 76
  offset 32   16-byte GUID
  offset 60   8-byte Windows FILETIME (scan timestamp)
  offset 68   f64 calibration scalar
  offset 76+  f64 AABB / transform slots (largely -1.0 sentinels)
  ...         u32-length-prefixed strings: job id, scan mode, UUID
  <body>      ~32 MB uncompressed high-entropy block (raw voxel/volume
              candidate - not yet fully decoded)
  <slices>    N JPEG streams, 1024x1280, grayscale  -> internal X-ray slices
  <mid>       intermediate binary block
  <thumbs>    ~200 JPEG streams, 98x98, RGB         -> multi-angle previews

Anything not positively identified is exposed as a raw region rather than
guessed at - this parser never fabricates structure.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

from advkit.core.binreader import BinaryReader, Region
from advkit.core.log import get_logger
from advkit.parsers.inspector import shannon_entropy
from advkit.parsers.jpeg import JpegStream, carve_all

_log = get_logger("adv")

# Windows FILETIME epoch (1601-01-01) to Unix epoch, in seconds.
_FILETIME_EPOCH_DELTA = 11644473600


def filetime_to_datetime(ft: int) -> _dt.datetime | None:
    """Convert a 64-bit Windows FILETIME to an aware UTC datetime."""
    if ft == 0 or ft == 0xFFFFFFFFFFFFFFFF:
        return None
    seconds = ft / 1e7 - _FILETIME_EPOCH_DELTA
    try:
        return _dt.datetime.fromtimestamp(seconds, tz=_dt.timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


@dataclass
class AdvHeader:
    """Decoded fixed-position header fields."""

    class_guid: str
    version: int
    size_field_1: int
    size_field_2: int
    secondary_guid: str
    scan_time: _dt.datetime | None
    calibration: float
    strings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "class_guid": self.class_guid,
            "version": self.version,
            "size_field_1": self.size_field_1,
            "size_field_2": self.size_field_2,
            "secondary_guid": self.secondary_guid,
            "scan_time": self.scan_time.isoformat() if self.scan_time else None,
            "calibration": self.calibration,
            "strings": self.strings,
        }


def _scan_length_prefixed_strings(reader: BinaryReader, start: int, end: int,
                                  min_len: int = 3, max_len: int = 128) -> list[str]:
    """Find u32-length-prefixed printable strings in ``[start, end)``.

    The header stores the job id / scan mode / UUID this way but at
    revision-dependent offsets, so they are discovered rather than hard-coded.
    """
    found: list[str] = []
    buf = reader.buffer
    off = start
    while off < end - 4:
        n = reader.u32(off)
        if min_len <= n <= max_len and off + 4 + n <= end:
            raw = bytes(buf[off + 4:off + 4 + n])
            if all(32 <= b < 127 for b in raw):
                found.append(raw.decode("ascii"))
                off += 4 + n
                continue
        off += 1
    return found


@dataclass
class AdvSlice:
    """One internal X-ray scan slice (a JPEG stream inside the container)."""

    index: int
    offset: int
    length: int
    width: int
    height: int
    valid: bool = True


class AdvFile:
    """Parsed view of a ``.adv`` container.

    Construction is cheap: the body is memory-mapped and only the marker
    table is walked. Pixel data is decoded lazily per slice.
    """

    SLICE_DIMS = (1024, 1280)
    THUMB_DIMS = (98, 98)

    def __init__(self, reader: BinaryReader):
        self.reader = reader
        self.path = reader.path
        self.size = reader.size
        self.header = self._parse_header()
        self._streams: list[JpegStream] = carve_all(reader.buffer)
        self.sections: list[Region] = []
        self.slices: list[AdvSlice] = []
        self.thumbnails: list[JpegStream] = []
        self._classify()

    # -- construction helpers ---------------------------------------------
    @classmethod
    def open(cls, path: str) -> "AdvFile":
        return cls(BinaryReader(path))

    def close(self) -> None:
        self.reader.close()

    def __enter__(self) -> "AdvFile":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- header ------------------------------------------------------------
    def _parse_header(self) -> AdvHeader:
        r = self.reader
        if r.size < 256:
            raise ValueError("file too small to be a valid .adv container")
        strings = _scan_length_prefixed_strings(r, 64, min(8192, r.size))
        return AdvHeader(
            class_guid=r.guid(0),
            version=r.u32(16),
            size_field_1=r.u32(20),
            size_field_2=r.u32(24),
            secondary_guid=r.guid(32),
            scan_time=filetime_to_datetime(r.u64(60)),
            calibration=r.f64(68),
            strings=strings,
        )

    # -- section classification ------------------------------------------
    def _classify(self) -> None:
        grays = [s for s in self._streams
                 if s.components == 1 and (s.width, s.height) == self.SLICE_DIMS]
        colors = [s for s in self._streams if s.components == 3]

        for i, s in enumerate(grays):
            self.slices.append(
                AdvSlice(i, s.offset, s.length, s.width, s.height,
                         valid=self._stream_decodes(s))
            )
        self.thumbnails = colors

        regions: list[Region] = []
        if grays:
            first = grays[0].offset
            regions.append(Region("header+body", 0, first, kind="raw",
                                   note="header + uncompressed volume-candidate block"))
            regions.append(Region("xray_slices", first, grays[-1].end,
                                   kind="jpeg-run",
                                   note=f"{len(grays)} grayscale 1024x1280 X-ray slices"))
            mid_start = grays[-1].end
        else:
            regions.append(Region("body", 0, self.size, kind="raw"))
            mid_start = self.size

        if colors:
            tstart = colors[0].offset
            if tstart > mid_start:
                regions.append(Region("intermediate", mid_start, tstart,
                                       kind="raw", note="undecoded binary block"))
            regions.append(Region("preview_thumbnails", tstart, colors[-1].end,
                                   kind="jpeg-run",
                                   note=f"{len(colors)} RGB 98x98 preview images"))
            if colors[-1].end < self.size:
                regions.append(Region("trailer", colors[-1].end, self.size,
                                       kind="raw"))
        elif mid_start < self.size:
            regions.append(Region("intermediate", mid_start, self.size, kind="raw"))
        self.sections = regions

    def _stream_decodes(self, stream: JpegStream) -> bool:
        """True if PIL can fully decode the stream (corruption check)."""
        try:
            import io
            from PIL import Image
            im = Image.open(io.BytesIO(self.reader.slice(stream.offset, stream.length)))
            im.load()
            return True
        except Exception:  # noqa: BLE001 - corruption is expected & reported
            return False

    # -- accessors ---------------------------------------------------------
    @property
    def slice_count(self) -> int:
        return len(self.slices)

    @property
    def damaged_slices(self) -> list[int]:
        return [s.index for s in self.slices if not s.valid]

    def slice_bytes(self, index: int) -> bytes:
        """Raw JPEG bytes of slice ``index``."""
        s = self.slices[index]
        return self.reader.slice(s.offset, s.length)

    def slice_image(self, index: int):
        """Decoded :class:`PIL.Image` of slice ``index`` (mode ``L``)."""
        import io
        from PIL import Image
        return Image.open(io.BytesIO(self.slice_bytes(index)))

    def thumbnail_bytes(self, index: int) -> bytes:
        t = self.thumbnails[index]
        return self.reader.slice(t.offset, t.length)

    def section(self, name: str) -> Region | None:
        for s in self.sections:
            if s.name == name:
                return s
        return None

    def region_entropy(self, region: Region, sample: int = 262144) -> float:
        """Entropy of the first ``sample`` bytes of ``region``."""
        return shannon_entropy(self.reader.slice(region.start,
                                                 min(sample, region.size)))

    def summary(self) -> dict:
        """Machine-readable structural summary (used by the CLI report)."""
        return {
            "path": self.path,
            "size": self.size,
            "header": self.header.as_dict(),
            "slice_count": self.slice_count,
            "damaged_slices": self.damaged_slices,
            "thumbnail_count": len(self.thumbnails),
            "sections": [
                {
                    "name": s.name,
                    "start": s.start,
                    "end": s.end,
                    "size": s.size,
                    "kind": s.kind,
                    "note": s.note,
                }
                for s in self.sections
            ],
        }
