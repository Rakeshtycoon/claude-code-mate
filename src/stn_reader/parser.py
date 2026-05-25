"""Parser for .stn (Stone-produced CAD/3D scan) files.

The .stn format has been partially reverse-engineered from sample files:

* Magic number at offset 0  ........... uint32 LE = 0x00000937
* Bounding-box / scaling doubles ..... offsets 16..96
* Header counts ...................... offsets 48, 56 (small dimensions)
* Format constant .................... offset 52 = 61200
* Length-prefixed part number ........ offset 213 (len) + 217 (chars)
* Length-prefixed quality tag ........ offset 237 (len) + 241 (chars)
* Producer metadata (StoneTextualData) embedded as trailing
  '(StoneTextualData: ...Date dd.mm.yyyy hh:mm:ss Version:x.y.z.b)'
  records near the file tail.
* Mesh body: quantized 16-bit heightfield, sentinel 0x6F7D = no-data.

The body decoder is not yet finalised - this module surfaces every header
field that is currently understood so the viewer has real information to
show, and stubs out the dense mesh extraction.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from pathlib import Path

STN_MAGIC = 0x00000937
NO_DATA_SENTINEL_U16 = 0x6F7D

_PART_NUMBER_LEN_OFFSET = 213
_PART_NUMBER_DATA_OFFSET = 217
_QUALITY_LEN_OFFSET = 237
_QUALITY_DATA_OFFSET = 241

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
class StnModel:
    source_path: Path
    byte_size: int
    header: StnHeader
    metadata: StnMetadata
    body_offset: int
    body_size: int

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
    file_id = struct.unpack_from("<I", data, 4)[0]
    creation_marker = struct.unpack_from("<I", data, 8)[0]
    scale_factor = struct.unpack_from("<d", data, 16)[0]
    width_count = struct.unpack_from("<I", data, 48)[0]
    constant_61200 = struct.unpack_from("<I", data, 52)[0]
    height_count = struct.unpack_from("<I", data, 56)[0]
    return StnHeader(
        magic=magic,
        file_id=file_id,
        creation_marker=creation_marker,
        scale_factor=scale_factor,
        width_count=width_count,
        constant_61200=constant_61200,
        height_count=height_count,
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


def parse_stn_file(path: str | Path) -> StnModel:
    file_path = Path(path)
    if not file_path.is_file():
        raise StnParseError(f"Not a file: {file_path}")

    data = file_path.read_bytes()
    header = _parse_header(data)
    metadata = _parse_metadata(data)

    body_offset = 256
    body_size = max(0, len(data) - body_offset)

    return StnModel(
        source_path=file_path,
        byte_size=len(data),
        header=header,
        metadata=metadata,
        body_offset=body_offset,
        body_size=body_size,
    )


def extract_heightfield_preview(
    data: bytes, max_samples: int = 65536
) -> list[int]:
    """Best-effort decode of the quantised 16-bit body.

    Returns a flat list of u16 samples with the no-data sentinel masked out.
    The exact grid dimensions are not yet known, so the caller should treat
    the result as a 1-D signal for now.
    """
    body = data[256:]
    sample_count = min(len(body) // 2, max_samples)
    samples = struct.unpack_from(f"<{sample_count}H", body, 0)
    return [s for s in samples if s != NO_DATA_SENTINEL_U16]
