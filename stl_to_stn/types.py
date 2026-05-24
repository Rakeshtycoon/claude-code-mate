"""Data types shared across the STL/STN pipeline."""

from dataclasses import dataclass, field
from typing import List, Tuple

Vertex = Tuple[float, float, float]
Normal = Tuple[float, float, float]
Triangle = Tuple[int, int, int]


@dataclass
class Mesh:
    """A triangle mesh with de-duplicated vertices."""

    vertices: List[Vertex] = field(default_factory=list)
    normals: List[Normal] = field(default_factory=list)
    triangles: List[Triangle] = field(default_factory=list)

    @property
    def triangle_count(self) -> int:
        return len(self.triangles)
