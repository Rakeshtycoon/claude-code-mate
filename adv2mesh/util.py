"""Low-level binary readers and numeric heuristics.

Every multi-byte value in the .ADV format is little-endian (confirmed:
GUIDs, counts, Windows FILETIME, IEEE floats all only decode correctly
as LE). These helpers are the single choke-point for that assumption.
"""
import struct
import math


def u8(d, o):  return d[o]
def u16(d, o): return struct.unpack_from("<H", d, o)[0]
def u32(d, o): return struct.unpack_from("<I", d, o)[0]
def u64(d, o): return struct.unpack_from("<Q", d, o)[0]
def i32(d, o): return struct.unpack_from("<i", d, o)[0]
def f32(d, o): return struct.unpack_from("<f", d, o)[0]
def f64(d, o): return struct.unpack_from("<d", d, o)[0]


def guid(d, o):
    """Decode a 16-byte Microsoft GUID to its canonical string form.

    Layout: Data1 u32-LE, Data2 u16-LE, Data3 u16-LE, Data4 8 raw bytes.
    """
    a = u32(d, o)
    b = u16(d, o + 4)
    c = u16(d, o + 6)
    rest = d[o + 8:o + 16]
    return "%08x-%04x-%04x-%s-%s" % (a, b, c, rest[:2].hex(), rest[2:].hex())


def read_lpstr(d, o, maxlen=8192):
    """Read a length-prefixed string: int32 byte-count followed by raw bytes.

    Returns (raw_bytes, total_consumed) or (None, 0) when the prefix is not
    a plausible length. No NUL terminator is used by the format.
    """
    if o + 4 > len(d):
        return None, 0
    n = u32(d, o)
    if n > maxlen or o + 4 + n > len(d):
        return None, 0
    return d[o + 4:o + 4 + n], 4 + n


def read_ascii(d, o, maxlen=256):
    """Read a length-prefixed string and return it as ASCII text or None.

    Tolerates a single trailing NUL (some enum-like fields are NUL-padded).
    """
    raw, _ = read_lpstr(d, o, maxlen)
    if raw is None:
        return None
    raw = raw.split(b"\x00")[0]
    if raw and all(32 <= b < 127 for b in raw):
        return raw.decode("ascii")
    return None


def plausible_f32(v):
    """True if v looks like a real float32 coordinate (finite, sane range)."""
    if v != v or v in (float("inf"), float("-inf")):
        return False
    a = abs(v)
    return a == 0.0 or (1e-4 < a < 1e7)


def plausible_f64(v):
    """True if v looks like a real float64 coordinate."""
    if v != v or v in (float("inf"), float("-inf")):
        return False
    a = abs(v)
    return a == 0.0 or (1e-6 < a < 1e6)


# ---- tiny 3-vector helpers (kept dependency-free; no numpy) ----

def vsub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def vadd(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def vdot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def vscale(a, s): return (a[0] * s, a[1] * s, a[2] * s)


def vcross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def vlen(a):
    return math.sqrt(vdot(a, a))


def vnorm(a):
    m = vlen(a) or 1.0
    return (a[0] / m, a[1] / m, a[2] / m)


def bbox(verts):
    """Axis-aligned bounding box of an iterable of (x,y,z) -> (min3, max3)."""
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    return ((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)))
