"""Headless tests for the viewer scene model (no Qt required)."""
from advrecover.format import parse_bytes
from advrecover.viewer.scene import LAYER_ORDER, build_scene


def test_build_scene_has_all_layers(synthetic_adv_bytes):
    doc = parse_bytes(synthetic_adv_bytes)
    scene = build_scene(synthetic_adv_bytes, doc, geometry_method="hull")
    keys = [layer.key for layer in scene.layers]
    assert keys == list(LAYER_ORDER)


def test_build_scene_planning_layers(synthetic_adv_bytes):
    doc = parse_bytes(synthetic_adv_bytes)
    scene = build_scene(synthetic_adv_bytes, doc, geometry_method="hull")
    saw = scene.layer("cutting_planes")
    pie = scene.layer("planned_stones")
    assert len(saw.meshes) == 2          # Saw1-1, Saw3-1
    assert len(pie.meshes) == 1          # Pie3-1


def test_build_scene_bounds_and_bbox(synthetic_adv_bytes):
    doc = parse_bytes(synthetic_adv_bytes)
    scene = build_scene(synthetic_adv_bytes, doc, geometry_method="hull")
    assert scene.bounds_min is not None
    assert scene.dimensions is not None
    assert all(d > 0 for d in scene.dimensions)
    assert len(scene.layer("bounding_box").lines) == 12


def test_build_scene_solution_filter(synthetic_adv_bytes):
    doc = parse_bytes(synthetic_adv_bytes)
    scene = build_scene(synthetic_adv_bytes, doc, solution="1",
                        geometry_method="hull")
    assert len(scene.layer("cutting_planes").meshes) == 1
    assert len(scene.layer("planned_stones").meshes) == 0


def test_rough_body_marked_inferred(synthetic_adv_bytes):
    doc = parse_bytes(synthetic_adv_bytes)
    scene = build_scene(synthetic_adv_bytes, doc, geometry_method="hull")
    assert scene.layer("rough_body").inferred is True
    assert scene.layer("cutting_planes").inferred is False
