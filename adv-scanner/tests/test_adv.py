"""Tests for the .adv container parser."""
import datetime as dt

import pytest

from advkit.parsers.adv import AdvFile, filetime_to_datetime


def test_filetime_conversion():
    ft = int((1704067200 + 11644473600) * 1e7)  # 2024-01-01T00:00:00Z
    parsed = filetime_to_datetime(ft)
    assert parsed == dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)
    assert filetime_to_datetime(0) is None
    assert filetime_to_datetime(0xFFFFFFFFFFFFFFFF) is None


def test_header_fields(synthetic_adv_path):
    with AdvFile.open(synthetic_adv_path) as adv:
        h = adv.header
        assert h.version == 2
        assert h.size_field_1 == adv.size - 24
        assert h.size_field_2 == adv.size - 76
        assert abs(h.calibration - 1.842) < 1e-9
        assert h.scan_time.year == 2024
        assert "168001688475" in h.strings
        assert "Fast" in h.strings


def test_section_classification(synthetic_adv_path):
    with AdvFile.open(synthetic_adv_path) as adv:
        names = [s.name for s in adv.sections]
        assert "xray_slices" in names
        assert "preview_thumbnails" in names
        # sections must tile the file with no overlap and in order
        for a, b in zip(adv.sections, adv.sections[1:]):
            assert a.end == b.start
        assert adv.sections[0].start == 0
        assert adv.sections[-1].end == adv.size


def test_slice_and_thumbnail_counts(synthetic_adv_path):
    with AdvFile.open(synthetic_adv_path) as adv:
        assert adv.slice_count == 4
        assert len(adv.thumbnails) == 3
        assert adv.damaged_slices == []


def test_slice_decoding(synthetic_adv_path):
    with AdvFile.open(synthetic_adv_path) as adv:
        img = adv.slice_image(0)
        assert img.size == (1024, 1280)


def test_summary_is_serialisable(synthetic_adv_path):
    import json
    with AdvFile.open(synthetic_adv_path) as adv:
        json.dumps(adv.summary(), default=str)  # must not raise


def test_rejects_tiny_file(tmp_path):
    bad = tmp_path / "tiny.adv"
    bad.write_bytes(b"\x00" * 32)
    with pytest.raises(ValueError):
        AdvFile.open(str(bad))


def test_real_file_structure(real_adv_path):
    with AdvFile.open(real_adv_path) as adv:
        assert adv.slice_count > 100
        assert adv.header.version >= 1
        assert adv.sections[0].start == 0
