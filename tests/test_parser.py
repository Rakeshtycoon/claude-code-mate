import struct
from pathlib import Path

import numpy as np
import pytest

from stn_reader.parser import (
    NO_DATA_SENTINEL_U16,
    STN_MAGIC,
    StnParseError,
    decode_heightfield,
    extract_heightfield_preview,
    parse_stn_file,
)


SAMPLES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_FILE = SAMPLES_DIR / "sample.stn"


def test_parse_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(StnParseError):
        parse_stn_file(tmp_path / "does-not-exist.stn")


def test_parse_rejects_non_stn(tmp_path: Path) -> None:
    bad = tmp_path / "bad.stn"
    bad.write_bytes(b"NOTASTN" + b"\x00" * 100)
    with pytest.raises(StnParseError, match="Bad magic"):
        parse_stn_file(bad)


def _make_synthetic_stn(tmp_path: Path, with_chunks: bool = True) -> Path:
    """Build a minimal valid .stn-shaped buffer for offline testing."""
    buf = bytearray(512)
    struct.pack_into("<I", buf, 0, STN_MAGIC)
    struct.pack_into("<I", buf, 4, 0x12345678)
    struct.pack_into("<I", buf, 8, 0x01DCC461)
    struct.pack_into("<d", buf, 16, 0.5)
    struct.pack_into("<I", buf, 48, 306)
    struct.pack_into("<I", buf, 52, 61200)
    struct.pack_into("<I", buf, 56, 350)

    part = b"TEST-0001"
    struct.pack_into("<I", buf, 213, len(part))
    buf[217 : 217 + len(part)] = part

    quality = b"Most Accurate"
    struct.pack_into("<I", buf, 237, len(quality))
    buf[241 : 241 + len(quality)] = quality

    # A few u16 height samples (one is the sentinel).
    samples = bytearray()
    for v in (1000, 2000, NO_DATA_SENTINEL_U16, 3000, 4000):
        samples += struct.pack("<H", v)
    buf[350 : 350 + len(samples)] = samples

    if with_chunks:
        # Two synthetic float chunks of 3 and 2 points.
        chunk1 = (
            struct.pack("<H", 0x42CC)
            + b"\xfc\xff\x01"
            + struct.pack("<I", 3)
            + struct.pack("<9f", 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0)
        )
        chunk2 = (
            struct.pack("<H", 0x4B14)
            + b"\xfc\xff\x01"
            + struct.pack("<I", 2)
            + struct.pack("<6f", 10.0, 11.0, 12.0, 13.0, 14.0, 15.0)
        )
        buf.extend(chunk1)
        buf.extend(chunk2)

    tag = b"(StoneTextualData: PrivateBuild 1 Date 01.01.2026 00:00:00 Version:5.3.0.165)"
    buf.extend(tag)

    path = tmp_path / "synthetic.stn"
    path.write_bytes(buf)
    return path


def test_parse_synthetic_header(tmp_path: Path) -> None:
    path = _make_synthetic_stn(tmp_path)
    model = parse_stn_file(path)

    assert model.is_valid
    assert model.header.magic == STN_MAGIC
    assert model.header.width_count == 306
    assert model.header.height_count == 350
    assert model.header.constant_61200 == 61200
    assert model.metadata.part_number == "TEST-0001"
    assert model.metadata.quality_tag == "Most Accurate"
    assert model.metadata.producer_version == "5.3.0.165"
    assert model.metadata.producer_dates == ["01.01.2026 00:00:00"]


def test_parse_synthetic_point_cloud(tmp_path: Path) -> None:
    path = _make_synthetic_stn(tmp_path)
    model = parse_stn_file(path)

    assert model.point_cloud.chunk_count == 2
    assert model.point_cloud.point_count == 5
    np.testing.assert_array_equal(
        model.point_cloud.points[0], np.array([1.0, 2.0, 3.0], dtype=np.float32)
    )
    np.testing.assert_array_equal(
        model.point_cloud.points[-1], np.array([13.0, 14.0, 15.0], dtype=np.float32)
    )


def test_parse_no_chunks(tmp_path: Path) -> None:
    path = _make_synthetic_stn(tmp_path, with_chunks=False)
    model = parse_stn_file(path)
    assert model.point_cloud.chunk_count == 0
    assert model.point_cloud.point_count == 0


def test_heightfield_preview_masks_sentinel_and_zero() -> None:
    body = struct.pack(
        f"<{6}H", 100, 200, NO_DATA_SENTINEL_U16, 300, 0, 400
    )
    data = b"\x00" * 351 + body
    samples = extract_heightfield_preview(data)
    assert samples == [100, 200, 300, 400]


def test_decode_heightfield_converts_no_data_to_nan() -> None:
    body = struct.pack("<5H", 100, NO_DATA_SENTINEL_U16, 300, 0, 500)
    data = b"\x00" * 351 + body
    out = decode_heightfield(data, 351, len(body))
    assert out[0] == 100
    assert np.isnan(out[1])
    assert out[2] == 300
    assert np.isnan(out[3])
    assert out[4] == 500


@pytest.mark.skipif(not SAMPLE_FILE.exists(), reason="real sample fixture not present")
def test_parse_real_sample() -> None:
    model = parse_stn_file(SAMPLE_FILE)
    assert model.is_valid
    assert model.metadata.part_number != ""
    assert model.metadata.quality_tag == "Most Accurate"
    assert model.metadata.producer_version.startswith("5.")

    # Every sample file in the wild has exactly 32 chunks.
    assert model.point_cloud.chunk_count == 32
    assert 1000 < model.point_cloud.point_count < 20000
    # Coordinates should be plausible mm values.
    xmin, xmax, ymin, ymax, zmin, zmax = model.point_cloud.bounds
    assert -2000 < xmin < xmax < 20000
    assert -5000 < ymin < ymax < 5000
    assert -1000 < zmin < zmax < 20000
