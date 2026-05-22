"""Debug visualisations - pure-stdlib PNG renderer (no PIL / numpy).

Produces orthographic wireframe views of the assembled scene so an
extraction run can be eyeballed without a 3D viewer.
"""
import struct
import zlib


class PNGCanvas:
    """Minimal RGB canvas with line drawing and a hand-rolled PNG encoder."""

    def __init__(self, w, h, bg=(10, 10, 16)):
        self.w = w
        self.h = h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            # additive blend so overlapping wireframes stay visible
            self.px[i] = max(self.px[i], c[0])
            self.px[i + 1] = max(self.px[i + 1], c[1])
            self.px[i + 2] = max(self.px[i + 2], c[2])

    def line(self, x0, y0, x1, y1, c):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def save(self, path):
        raw = bytearray()
        for y in range(self.h):
            raw.append(0)                              # filter byte 0
            raw += self.px[y * self.w * 3:(y + 1) * self.w * 3]
        comp = zlib.compress(bytes(raw), 9)

        def chunk(tag, data):
            return (struct.pack(">I", len(data)) + tag + data
                    + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        with open(path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
            f.write(chunk(b"IHDR", ihdr))
            f.write(chunk(b"IDAT", comp))
            f.write(chunk(b"IEND", b""))


def render_scene(scene, path, size=440):
    """Render three orthographic wireframe views (X-Z, X-Y, Z-Y)."""
    from .scene import transform_point

    # gather world-space triangles tagged by material
    tris = []
    for node, world in scene.walk():
        m = node.mesh
        if not m or not m.faces:
            continue
        mat = node.extras.get("material", "rough")
        wv = [transform_point(world, v) for v in m.verts]
        for tri in m.faces:
            tris.append((mat, wv[tri[0]], wv[tri[1]], wv[tri[2]]))
    if not tris:
        return None

    pts = [p for t in tris for p in t[1:]]
    bb = [(min(p[i] for p in pts), max(p[i] for p in pts)) for i in range(3)]
    colors = {"rough": (70, 150, 210), "polished": (90, 235, 200),
              "cutting_plane": (70, 34, 26), "inclusion": (235, 90, 90)}

    img = PNGCanvas(3 * size, size)
    for pi, (ax, ay) in enumerate([(0, 2), (0, 1), (2, 1)]):
        ox = pi * size
        ex = bb[ax][1] - bb[ax][0] or 1
        ey = bb[ay][1] - bb[ay][0] or 1
        sc = min((size - 30) / ex, (size - 30) / ey)

        def proj(v):
            return (ox + 15 + (v[ax] - bb[ax][0]) * sc,
                    (size - 15) - (v[ay] - bb[ay][0]) * sc)

        # planes first (dim), then everything else
        order = sorted(tris, key=lambda t: 0 if t[0] == "cutting_plane" else 1)
        for mat, a, b, c in order:
            col = colors.get(mat, (150, 150, 150))
            for e0, e1 in ((a, b), (b, c), (c, a)):
                p0, p1 = proj(e0), proj(e1)
                img.line(p0[0], p0[1], p1[0], p1[1], col)
    img.save(path)
    return path
