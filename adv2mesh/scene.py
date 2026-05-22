"""Scene-graph model and assembly.

The scene is a simple node tree. Each node may carry one Mesh and a
4x4 row-major transform. Exporters consume this model directly, so the
same scene drives OBJ / STL / glTF without per-format assembly logic.

World convention: right-handed, Z-up, origin at the rough centroid
(all geometry is translated so the rough diamond is centred).
"""
from .util import bbox, vdot, vcross, vnorm

IDENTITY4 = [1.0, 0.0, 0.0, 0.0,
             0.0, 1.0, 0.0, 0.0,
             0.0, 0.0, 1.0, 0.0,
             0.0, 0.0, 0.0, 1.0]


class Mesh:
    """Triangle mesh and/or polyline set in node-local coordinates."""

    def __init__(self, name, verts=None, faces=None, lines=None):
        self.name = name
        self.verts = verts or []
        self.faces = faces or []          # list of (i,j,k)
        self.lines = lines or []          # list of index polylines

    def bbox(self):
        return bbox(self.verts) if self.verts else ((0, 0, 0), (0, 0, 0))


class Node:
    """A scene-graph node: name, transform, optional mesh, children, extras."""

    def __init__(self, name, mesh=None, matrix=None, extras=None):
        self.name = name
        self.mesh = mesh
        self.matrix = matrix or list(IDENTITY4)   # row-major 4x4
        self.children = []
        self.extras = extras or {}

    def add(self, child):
        self.children.append(child)
        return child

    def walk(self, parent_world=None):
        """Yield (node, world_matrix) depth-first."""
        world = (self.matrix if parent_world is None
                 else _mat_mul(parent_world, self.matrix))
        yield self, world
        for c in self.children:
            yield from c.walk(world)


class Scene:
    """Root container plus assembly metadata."""

    def __init__(self, name):
        self.root = Node(name)
        self.metadata = {}

    def walk(self):
        yield from self.root.walk()


# ---- 4x4 row-major helpers -------------------------------------------

def _mat_mul(a, b):
    out = [0.0] * 16
    for r in range(4):
        for c in range(4):
            out[r * 4 + c] = sum(a[r * 4 + k] * b[k * 4 + c] for k in range(4))
    return out


def transform_point(m, p):
    """Apply a row-major 4x4 to a point."""
    x, y, z = p
    return (m[0] * x + m[1] * y + m[2] * z + m[3],
            m[4] * x + m[5] * y + m[6] * z + m[7],
            m[8] * x + m[9] * y + m[10] * z + m[11])


def translation(t):
    m = list(IDENTITY4)
    m[3], m[7], m[11] = t[0], t[1], t[2]
    return m


def plane_basis_matrix(normal, anchor, half_size):
    """Build a row-major 4x4 that places a unit quad as a cutting plate.

    Columns U,V span the plane (scaled by half_size); the normal is the
    third axis; anchor is the translation.
    """
    n = vnorm(normal)
    ref = (0.0, 0.0, 1.0) if abs(n[2]) < 0.9 else (1.0, 0.0, 0.0)
    u = vnorm(vcross(n, ref))
    v = vcross(n, u)
    s = half_size
    return [u[0] * s, v[0] * s, n[0], anchor[0],
            u[1] * s, v[1] * s, n[1], anchor[1],
            u[2] * s, v[2] * s, n[2], anchor[2],
            0.0,      0.0,      0.0,  1.0]
