"""Geometry harvesting and mesh building.

Two contour encodings exist in the payload region (header .. first JPEG):

  * float32 contour chain
      record header (9 bytes):  u32 tag ; u8 0x01 ; u32 vertex_count
      then vertex_count * 3 float32 (x,y,z), 12 bytes/vertex.
      Records are packed back-to-back; the chain drifts off any fixed
      byte alignment, so it MUST be parsed sequentially, not grid-scanned.

  * float64 contour arrays
      vertex_count * 3 float64 (24 bytes/vertex). Mostly planar loops
      (one component ~0) - scan silhouette / cross-section outlines.

The mesh builder lofts a contour stack into a triangle surface. NOTE:
validation against the scanner imagery showed that lofting per-angle
*silhouette* contours twists the surface - a visual-hull builder is the
correct long-term fix. `MeshBuilder` is therefore an explicit interface
so a `VisualHullBuilder` can be dropped in without touching callers.
"""
import math
from .util import f32, f64, u32, plausible_f32, plausible_f64, bbox

VERTEX_STRIDE_F32 = 12
HEADER_LEN_F32 = 9


# ----------------------------------------------------------------------
# harvesting
# ----------------------------------------------------------------------

def _try_f32_chain(data, p, hi):
    """Parse a maximal run of float32 contour records starting at p."""
    out = []
    while p + HEADER_LEN_F32 < hi:
        if data[p + 4] != 0x01:                # marker byte
            break
        count = u32(data, p + 5)
        if not (3 <= count <= 4000):
            break
        vstart = p + HEADER_LEN_F32
        vend = vstart + count * VERTEX_STRIDE_F32
        if vend > hi:
            break
        step = max(1, count // 10)             # sample-validate the floats
        if not all(plausible_f32(f32(data, vstart + 12 * k))
                   for k in range(0, count, step)):
            break
        verts = [(f32(data, vstart + 12 * k),
                  f32(data, vstart + 12 * k + 4),
                  f32(data, vstart + 12 * k + 8)) for k in range(count)]
        out.append({"offset": vstart, "tag": u32(data, p), "verts": verts})
        p = vend
    return out, p


def harvest_f32_contours(data, lo, hi):
    """Return all float32 contour records in [lo, hi) via sequential chains."""
    contours = []
    p = lo
    while p < hi - HEADER_LEN_F32:
        if data[p + 4] != 0x01:
            p += 1
            continue
        chain, end = _try_f32_chain(data, p, hi)
        if len(chain) >= 3:                    # require >=3 to lock onto a chain
            contours.extend(chain)
            p = end
        else:
            p += 1
    return contours


def harvest_f64_contours(data, lo, hi):
    """Return all float64 contour arrays (>=4 vertices) in [lo, hi)."""
    contours = []
    o = lo
    while o + 8 <= hi:
        v = f64(data, o)
        if plausible_f64(v) and v != 0.0:
            start = o
            while o + 8 <= hi and plausible_f64(f64(data, o)):
                o += 8
            ndoubles = (o - start) // 8
            if ndoubles >= 12 and ndoubles % 3 == 0:
                nv = ndoubles // 3
                verts = [(f64(data, start + 24 * k),
                          f64(data, start + 24 * k + 8),
                          f64(data, start + 24 * k + 16)) for k in range(nv)]
                contours.append({"offset": start, "verts": verts})
        else:
            o += 1
    return contours


def detect_compressed_blob(data, lo, hi, window=16384):
    """Locate a high-entropy (likely proprietary-compressed) region.

    Used to flag where the inclusion meshes live; they are NOT decodable
    without the Advisor codec, so the converter only reports the region.
    """
    import collections
    best = None
    o = lo
    while o + window <= hi:
        seg = data[o:o + window]
        cnt = collections.Counter(seg)
        ent = -sum((c / window) * math.log2(c / window) for c in cnt.values())
        if ent > 7.8:
            if best is None:
                best = [o, o + window]
            else:
                best[1] = o + window
        elif best is not None and best[1] - best[0] > 4 * window:
            break
        o += window
    return tuple(best) if best else None


# ----------------------------------------------------------------------
# mesh builders (extensible)
# ----------------------------------------------------------------------

class MeshBuilder:
    """Interface: turn a list of contours into (verts, faces)."""

    def build(self, contours):
        raise NotImplementedError


class LoftMeshBuilder(MeshBuilder):
    """Loft a stack of contours into a triangle surface.

    Assumes the contours are ordered cross-sections. For per-angle
    silhouette data this twists - see module docstring.
    """

    def __init__(self, ring_samples=72):
        self.M = ring_samples

    @staticmethod
    def _dist(a, b):
        return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))

    def _resample(self, poly, M):
        seg = [self._dist(poly[i], poly[i + 1]) for i in range(len(poly) - 1)]
        total = sum(seg) or 1.0
        out, i, acc = [], 0, 0.0
        for m in range(M):
            t = total * m / (M - 1)
            while i < len(seg) - 1 and acc + seg[i] < t:
                acc += seg[i]
                i += 1
            f = (t - acc) / seg[i] if seg[i] > 0 else 0.0
            a, b = poly[i], poly[i + 1]
            out.append(tuple(a[k] + f * (b[k] - a[k]) for k in range(3)))
        return out

    def build(self, contours):
        polys = [c["verts"] for c in contours if len(c["verts"]) >= 3]
        if len(polys) < 2:
            return [], []
        M = self.M
        rings = []
        for poly in polys:
            r = self._resample(poly, M)
            if rings and self._dist(r[0], rings[-1][0]) > \
                         self._dist(r[-1], rings[-1][0]):
                r = r[::-1]                    # keep consistent direction
            rings.append(r)
        verts = [p for r in rings for p in r]
        faces = []
        for i in range(len(rings) - 1):
            a, b = i * M, (i + 1) * M
            for j in range(M - 1):
                faces.append((a + j, a + j + 1, b + j + 1))
                faces.append((a + j, b + j + 1, b + j))
        return verts, faces


def contour_lines(contours):
    """Flatten contours into (verts, polylines) for line-geometry export."""
    verts, lines, base = [], [], 0
    for c in contours:
        v = c["verts"]
        verts.extend(v)
        lines.append(list(range(base, base + len(v))))
        base += len(v)
    return verts, lines
