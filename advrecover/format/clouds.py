"""Decoder for the labeled 3-D point clouds in ``section[1]``.

The ``main_model`` section turned out to be a concatenation of standalone
ZIP archives (one ZIP per "ZippedData" record). Each decompressed record
holds:

* a label string  -- ``Cloud<N> - (3D)`` for surface patches that belong
  to planning elements (saw cuts, planned-stone facets) or ``Inc<N> - (3D)``
  for scanned inclusion meshes;
* a class GUID ``89B2F295-9627-483B-A7A2-00CBA02F27AB`` marking each
  attached sub-mesh (often repeated as LOD levels);
* per sub-mesh: ``u32`` version, ``u32`` format tag, ``u32`` vertex count,
  then ``count * 3 * f64`` coordinates in microns.

Coordinates are expressed in the diamond's local frame, in microns.
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field

import numpy as np

from .constants import MICRONS_PER_MM, NESTED_CLOUD, ZIP_LFH_MAGIC
from .model import AdvDocument


@dataclass
class CloudEntry:
    """One labeled 3-D point cloud decoded from ``section[1]``."""

    name: str
    kind: str                       # "cloud" | "inclusion" | "other"
    vertices: np.ndarray            # (N, 3) float64 in MICRONS
    file_offset: int = 0            # absolute file offset of the ZIP LFH
    lod_levels: tuple[int, ...] = ()  # vertex counts of each LOD chain entry

    @property
    def vertices_mm(self) -> np.ndarray:
        return self.vertices / MICRONS_PER_MM

    @property
    def is_empty(self) -> bool:
        return len(self.vertices) == 0

    @property
    def element_id(self) -> int | None:
        """The numeric id parsed out of names like ``Cloud520 - (3D)``."""
        digits = "".join(c for c in self.name.split(" - ")[0] if c.isdigit())
        return int(digits) if digits else None


# Pre-built GUID byte pattern (Microsoft GUID binary form, LE-swapped fields)
_GUID_BYTES = bytes.fromhex("95f2b28927963b48a7a200cba02f27ab")
assert NESTED_CLOUD  # keeps the import alive; constants used in docs

# Limits used for sanity-checking decoded records.
_MAX_LABEL_LEN = 256
_MAX_VERT_COUNT = 200_000
_MAX_ABS_COORD_UM = 50_000.0          # 50 mm; diamonds are at most ~10 mm
_MIN_VERT_COUNT = 3


def _iter_zip_records(blob: bytes):
    """Yield ``(zip_local_offset, decompressed_bytes)`` for each ZIP archive."""
    pos = 0
    while True:
        p = blob.find(ZIP_LFH_MAGIC, pos)
        if p < 0:
            return
        try:
            (_, _, _, comp, _, _, _, csz, _, nlen, xlen) = struct.unpack_from(
                "<IHHHHHIIIHH", blob, p)
            data_off = p + 30 + nlen + xlen
            if data_off + csz > len(blob):
                pos = p + 1
                continue
            payload = blob[data_off:data_off + csz]
            decoded = zlib.decompress(payload, -15) if comp == 8 else payload
            yield p, decoded
        except (struct.error, zlib.error):
            pass
        pos = p + 1


def _parse_record(blob: bytes) -> tuple[str, list[tuple[int, int, np.ndarray]]] | None:
    """Parse one decompressed ZippedData blob.

    Returns ``(label, [(count, tag, vertices), ...])`` ordered by descending
    vertex count, or ``None`` if the blob does not look like a cloud record.
    """
    if len(blob) < 36:
        return None
    marker = struct.unpack_from("<I", blob, 0)[0]
    if marker != 1:
        return None
    pos = 32                                                  # skip header
    if pos + 4 > len(blob):
        return None
    n = struct.unpack_from("<I", blob, pos)[0]
    if not 1 <= n <= _MAX_LABEL_LEN or pos + 4 + n > len(blob):
        return None
    try:
        label = blob[pos + 4:pos + 4 + n].decode("ascii")
    except UnicodeDecodeError:
        return None
    if not label.isprintable():
        return None

    sub_meshes: list[tuple[int, int, np.ndarray]] = []
    p_search = pos + 4 + n
    while p_search < len(blob):
        g = blob.find(_GUID_BYTES, p_search)
        if g < 0:
            break
        h = g + 16
        if h + 12 > len(blob):
            break
        try:
            ver, tag, count = struct.unpack_from("<3I", blob, h)
        except struct.error:
            break
        start = h + 12
        if _MIN_VERT_COUNT <= count <= _MAX_VERT_COUNT and \
                start + count * 24 <= len(blob):
            arr = np.frombuffer(blob[start:start + count * 24],
                                dtype="<f8").reshape(-1, 3)
            if np.all(np.isfinite(arr)) and \
                    np.all(np.abs(arr) < _MAX_ABS_COORD_UM):
                sub_meshes.append((count, tag, arr.copy()))
        p_search = g + 1

    sub_meshes.sort(key=lambda m: -m[0])
    return (label, sub_meshes)


def _classify(label: str) -> str:
    if label.startswith("Cloud"):
        return "cloud"
    if label.startswith("Inc"):
        return "inclusion"
    return "other"


def extract_clouds(data: bytes, doc: AdvDocument) -> list[CloudEntry]:
    """Decode all labeled point clouds from ``section[1]`` of ``doc``.

    Returns one :class:`CloudEntry` per labeled record; entries with no
    decoded sub-mesh are skipped. Vertex coordinates are returned in
    microns in the diamond's local frame (same units as the planning
    element offsets, so they live in the same coordinate system).
    """
    section = doc.section(1)
    if section is None:
        return []
    blob = data[section.offset:section.end]
    entries: list[CloudEntry] = []
    for zip_off, decoded in _iter_zip_records(blob):
        parsed = _parse_record(decoded)
        if parsed is None:
            continue
        label, sub_meshes = parsed
        if not sub_meshes:
            continue
        primary = sub_meshes[0][2]
        entries.append(CloudEntry(
            name=label,
            kind=_classify(label),
            vertices=primary,
            file_offset=section.offset + zip_off,
            lod_levels=tuple(m[0] for m in sub_meshes),
        ))
    return entries
