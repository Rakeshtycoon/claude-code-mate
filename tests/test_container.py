"""Tests for the ``.ADV`` container parser using a synthetic file."""
import pytest

from advrecover.format import constants as C
from advrecover.format import AdvParseError, parse_bytes, parse_file


def test_parse_synthetic_header(synthetic_adv_bytes):
    doc = parse_bytes(synthetic_adv_bytes)
    assert doc.magic == C.ADV_MAGIC
    assert doc.version == 2
    assert doc.warnings == []


def test_parse_synthetic_sections(synthetic_adv_bytes):
    doc = parse_bytes(synthetic_adv_bytes)
    main = doc.section(1)
    assert main is not None
    assert main.guid == C.SECTION_MAIN_MODEL
    assert main.offset == 0x20


def test_parse_synthetic_metadata(synthetic_adv_file):
    doc = parse_file(synthetic_adv_file)
    mm = doc.main_model
    assert mm is not None
    assert mm.tag == 9
    assert mm.stone_id == "330-001(GA)(WH)"
    assert mm.scan_mode == "Accurate"
    assert mm.document_uuid == "11111111-2222-3333-4444-555555555555"
    assert "Saw1-1" in mm.planning_tree
    assert "Pie3-1" in mm.planning_tree
    assert mm.created is not None


def test_bad_magic_rejected():
    with pytest.raises(AdvParseError):
        parse_bytes(b"\x00" * 64)
