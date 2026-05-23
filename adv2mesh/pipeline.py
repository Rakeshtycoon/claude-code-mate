"""Conversion pipeline - orchestrates parse -> extract -> assemble -> export.

`convert()` is the single public entry point. It is intentionally linear
and heavily logged so an extraction run is fully auditable.
"""
import os
import json
import logging

from .container import ADVContainer, CHUNK_NAMES
from .chunks import decode_chunk
from .geometry import (harvest_f32_contours, harvest_f64_contours,
                       detect_compressed_blob, LoftMeshBuilder, contour_lines)
from .planes import extract_cutting_planes
from .polished import extract_polished
from .units import estimate_units
from .scene import Scene, Node, Mesh, translation, plane_basis_matrix
from .exporters import export_obj, export_mtl, export_stl, export_gltf
from .debug import render_scene
from .util import bbox, vdot

log = logging.getLogger("adv2mesh")


def _setup_log_file(out_dir, verbose):
    """Attach a per-run FileHandler to the package logger and return it.

    Console / GUI handlers are the caller's responsibility - we never touch
    pre-existing handlers, so the same `convert()` works under the CLI and
    inside the Tkinter GUI thread without conflict.
    """
    log.setLevel(logging.DEBUG if verbose else logging.INFO)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s",
                            "%H:%M:%S")
    fh = logging.FileHandler(os.path.join(out_dir, "extraction.log"), "w")
    fh.setFormatter(fmt)
    fh.setLevel(logging.DEBUG)
    log.addHandler(fh)
    return fh


def convert(adv_path, out_dir, *, loft=True, debug_png=True, verbose=False):
    """Convert an .ADV file into OBJ/STL/glTF + metadata, returning a report.

    Parameters
    ----------
    adv_path  : path to the input .ADV file
    out_dir   : directory for all generated artefacts (created if needed)
    loft      : build a lofted rough mesh (else rough is contour lines only)
    debug_png : render an orthographic debug PNG of the scene
    verbose   : DEBUG-level logging
    """
    os.makedirs(out_dir, exist_ok=True)
    fh = _setup_log_file(out_dir, verbose)
    try:
        return _convert_impl(adv_path, out_dir, loft, debug_png)
    finally:
        log.removeHandler(fh)
        fh.close()


def _convert_impl(adv_path, out_dir, loft, debug_png):
    log.info("adv2mesh - converting %s", adv_path)

    with open(adv_path, "rb") as f:
        data = f.read()
    log.info("read %d bytes", len(data))

    # -- 1. container -------------------------------------------------
    cont = ADVContainer(data)
    log.info("container OK  magic=%s  version=%d", cont.magic, cont.version)
    for cid, off in sorted(cont.chunks.items()):
        log.info("  chunk %-18s @ 0x%X", CHUNK_NAMES.get(cid, str(cid)), off)

    # -- 2. metadata --------------------------------------------------
    meta = decode_chunk(3, cont.chunk_bytes(3)) or {"key_values": {}}
    kv = meta.get("key_values", {})
    rough_ct = _flt(kv.get("stone.RoughWeight"))
    log.info("metadata: %d key/values  rough=%.4f ct  color=%s clarity=%s",
             len(kv), rough_ct or 0.0,
             _str(meta, "Stone.color"), _str(meta, "Stone.clarity"))

    # -- 3. geometry harvest -----------------------------------------
    first_jpeg = data.find(b"\xff\xd8\xff")
    geom_end = first_jpeg if first_jpeg > 0 else cont.footer_ptr
    f32 = harvest_f32_contours(data, 0x20, geom_end)
    f32_start = min((c["offset"] for c in f32), default=geom_end)
    f64 = harvest_f64_contours(data, 0x20, f32_start)
    log.info("contours: %d float32 (rough)  %d float64 (silhouettes)",
             len(f32), len(f64))

    blob = detect_compressed_blob(data, 0x10000, geom_end)
    if blob:
        log.warning("opaque compressed region 0x%X-0x%X (%d KB) - inclusion "
                    "meshes live here and are NOT decodable",
                    blob[0], blob[1], (blob[1] - blob[0]) // 1024)

    # -- 4. cutting planes & polished --------------------------------
    planes = extract_cutting_planes(data)
    polished = extract_polished(data)
    log.info("cutting planes: %d   polished instances: %d",
             len(planes), len(polished))
    if not planes:
        log.warning("no cutting planes matched - the plane extractor keys on "
                    "the const_field=50.0 signature; this file may use a "
                    "format variant (see RE_NOTES.md)")

    # -- 5. rough mesh + centroid ------------------------------------
    rough_verts, rough_faces = ([], [])
    if loft and f32:
        rough_verts, rough_faces = LoftMeshBuilder().build(f32)
        log.info("rough loft mesh: %d verts / %d tris",
                 len(rough_verts), len(rough_faces))
    all_rough_pts = [v for c in f32 for v in c["verts"]] or [(0, 0, 0)]
    centroid = tuple(sum(p[i] for p in all_rough_pts) / len(all_rough_pts)
                     for i in range(3))
    log.info("rough centroid (world origin): (%.1f, %.1f, %.1f)", *centroid)

    # -- 6. units -----------------------------------------------------
    sil_pts = ([v for c in f64 for v in c["verts"]]
               or [v for c in f32 for v in c["verts"]] or [(0, 0, 0)])
    sb = bbox(sil_pts)
    extent = max(sb[1][i] - sb[0][i] for i in range(3))
    units = estimate_units(extent, rough_ct)
    if "estimated_units_per_mm" in units:
        log.info("unit estimate: ~%.0f units/mm (%s)",
                 units["estimated_units_per_mm"], units["system"])

    # -- 7. assemble scene -------------------------------------------
    scene = _build_scene(cont, f32, f64, planes, polished,
                         rough_verts, rough_faces, centroid, loft)
    diag = _scene_diag(scene)

    # -- 8. export ----------------------------------------------------
    stem = os.path.splitext(os.path.basename(adv_path))[0]
    obj_p = os.path.join(out_dir, stem + ".obj")
    mtl_p = os.path.join(out_dir, stem + ".mtl")
    stl_p = os.path.join(out_dir, stem + ".stl")
    gltf_p = os.path.join(out_dir, stem + ".gltf")
    export_mtl(mtl_p)
    export_obj(scene, obj_p, os.path.basename(mtl_p))
    ntri = export_stl(scene, stl_p)
    export_gltf(scene, gltf_p)
    log.info("exported OBJ/MTL/STL(%d tri)/glTF", ntri)

    png_p = None
    if debug_png:
        png_p = render_scene(scene, os.path.join(out_dir, stem + "_debug.png"))
        if png_p:
            log.info("debug visualisation -> %s", os.path.basename(png_p))

    # -- 9. metadata JSON --------------------------------------------
    report = {
        "source": os.path.basename(adv_path),
        "container": cont.summary(),
        "stone_metadata": kv,
        "units": units,
        "coordinate_system": {
            "world_origin": "rough diamond centroid",
            "original_centroid": [round(x, 2) for x in centroid],
            "handedness": "right-handed", "up_axis": "Z"},
        "object_counts": {
            "rough_diamond": 1,
            "polished_diamonds": len(polished),
            "cutting_planes": len(planes),
            "inclusions": ("%s (compressed blob - not recoverable)"
                           % _inclusion_count(kv))},
        "compressed_blob": (None if not blob else
                            {"start": hex(blob[0]), "end": hex(blob[1]),
                             "note": "inclusion meshes - proprietary codec"}),
        "cutting_planes": [p.to_dict() for p in planes],
        "polished_diamonds": [p.to_dict() for p in polished],
        "scene_hierarchy": diag["hierarchy"],
        "bounding_boxes": diag["bboxes"],
        "node_transforms": diag["transforms"],
        "exports": [os.path.basename(p) for p in
                    (obj_p, mtl_p, stl_p, gltf_p) ],
    }
    json_p = os.path.join(out_dir, stem + "_metadata.json")
    with open(json_p, "w") as f:
        json.dump(report, f, indent=1)
    log.info("metadata JSON -> %s", os.path.basename(json_p))
    log.info("done.")
    return report


# ----------------------------------------------------------------------
# scene assembly
# ----------------------------------------------------------------------

def _build_scene(cont, f32, f64, planes, polished,
                 rough_verts, rough_faces, centroid, loft):
    scene = Scene("ADV_planning_scene")

    def shift(v):
        return (v[0] - centroid[0], v[1] - centroid[1], v[2] - centroid[2])

    # rough diamond ----------------------------------------------------
    if loft and rough_verts:
        rmesh = Mesh("rough_diamond",
                     verts=[shift(v) for v in rough_verts], faces=rough_faces)
    else:
        verts, lines = contour_lines(f32)
        rmesh = Mesh("rough_diamond",
                     verts=[shift(v) for v in verts], lines=lines)
    rough_node = Node("rough_diamond", mesh=rmesh,
                      extras={"material": "rough"})
    scene.root.add(rough_node)

    # inclusions (placeholder - geometry is locked in the compressed blob)
    scene.root.add(Node("inclusions", extras={
        "material": "inclusion",
        "status": "1602 meshes inside proprietary compressed blob - "
                  "not recoverable"}))

    # polished diamonds ------------------------------------------------
    pol_group = scene.root.add(Node("polished_solutions"))
    for pd in polished:
        if not pd.cage:
            pol_group.add(Node("polished_%03d" % pd.idx,
                               extras={"material": "polished",
                                       "note": "metadata/plane-only"}))
            continue
        cc = [sum(v[i] for v in pd.cage) / len(pd.cage) for i in range(3)]
        local = [tuple(v[i] - cc[i] for i in range(3)) for v in pd.cage]
        mesh = Mesh("polished_%03d" % pd.idx, verts=local, faces=pd.faces)
        pol_group.add(Node("polished_%03d" % pd.idx, mesh=mesh,
                           extras={"material": "polished"}))

    # cutting planes ---------------------------------------------------
    quad = Mesh("plane_quad",
                verts=[(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)],
                faces=[(0, 1, 2), (0, 2, 3)])
    plane_group = scene.root.add(Node("cutting_planes"))
    for i, p in enumerate(planes):
        p.solve(centroid)
        anchor_w = shift(p.anchor)
        half = 0.5 * _rough_diag(rough_verts) or 1500.0
        mtx = plane_basis_matrix(p.normal, anchor_w, half)
        plane_group.add(Node("cut_plane_%03d_%s" % (i, p.name or "x"),
                              mesh=quad, matrix=mtx,
                              extras={"material": "cutting_plane"}))
    return scene


def _rough_diag(verts):
    if not verts:
        return 0.0
    bb = bbox(verts)
    return sum((bb[1][i] - bb[0][i]) ** 2 for i in range(3)) ** 0.5


def _scene_diag(scene):
    """Collect hierarchy / bbox / transform diagnostics for the JSON report."""
    hierarchy = []
    bboxes = {}
    transforms = {}

    def visit(node, depth):
        line = "  " * depth + node.name
        if node.mesh and node.mesh.verts:
            line += "  [%d v / %d tri]" % (len(node.mesh.verts),
                                           len(node.mesh.faces))
            bb = node.mesh.bbox()
            bboxes[node.name] = [[round(x, 1) for x in bb[0]],
                                 [round(x, 1) for x in bb[1]]]
        hierarchy.append(line)
        if node.matrix != [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]:
            transforms[node.name] = [round(x, 5) for x in node.matrix]
        for c in node.children:
            visit(c, depth + 1)

    visit(scene.root, 0)
    return {"hierarchy": hierarchy, "bboxes": bboxes,
            "transforms": transforms}


# -- small metadata helpers --------------------------------------------

def _flt(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _str(meta, key):
    return meta.get("key_values", {}).get(key)


def _inclusion_count(kv):
    return kv.get("inclusions.count.meshes") or kv.get(
        "Stone.TotalNumberOfInclusions") or "?"
