"""Tests for the OBJ and STL exporters."""
import struct

from advrecover.export import write_obj, write_stl
from advrecover.format import parse_bytes
from advrecover.recon import reconstruct


def _result(adv_bytes):
    doc = parse_bytes(adv_bytes)
    return reconstruct(adv_bytes, doc, method="hull")


def test_obj_export(tmp_path, synthetic_adv_bytes):
    result = _result(synthetic_adv_bytes)
    path = tmp_path / "model.obj"
    write_obj(result, str(path))
    text = path.read_text()
    assert text.startswith("# ADV Planning Data Recovery")
    assert "mtllib model.mtl" in text
    assert text.count("\no ") >= 1            # at least one object group
    assert (tmp_path / "model.mtl").exists()


def test_stl_export_is_valid_binary(tmp_path, synthetic_adv_bytes):
    result = _result(synthetic_adv_bytes)
    path = tmp_path / "model.stl"
    write_stl(result, str(path))
    data = path.read_bytes()
    assert len(data) >= 84
    facet_count = struct.unpack_from("<I", data, 80)[0]
    assert len(data) == 84 + facet_count * 50   # exact binary-STL size
    assert facet_count > 0
