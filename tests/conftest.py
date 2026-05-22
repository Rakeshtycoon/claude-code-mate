"""Shared test fixtures.

No proprietary ``.ADV`` samples are committed; instead a structurally valid
synthetic ``.ADV`` file is built in memory so the parser, scanner and
exporter can be tested deterministically.
"""
from __future__ import annotations

import struct

import numpy as np
import pytest

from advrecover.format import constants as C

# A float that the geometry scanner rejects — used to separate runs.
_RUN_SEPARATOR = struct.pack("<I", 0x7FC00000)  # quiet NaN bit pattern


def _string(text: str) -> bytes:
    raw = text.encode("ascii")
    return struct.pack("<I", len(raw)) + raw


def build_synthetic_adv(stone_id: str = "330-001(GA)(WH)", run_count: int = 5,
                        points_per_run: int = 120) -> bytes:
    """Return bytes for a minimal but valid one-section ``.ADV`` file."""
    rng = np.random.default_rng(42)

    section = bytearray()
    section += C.SECTION_MAIN_MODEL.raw
    section += struct.pack("<III", 9, 61809, 2359)         # tag, const_a, const_b
    section += struct.pack("<Q", 132_000_000_000_000_000)  # FILETIME
    section += struct.pack("<I", 0xFFFFFFFF)               # sentinel
    for text in (stone_id, "DV", "P77-XX", "Accurate",
                 "11111111-2222-3333-4444-555555555555"):
        section += _string(text)
    # Proper 60-byte planning-element records, each followed by its name.
    for eid, (offset, normal, name) in enumerate([
        (1000.0, (0.0, 0.0, 1.0), "Saw1-1"),
        (-500.0, (0.6, 0.0, 0.8), "Pie3-1"),
        (250.0, (0.0, 1.0, 0.0), "Saw3-1"),
    ]):
        section += struct.pack("<II", 86, eid)
        section += struct.pack("<6d", 54.0, offset, 0.0, *normal)
        section += struct.pack("<I", 1)
        section += _string(name)

    # Pad to a 4-byte boundary so the float32 geometry stays word-aligned
    # (the section itself starts at the aligned offset 0x20).
    while len(section) % 4 != 0:
        section += b"\x80"

    # Coherent geometry: runs clustered near a diamond-scale centre (microns).
    centre = np.array([7000.0, -1700.0, 6400.0])
    for _ in range(run_count):
        pts = centre + rng.uniform(-600, 600, size=(points_per_run, 3))
        section += _RUN_SEPARATOR
        section += pts.astype("<f4").tobytes()
        section += _RUN_SEPARATOR

    directory_offset = 0x20 + len(section)
    directory = bytearray()
    directory += C.DIRECTORY_MAGIC.raw
    directory += struct.pack("<III", 0, 16, 1)             # flags, size, count
    directory += struct.pack("<III", 1, 0x20, 0)           # entry: id 1 @ 0x20

    header = bytearray()
    header += C.ADV_MAGIC.raw
    header += struct.pack("<IIII", 2, directory_offset, directory_offset, 0)

    return bytes(header) + bytes(section) + bytes(directory)


@pytest.fixture
def synthetic_adv_bytes() -> bytes:
    return build_synthetic_adv()


@pytest.fixture
def synthetic_adv_file(tmp_path, synthetic_adv_bytes) -> str:
    path = tmp_path / "synthetic.adv"
    path.write_bytes(synthetic_adv_bytes)
    return str(path)
