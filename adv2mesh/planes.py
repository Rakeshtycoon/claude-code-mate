"""Cutting / saw plane extraction.

Each Saw*/Pie* planning object embeds a fixed 6 x float64 plane record:

    f64  const_field      = 50.0  (fixed in every observed plane)
    f64  offset           signed distance of the plane from the rough centroid
    f64  blade_thickness  = 0.0   (idealised zero-kerf cut)
    f64  nx, ny, nz       unit normal vector  (|n| = 1)

The plane equation, with C = rough-mesh centroid, is:

        n . X = n . C + offset

This frame was verified: 277/277 planes land inside the rough model's
n.X range when (and only when) the centroid term is included.
"""
import struct
import re
import math
import bisect
from .util import f64, u32, vdot

CONST_FIELD = 50.0
_FIFTY = struct.pack("<d", 50.0)


class CuttingPlane:
    """A single saw / cleave plane with its world-space placement."""

    __slots__ = ("file_offset", "name", "normal", "offset",
                 "d_abs", "anchor", "azimuth", "elevation")

    def __init__(self, file_offset, name, normal, offset):
        self.file_offset = file_offset
        self.name = name
        self.normal = normal
        self.offset = offset
        self.d_abs = None
        self.anchor = None
        self.azimuth = math.degrees(math.atan2(normal[1], normal[0]))
        self.elevation = math.degrees(math.asin(max(-1.0, min(1.0, normal[2]))))

    def solve(self, centroid):
        """Resolve the absolute plane equation and anchor point."""
        nc = vdot(self.normal, centroid)
        self.d_abs = nc + self.offset
        self.anchor = tuple(centroid[i] + self.offset * self.normal[i]
                            for i in range(3))

    def to_dict(self):
        return {
            "name": self.name,
            "file_offset": hex(self.file_offset),
            "normal": [round(x, 6) for x in self.normal],
            "offset_from_centroid": round(self.offset, 4),
            "plane_d_abs": None if self.d_abs is None else round(self.d_abs, 4),
            "blade_thickness": 0.0,
            "anchor_point": None if self.anchor is None
                            else [round(x, 3) for x in self.anchor],
            "azimuth_deg": round(self.azimuth, 2),
            "elevation_deg": round(self.elevation, 2),
        }


def _names(data):
    """Index every length-prefixed Saw*/Pie* object name -> (offset, text)."""
    out = []
    for m in re.finditer(rb"(Saw|Pie)\d+-\d+", data):
        o = m.start()
        if o >= 4 and u32(data, o - 4) == m.end() - m.start():
            out.append((o - 4, m.group().decode()))
    out.sort()
    return out


def extract_cutting_planes(data):
    """Scan the whole file for plane records; return a deduplicated list.

    The 50.0 anchor double + zero blade-thickness double + unit normal is a
    highly specific signature, so false positives are effectively nil.
    """
    names = _names(data)
    name_off = [n[0] for n in names]
    planes, pos, seen = [], 0, set()
    while True:
        o = data.find(_FIFTY, pos)
        if o < 0:
            break
        pos = o + 1
        if o + 48 > len(data):
            continue
        if abs(f64(data, o + 16)) > 1e-12:          # blade thickness must be 0
            continue
        nx, ny, nz = f64(data, o + 24), f64(data, o + 32), f64(data, o + 40)
        if any(v != v for v in (nx, ny, nz)):
            continue
        mag = math.sqrt(nx * nx + ny * ny + nz * nz)
        if not (0.985 < mag < 1.015):               # must be a unit normal
            continue
        off = f64(data, o + 8)
        if off != off or abs(off) > 1e7:
            continue
        normal = (nx / mag, ny / mag, nz / mag)
        idx = bisect.bisect_right(name_off, o) - 1
        name = (names[idx][1]
                if idx >= 0 and o - names[idx][0] < 600 else None)
        key = (name, round(off, 3), tuple(round(x, 5) for x in normal))
        if key in seen:
            continue
        seen.add(key)
        planes.append(CuttingPlane(o, name, normal, off))
    return planes
