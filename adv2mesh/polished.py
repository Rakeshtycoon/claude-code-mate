"""Planned polished diamond extraction.

Each planned polished result is a ~2.4-3.2 KB record keyed by a
length-prefixed shape string ("ROUND"). A record carries:

  * shape ("ROUND"), scanner ("GLX" / "GLX-1"), colour ("WH"), and a
    polish-orientation mode string ("Manual" / ...)
  * embedded saw/facet planes in the same [n, offset, 50.0] form as planes.py
  * a small (7-10 point) bounding-cage vertex set (float64)

NOTE: the polished diamonds are stored as planning solutions, NOT as
explicit 57-facet meshes - the brilliant geometry is parametric. The
cage vertices are exported as a low-poly proxy only.
"""
import re
import math
from .util import f64, u32, read_ascii, plausible_f64

_ORIENT = ("Manual", "Automatic", "Auto", "Fixed", "Optimal")
_SCAN = ("GLX-1", "GLX")
_COLOR = ("WH", "YE", "BR", "BN")


class PolishedDiamond:
    """One planned polished diamond instance (a planning solution result)."""

    def __init__(self, idx, file_offset):
        self.idx = idx
        self.file_offset = file_offset
        self.shape = "ROUND"
        self.scanner = None
        self.color = None
        self.orientation = None
        self.planes = []            # list of (normal, offset)
        self.cage = []              # list of (x,y,z) bounding-cage vertices
        self.faces = []             # convex-hull faces of the cage

    def to_dict(self):
        bb = None
        if self.cage:
            bb = [[min(v[i] for v in self.cage) for i in range(3)],
                  [max(v[i] for v in self.cage) for i in range(3)]]
        return {
            "id": self.idx, "file_offset": hex(self.file_offset),
            "shape": self.shape, "scanner": self.scanner, "color": self.color,
            "polish_orientation": self.orientation,
            "facet_saw_planes": [{"normal": [round(x, 5) for x in n],
                                  "offset": round(o, 3)}
                                 for n, o in self.planes],
            "cage_vertices": len(self.cage), "hull_faces": len(self.faces),
            "bbox": bb,
        }


def _hull(P):
    """Brute-force convex hull (O(n^4)) - fine for the tiny 7-10 point cages."""
    n = len(P)
    if n < 4:
        return []
    cen = [sum(p[i] for p in P) / n for i in range(3)]

    def sub(a, b): return [a[i] - b[i] for i in range(3)]
    def cr(a, b): return [a[1] * b[2] - a[2] * b[1],
                          a[2] * b[0] - a[0] * b[2],
                          a[0] * b[1] - a[1] * b[0]]
    def dt(a, b): return sum(a[i] * b[i] for i in range(3))

    faces = set()
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                nr = cr(sub(P[j], P[i]), sub(P[k], P[i]))
                if dt(nr, nr) < 1e-9:
                    continue
                side = [dt(nr, sub(P[m], P[i]))
                        for m in range(n) if m not in (i, j, k)]
                inward = dt(nr, sub(cen, P[i])) < 0
                if all(s <= 1e-6 for s in side):
                    faces.add((i, j, k) if inward else (i, k, j))
                elif all(s >= -1e-6 for s in side):
                    faces.add((i, k, j) if inward else (i, j, k))
    return list(faces)


def extract_polished(data):
    """Find every 'ROUND' record and decode it into a PolishedDiamond."""
    rounds = [m.start() - 4 for m in re.finditer(rb"ROUND", data)
              if m.start() >= 4 and u32(data, m.start() - 4) == 5]
    result = []
    for idx, r in enumerate(rounds):
        a = max(0, r - 0x220)
        b = min(len(data), r - 0x220 + 3400)
        pd = PolishedDiamond(idx, r)
        window = data[a:b]
        for tok in _SCAN:
            if pd.scanner is None and tok.encode() in window:
                pd.scanner = tok
        for tok in _COLOR:
            if pd.color is None and (b"\x02\x00\x00\x00" + tok.encode()) in window:
                pd.color = tok
        for tok in _ORIENT:
            if tok.encode() in window:
                pd.orientation = tok
                break
        # embedded planes: [nx,ny,nz,offset,50.0]
        seen = set()
        for o in range(a, b - 40):
            if abs(f64(data, o + 32) - 50.0) > 1e-9:
                continue
            nx, ny, nz = f64(data, o), f64(data, o + 8), f64(data, o + 16)
            if any(v != v for v in (nx, ny, nz)):
                continue
            mag = math.sqrt(nx * nx + ny * ny + nz * nz)
            if 0.985 < mag < 1.015:
                normal = (nx / mag, ny / mag, nz / mag)
                off = f64(data, o + 24)
                key = (round(off, 2), tuple(round(x, 3) for x in normal))
                if key not in seen:
                    seen.add(key)
                    pd.planes.append((normal, off))
        # bounding-cage vertex set: longest plausible float64 triple run
        best = None
        for al in range(8):
            o = a + al
            while o + 24 <= b:
                if plausible_f64(f64(data, o)):
                    st = o
                    while o + 8 <= b and plausible_f64(f64(data, o)):
                        o += 8
                    cc = (o - st) // 8
                    if cc >= 9 and cc % 3 == 0 and abs(f64(data, st)) > 1 \
                            and (best is None or cc > best[1]):
                        best = (st, cc)
                else:
                    o += 1
        if best:
            st, cc = best
            pd.cage = [(f64(data, st + 24 * k),
                        f64(data, st + 24 * k + 8),
                        f64(data, st + 24 * k + 16)) for k in range(cc // 3)]
            pd.faces = _hull(pd.cage)
        result.append(pd)
    return result
