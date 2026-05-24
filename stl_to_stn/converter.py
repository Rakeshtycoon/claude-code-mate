"""STL reading and STN writing."""

from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import BinaryIO, Dict, IO, Tuple

from .types import Mesh, Normal, Vertex

_BINARY_HEADER_LEN = 80
_BINARY_TRIANGLE_LEN = 50  # 12 floats * 4 bytes + 2 attribute bytes


def _is_binary_stl(data: bytes) -> bool:
    """Detect binary vs ASCII STL.

    ASCII STL starts with "solid" but so do some binary files, so we
    cross-check the declared triangle count against the file length.
    """
    if len(data) < _BINARY_HEADER_LEN + 4:
        return False
    declared = struct.unpack_from("<I", data, _BINARY_HEADER_LEN)[0]
    expected = _BINARY_HEADER_LEN + 4 + declared * _BINARY_TRIANGLE_LEN
    if expected == len(data):
        return True
    # Fall back to ASCII if the file plausibly begins with "solid" and
    # contains the "facet" keyword.
    head = data[:512].lstrip().lower()
    return not (head.startswith(b"solid") and b"facet" in data[:4096].lower())


class _VertexPool:
    """Builds a deduplicated vertex list keyed by exact float tuples."""

    def __init__(self) -> None:
        self._index: Dict[Vertex, int] = {}
        self.vertices: list[Vertex] = []

    def add(self, v: Vertex) -> int:
        idx = self._index.get(v)
        if idx is None:
            idx = len(self.vertices)
            self._index[v] = idx
            self.vertices.append(v)
        return idx


def _parse_binary(data: bytes) -> Mesh:
    count = struct.unpack_from("<I", data, _BINARY_HEADER_LEN)[0]
    body_start = _BINARY_HEADER_LEN + 4
    expected = body_start + count * _BINARY_TRIANGLE_LEN
    if len(data) < expected:
        raise ValueError(
            f"Binary STL truncated: expected {expected} bytes, got {len(data)}"
        )

    pool = _VertexPool()
    normals: list[Normal] = []
    triangles: list[Tuple[int, int, int]] = []

    offset = body_start
    for _ in range(count):
        nx, ny, nz, ax, ay, az, bx, by, bz, cx, cy, cz = struct.unpack_from(
            "<12f", data, offset
        )
        offset += _BINARY_TRIANGLE_LEN
        normals.append((nx, ny, nz))
        triangles.append(
            (
                pool.add((ax, ay, az)),
                pool.add((bx, by, bz)),
                pool.add((cx, cy, cz)),
            )
        )

    return Mesh(vertices=pool.vertices, normals=normals, triangles=triangles)


def _parse_ascii(text: str) -> Mesh:
    pool = _VertexPool()
    normals: list[Normal] = []
    triangles: list[Tuple[int, int, int]] = []

    tokens = text.split()
    i = 0
    n = len(tokens)
    current_normal: Normal | None = None
    current_verts: list[Vertex] = []

    while i < n:
        tok = tokens[i].lower()
        if tok == "facet" and i + 4 < n and tokens[i + 1].lower() == "normal":
            current_normal = (
                float(tokens[i + 2]),
                float(tokens[i + 3]),
                float(tokens[i + 4]),
            )
            current_verts = []
            i += 5
        elif tok == "vertex" and i + 3 < n:
            current_verts.append(
                (
                    float(tokens[i + 1]),
                    float(tokens[i + 2]),
                    float(tokens[i + 3]),
                )
            )
            i += 4
        elif tok == "endfacet":
            if current_normal is None or len(current_verts) != 3:
                raise ValueError("Malformed ASCII STL: incomplete facet")
            normals.append(current_normal)
            triangles.append(
                (
                    pool.add(current_verts[0]),
                    pool.add(current_verts[1]),
                    pool.add(current_verts[2]),
                )
            )
            current_normal = None
            current_verts = []
            i += 1
        else:
            i += 1

    if not triangles:
        raise ValueError("ASCII STL contained no facets")
    return Mesh(vertices=pool.vertices, normals=normals, triangles=triangles)


def read_stl(source: bytes | str | Path | IO[bytes]) -> Mesh:
    """Parse an STL file into a Mesh.

    Accepts a path, raw bytes, or a binary file-like object.
    """
    if isinstance(source, (str, Path)):
        data = Path(source).read_bytes()
    elif isinstance(source, (bytes, bytearray)):
        data = bytes(source)
    else:
        data = source.read()

    if _is_binary_stl(data):
        return _parse_binary(data)
    return _parse_ascii(data.decode("utf-8", errors="replace"))


def write_stn(
    mesh: Mesh,
    destination: str | Path | IO[str],
    *,
    source_name: str = "",
    units: str = "mm",
    pretty: bool = False,
) -> None:
    """Serialize a Mesh to STN (JSON) format."""
    payload = {
        "format": "STN",
        "version": 1,
        "source": source_name,
        "units": units,
        "triangle_count": mesh.triangle_count,
        "vertices": [list(v) for v in mesh.vertices],
        "normals": [list(n) for n in mesh.normals],
        "triangles": [list(t) for t in mesh.triangles],
    }

    indent = 2 if pretty else None
    separators = (", ", ": ") if pretty else (",", ":")
    text = json.dumps(payload, indent=indent, separators=separators)

    if isinstance(destination, (str, Path)):
        Path(destination).write_text(text, encoding="utf-8")
    else:
        destination.write(text)


def convert(
    stl_path: str | Path,
    stn_path: str | Path,
    *,
    units: str = "mm",
    pretty: bool = False,
) -> Mesh:
    """Convenience: read an STL file from disk and write the STN result."""
    mesh = read_stl(stl_path)
    write_stn(
        mesh,
        stn_path,
        source_name=Path(stl_path).name,
        units=units,
        pretty=pretty,
    )
    return mesh
