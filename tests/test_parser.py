import struct
from pathlib import Path

import pytest

from stn_reader.parser import (
    NO_DATA_SENTINEL_U16,
    STN_MAGIC,
    StnParseError,
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


def _make_synthetic_stn(tmp_path: Path) -> Path:
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


def test_heightfield_preview_masks_sentinel() -> None:
    body = struct.pack(
        f"<{6}H", 100, 200, NO_DATA_SENTINEL_U16, 300, NO_DATA_SENTINEL_U16, 400
    )
    data = b"\x00" * 256 + body
    samples = extract_heightfield_preview(data)
    assert samples == [100, 200, 300, 400]


@pytest.mark.skipif(not SAMPLE_FILE.exists(), reason="real sample fixture not present")
def test_parse_real_sample() -> None:
    model = parse_stn_file(SAMPLE_FILE)
    assert model.is_valid
    assert model.metadata.part_number != ""
    assert model.metadata.quality_tag == "Most Accurate"
    assert model.metadata.producer_version.startswith("5.")
    assert model.byte_size > 100_000
