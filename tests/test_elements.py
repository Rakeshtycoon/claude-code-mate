"""Tests for planning-element decoding and parametric reconstruction."""
from advrecover.format import parse_bytes
from advrecover.format.elements import parse_elements
from advrecover.recon.planning import list_solutions, reconstruct_planning


def test_parse_elements_decodes_records(synthetic_adv_bytes):
    doc = parse_bytes(synthetic_adv_bytes)
    elements = parse_elements(synthetic_adv_bytes, doc)
    assert len(elements) == 3
    names = {e.name for e in elements}
    assert names == {"Saw1-1", "Pie3-1", "Saw3-1"}


def test_element_fields(synthetic_adv_bytes):
    doc = parse_bytes(synthetic_adv_bytes)
    by_name = {e.name: e for e in parse_elements(synthetic_adv_bytes, doc)}
    saw = by_name["Saw1-1"]
    assert saw.kind == "saw"
    assert saw.tag == 86
    assert abs(saw.offset - 1000.0) < 1e-6
    assert abs(saw.normal[2] - 1.0) < 1e-6        # unit normal preserved
    assert by_name["Pie3-1"].kind == "pie"


def test_element_solution_grouping(synthetic_adv_bytes):
    doc = parse_bytes(synthetic_adv_bytes)
    by_name = {e.name: e for e in parse_elements(synthetic_adv_bytes, doc)}
    assert by_name["Saw1-1"].solution == "1"
    assert by_name["Pie3-1"].solution == "3"
    assert list_solutions(synthetic_adv_bytes, doc) == {"1": 1, "3": 2}


def test_reconstruct_planning_proxy_planes(synthetic_adv_bytes):
    doc = parse_bytes(synthetic_adv_bytes)
    result = reconstruct_planning(synthetic_adv_bytes, doc, plane_size_mm=7.0,
                                  stone_solids=False)
    assert len(result.meshes) == 3
    assert len(result.contours) == 3
    for mesh in result.meshes:
        assert mesh.faces.shape == (2, 3)         # each element is a quad
        assert not mesh.is_empty


def test_reconstruct_planning_stone_solids(synthetic_adv_bytes):
    doc = parse_bytes(synthetic_adv_bytes)
    result = reconstruct_planning(synthetic_adv_bytes, doc, stone_solids=True)
    by_name = {m.name: m for m in result.meshes}
    # Pie element -> faceted brilliant-cut solid
    assert by_name["Pie3-1"].faces.shape[0] > 50
    assert not by_name["Pie3-1"].is_empty
    # Saw elements stay flat cutting planes
    assert by_name["Saw1-1"].faces.shape == (2, 3)


def test_reconstruct_planning_solution_filter(synthetic_adv_bytes):
    doc = parse_bytes(synthetic_adv_bytes)
    one = reconstruct_planning(synthetic_adv_bytes, doc, solution="1")
    assert [m.name for m in one.meshes] == ["Saw1-1"]
    three = reconstruct_planning(synthetic_adv_bytes, doc, solution="3")
    assert {m.name for m in three.meshes} == {"Pie3-1", "Saw3-1"}
