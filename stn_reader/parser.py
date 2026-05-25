"""Parser for .stn (Stone-produced 3D scan) files.

Reverse-engineered from sample files produced by Stone v5.3.0.165:

* Magic number at offset 0 ............ uint32 LE = 0x00000937
* Scale factor ........................ float64 at offset 16
* Header dimensions ................... uint32 at offsets 48 and 56
* Format constant ..................... uint32 at offset 52 = 61200
* Length-prefixed part number ......... offset 213 (len) + 217 (chars)
* Length-prefixed quality tag ......... offset 237 (len) + 241 (chars)
* Quantised u16 heightfield ........... starts around offset 350; the
  value 0x6F7D marks a no-data pixel.  This is the bulk-data region.
* Float32 XYZ point-cloud chunks ...... a run of contiguous chunks near
  the tail; each chunk uses the layout::

      uint16   chunk index / id        (2 bytes)
      uint16   constant marker 0xFFFC  (2 bytes)
      uint8    constant marker 0x01    (1 byte)
      uint32   point count N           (4 bytes, little endian)
      float32  xyz[N]                  (N * 12 bytes)

  All four sample files contain exactly 32 such chunks (4-8 K points
  total), describing scan edges / key feature contours in real world
  millimetre coordinates.
* Producer metadata trailer ........... ASCII records of the form
  ``(StoneTextualData: PrivateBuild N Date d.m.y h:m:s Version:x.y.z.b)``.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

STN_MAGIC = 0x00000937
NO_DATA_SENTINEL_U16 = 0x6F7D

_HEIGHTFIELD_START = 350
_CHUNK_MARKER = b"\xfc\xff\x01"
_CHUNK_MIN_COUNT = 1
_CHUNK_MAX_COUNT = 5000

_PART_NUMBER_LEN_OFFSET = 213
_QUALITY_LEN_OFFSET = 237

_PRODUCER_RE = re.compile(
    rb"\(StoneTextualData:[^)]{0,256}Version:([0-9.]+)\)"
)
_DATE_RE = re.compile(
    rb"Date\s+(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2}:\d{2})"
)


@dataclass
class StnHeader:
    magic: int
    file_id: int
    creation_marker: int
    scale_factor: float
    width_count: int
    constant_61200: int
    height_count: int
    raw: bytes


@dataclass
class StnMetadata:
    part_number: str = ""
    quality_tag: str = ""
    producer_version: str = ""
    producer_dates: list[str] = field(default_factory=list)


@dataclass
class StnPointCloud:
    """The float32 XYZ chunk section near the file tail."""

    points: np.ndarray  # shape (N, 3), float32
    chunk_count: int
    region_start: int
    region_end: int

    @property
    def point_count(self) -> int:
        return int(self.points.shape[0])

    @property
    def bounds(self) -> tuple[float, float, float, float, float, float]:
        if self.points.size == 0:
            return (0.0,) * 6
        mn = self.points.min(axis=0)
        mx = self.points.max(axis=0)
        return (
            float(mn[0]), float(mx[0]),
            float(mn[1]), float(mx[1]),
            float(mn[2]), float(mx[2]),
        )


@dataclass
class StnModel:
    source_path: Path
    byte_size: int
    header: StnHeader
    metadata: StnMetadata
    heightfield_offset: int
    heightfield_size: int
    point_cloud: StnPointCloud

    @property
    def is_valid(self) -> bool:
        return self.header.magic == STN_MAGIC


class StnParseError(Exception):
    """Raised when a .stn file cannot be parsed."""


def _read_length_prefixed_string(data: bytes, len_offset: int) -> str:
    if len_offset + 4 > len(data):
        return ""
    length = struct.unpack_from("<I", data, len_offset)[0]
    if length == 0 or length > 128:
        return ""
    start = len_offset + 4
    end = start + length
    if end > len(data):
        return ""
    return data[start:end].decode("latin-1", errors="replace")


def _parse_header(data: bytes) -> StnHeader:
    if len(data) < 96:
        raise StnParseError("File too small to be a .stn (header truncated).")
    magic = struct.unpack_from("<I", data, 0)[0]
    if magic != STN_MAGIC:
        raise StnParseError(
            f"Bad magic: got 0x{magic:08x}, expected 0x{STN_MAGIC:08x}."
        )
    return StnHeader(
        magic=magic,
        file_id=struct.unpack_from("<I", data, 4)[0],
        creation_marker=struct.unpack_from("<I", data, 8)[0],
        scale_factor=struct.unpack_from("<d", data, 16)[0],
        width_count=struct.unpack_from("<I", data, 48)[0],
        constant_61200=struct.unpack_from("<I", data, 52)[0],
        height_count=struct.unpack_from("<I", data, 56)[0],
        raw=data[:96],
    )


def _parse_metadata(data: bytes) -> StnMetadata:
    meta = StnMetadata()
    meta.part_number = _read_length_prefixed_string(data, _PART_NUMBER_LEN_OFFSET)
    meta.quality_tag = _read_length_prefixed_string(data, _QUALITY_LEN_OFFSET)
    producers = _PRODUCER_RE.findall(data)
    if producers:
        meta.producer_version = producers[-1].decode("ascii", "replace")
    for date_m in _DATE_RE.finditer(data):
        meta.producer_dates.append(
            f"{date_m.group(1).decode()} {date_m.group(2).decode()}"
        )
    return meta


def _extract_point_cloud(data: bytes) -> StnPointCloud:
    """Find every float32 XYZ chunk and concatenate them into one array."""
    arrays: list[np.ndarray] = []
    chunk_count = 0
    first_off = len(data)
    last_end = 0

    pos = 0
    while True:
        idx = data.find(_CHUNK_MARKER, pos)
        if idx < 0:
            break
        header_start = idx - 2
        count_off = idx + len(_CHUNK_MARKER)
        if header_start < 0 or count_off + 4 > len(data):
            pos = idx + 1
            continue
        count = struct.unpack_from("<I", data, count_off)[0]
        if not (_CHUNK_MIN_COUNT <= count <= _CHUNK_MAX_COUNT):
            pos = idx + 1
            continue
        pts_start = count_off + 4
        pts_end = pts_start + count * 12
        if pts_end > len(data):
            pos = idx + 1
            continue
        # Sanity-check the first triplet so we ignore stray marker matches.
        sample = struct.unpack_from("<3f", data, pts_start)
        if not all(_finite_and_small(v) for v in sample):
            pos = idx + 1
            continue

        chunk = np.frombuffer(
            data[pts_start:pts_end], dtype="<f4"
        ).reshape(-1, 3)
        arrays.append(chunk)
        chunk_count += 1
        if header_start < first_off:
            first_off = header_start
        last_end = pts_end
        pos = pts_end

    if arrays:
        points = np.concatenate(arrays, axis=0).astype(np.float32, copy=False)
    else:
        points = np.zeros((0, 3), dtype=np.float32)
        first_off = 0
        last_end = 0

    return StnPointCloud(
        points=points,
        chunk_count=chunk_count,
        region_start=first_off,
        region_end=last_end,
    )


def _finite_and_small(value: float) -> bool:
    return (
        value == value  # not NaN
        and -1e6 < value < 1e6
        and (value == 0.0 or abs(value) > 1e-6)
    )


def parse_stn_file(path: str | Path) -> StnModel:
    file_path = Path(path)
    if not file_path.is_file():
        raise StnParseError(f"Not a file: {file_path}")

    data = file_path.read_bytes()
    header = _parse_header(data)
    metadata = _parse_metadata(data)
    pc = _extract_point_cloud(data)

    hf_end = pc.region_start if pc.point_count > 0 else len(data)
    hf_offset = _HEIGHTFIELD_START
    hf_size = max(0, hf_end - hf_offset)

    return StnModel(
        source_path=file_path,
        byte_size=len(data),
        header=header,
        metadata=metadata,
        heightfield_offset=hf_offset,
        heightfield_size=hf_size,
        point_cloud=pc,
    )


def decode_heightfield(
    data: bytes, offset: int, size: int, max_samples: int = 1_500_000
) -> np.ndarray:
    """Decode the quantised u16 heightfield region into a 1-D array.

    The sentinel value 0x6F7D is converted to NaN. Caller decides how to
    reshape the result (the exact 2-D layout is still being confirmed).
    """
    end = min(offset + size, len(data))
    end -= (end - offset) % 2  # u16 alignment
    raw = data[offset:end]
    n = min(len(raw) // 2, max_samples)
    samples = np.frombuffer(raw[: n * 2], dtype="<u2").astype(np.float32)
    samples[samples == NO_DATA_SENTINEL_U16] = np.nan
    return samples


# Backwards-compat helper kept for tests.
def extract_heightfield_preview(
    data: bytes, max_samples: int = 65536
) -> list[int]:
    body_offset = _HEIGHTFIELD_START
    end = min(len(data), body_offset + max_samples * 2)
    end -= (end - body_offset) % 2
    raw = data[body_offset:end]
    samples = np.frombuffer(raw, dtype="<u2")
    return samples[samples != NO_DATA_SENTINEL_U16].tolist()
