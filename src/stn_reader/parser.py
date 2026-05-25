"""Parser for .stn (CAD/3D) files.

This is a scaffolding stub. Replace the body of :func:`parse_stn_file`
with real parsing once the on-disk format is pinned down.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class StnModel:
    """In-memory representation of a parsed .stn file."""

    source_path: Path
    byte_size: int
    header: bytes = b""
    vertices: list[tuple[float, float, float]] = field(default_factory=list)
    faces: list[tuple[int, ...]] = field(default_factory=list)


class StnParseError(Exception):
    """Raised when a .stn file cannot be parsed."""


def parse_stn_file(path: str | Path) -> StnModel:
    file_path = Path(path)
    if not file_path.is_file():
        raise StnParseError(f"Not a file: {file_path}")

    data = file_path.read_bytes()
    return StnModel(
        source_path=file_path,
        byte_size=len(data),
        header=data[:16],
    )
