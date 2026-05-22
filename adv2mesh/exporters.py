"""Exporter pipeline: Scene -> OBJ / MTL / STL / glTF.

OBJ and STL bake every node transform into world space. glTF keeps the
node hierarchy and per-node matrices intact (true scene graph). All four
consume the same Scene object - adding a format means adding one writer.
"""
import struct
import base64
import json
import math
from .scene import transform_point

# material name -> (RGB 0..1, alpha)
MATERIALS = {
    "rough":         ((0.85, 0.88, 0.95), 0.45),
    "polished":      ((0.30, 0.80, 0.90), 0.85),
    "cutting_plane": ((0.90, 0.32, 0.22), 0.40),
    "inclusion":     ((0.90, 0.12, 0.12), 1.00),
}


def _material_of(node):
    return node.extras.get("material", "rough")


# ----------------------------------------------------------------------
# OBJ + MTL
# ----------------------------------------------------------------------

def export_obj(scene, obj_path, mtl_name="model.mtl"):
    base = 1
    with open(obj_path, "w") as f:
        f.write("# adv2mesh OBJ export\n")
        f.write("mtllib %s\n" % mtl_name)
        for node, world in scene.walk():
            m = node.mesh
            if not m or not m.verts:
                continue
            f.write("o %s\n" % node.name)
            f.write("usemtl %s\n" % _material_of(node))
            for v in m.verts:
                w = transform_point(world, v)
                f.write("v %.5f %.5f %.5f\n" % w)
            for tri in m.faces:
                f.write("f %d %d %d\n"
                        % (base + tri[0], base + tri[1], base + tri[2]))
            for poly in m.lines:
                f.write("l " + " ".join(str(base + i) for i in poly) + "\n")
            base += len(m.verts)


def export_mtl(mtl_path):
    with open(mtl_path, "w") as f:
        f.write("# adv2mesh materials\n")
        for name, (rgb, alpha) in MATERIALS.items():
            f.write("newmtl %s\n" % name)
            f.write("Kd %.3f %.3f %.3f\n" % rgb)
            f.write("d %.3f\n" % alpha)
            f.write("illum 2\n\n")


# ----------------------------------------------------------------------
# STL (binary, world space)
# ----------------------------------------------------------------------

def _face_normal(a, b, c):
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    n = (u[1] * v[2] - u[2] * v[1],
         u[2] * v[0] - u[0] * v[2],
         u[0] * v[1] - u[1] * v[0])
    m = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) or 1.0
    return (n[0] / m, n[1] / m, n[2] / m)


def export_stl(scene, stl_path):
    tris = []
    for node, world in scene.walk():
        m = node.mesh
        if not m or not m.faces:
            continue
        wv = [transform_point(world, v) for v in m.verts]
        for tri in m.faces:
            tris.append((wv[tri[0]], wv[tri[1]], wv[tri[2]]))
    with open(stl_path, "wb") as f:
        f.write(b"adv2mesh binary STL".ljust(80, b"\x00"))
        f.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            f.write(struct.pack("<3f", *_face_normal(a, b, c)))
            f.write(struct.pack("<3f", *a))
            f.write(struct.pack("<3f", *b))
            f.write(struct.pack("<3f", *c))
            f.write(struct.pack("<H", 0))
    return len(tris)


# ----------------------------------------------------------------------
# glTF 2.0 (single file, base64-embedded buffer, hierarchy preserved)
# ----------------------------------------------------------------------

class _GltfBuilder:
    def __init__(self):
        self.buf = bytearray()
        self.bufviews = []
        self.accessors = []
        self.meshes = []

    def _pad(self):
        while len(self.buf) % 4:
            self.buf.append(0)

    def _positions(self, verts):
        self._pad()
        off = len(self.buf)
        for v in verts:
            self.buf.extend(struct.pack("<3f", *v))
        self.bufviews.append({"buffer": 0, "byteOffset": off,
                              "byteLength": len(verts) * 12, "target": 34962})
        mn = [min(v[i] for v in verts) for i in range(3)]
        mx = [max(v[i] for v in verts) for i in range(3)]
        self.accessors.append({"bufferView": len(self.bufviews) - 1,
                               "componentType": 5126, "count": len(verts),
                               "type": "VEC3", "min": mn, "max": mx})
        return len(self.accessors) - 1

    def _indices(self, flat):
        self._pad()
        off = len(self.buf)
        for i in flat:
            self.buf.extend(struct.pack("<I", i))
        self.bufviews.append({"buffer": 0, "byteOffset": off,
                              "byteLength": len(flat) * 4, "target": 34963})
        self.accessors.append({"bufferView": len(self.bufviews) - 1,
                               "componentType": 5125, "count": len(flat),
                               "type": "SCALAR"})
        return len(self.accessors) - 1

    def add_mesh(self, mesh, material):
        if not mesh.verts:
            return None
        pos = self._positions(mesh.verts)
        prims = []
        if mesh.faces:
            idx = self._indices([i for t in mesh.faces for i in t])
            prims.append({"attributes": {"POSITION": pos},
                          "indices": idx, "material": material, "mode": 4})
        elif mesh.lines:
            for poly in mesh.lines:
                idx = self._indices(poly)
                prims.append({"attributes": {"POSITION": pos},
                              "indices": idx, "material": material, "mode": 3})
        else:
            prims.append({"attributes": {"POSITION": pos},
                          "material": material, "mode": 0})
        self.meshes.append({"name": mesh.name, "primitives": prims})
        return len(self.meshes) - 1


def _to_column_major(row_major):
    """glTF node matrices are column-major; transpose our row-major form."""
    m = row_major
    return [m[0], m[4], m[8], m[12],
            m[1], m[5], m[9], m[13],
            m[2], m[6], m[10], m[14],
            m[3], m[7], m[11], m[15]]


def export_gltf(scene, gltf_path):
    gb = _GltfBuilder()
    mat_index = {name: i for i, name in enumerate(MATERIALS)}
    nodes = []
    mesh_cache = {}                       # id(Mesh) -> glTF mesh index

    def emit(node):
        gltf_node = {"name": node.name}
        if node.matrix and node.matrix != [1, 0, 0, 0, 0, 1, 0, 0,
                                           0, 0, 1, 0, 0, 0, 0, 1]:
            gltf_node["matrix"] = _to_column_major(node.matrix)
        if node.mesh:
            key = id(node.mesh)           # shared meshes are emitted once
            if key not in mesh_cache:
                mesh_cache[key] = gb.add_mesh(
                    node.mesh, mat_index.get(_material_of(node), 0))
            mi = mesh_cache[key]
            if mi is not None:
                gltf_node["mesh"] = mi
        idx = len(nodes)
        nodes.append(gltf_node)
        child_ids = [emit(c) for c in node.children]
        if child_ids:
            nodes[idx]["children"] = child_ids
        return idx

    root_id = emit(scene.root)
    materials = []
    for name, (rgb, alpha) in MATERIALS.items():
        materials.append({
            "name": name,
            "pbrMetallicRoughness": {
                "baseColorFactor": [rgb[0], rgb[1], rgb[2], alpha],
                "metallicFactor": 0.1, "roughnessFactor": 0.2},
            "alphaMode": "BLEND" if alpha < 1.0 else "OPAQUE",
            "doubleSided": True,
        })
    gltf = {
        "asset": {"version": "2.0", "generator": "adv2mesh"},
        "scene": 0,
        "scenes": [{"nodes": [root_id]}],
        "nodes": nodes,
        "meshes": gb.meshes,
        "accessors": gb.accessors,
        "bufferViews": gb.bufviews,
        "materials": materials,
        "buffers": [{
            "byteLength": len(gb.buf),
            "uri": "data:application/octet-stream;base64,"
                   + base64.b64encode(bytes(gb.buf)).decode("ascii"),
        }],
    }
    with open(gltf_path, "w") as f:
        json.dump(gltf, f)
