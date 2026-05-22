"""Planning-element record parser.

Each ``Saw`` / ``Pie`` planning element is preceded in the file by a fixed
60-byte record:

```
u32      tag            element class tag (84/85/86 = active records)
u32      element_id     sequential id
f64      fixed          a constant (~54.0) - reserved / reference angle
f64      offset         signed plane offset, in microns
f64      reserved       constant 0.0
f64[3]   normal         unit normal vector  (verified |n| == 1)
u32                     trailing marker (== 1)
[u32 name_len][name]    the element name follows immediately
```

Verified across the sample set: ``normal`` is a true unit vector, so a
``Saw`` element defines the cutting plane ``normal . x == offset`` and a
``Pie`` element defines a planned stone's orientation + position. This is
the basis of the parametric ("Path B") reconstruction.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

from ..binio.guid import Guid  # noqa: F401  (kept for downstream callers)
from .model import AdvDocument
from .strings import harvest_strings

RECORD_SIZE = 60
_ACTIVE_TAGS = (84, 85, 86)


@dataclass
class PlanningElement:
    """One decoded ``Saw`` / ``Pie`` planning element."""

    name: str
    kind: str                       # "saw" or "pie"
    tag: int
    element_id: int
    fixed: float                    # ~54.0 constant
    offset: float                   # signed plane offset (microns)
    reserved: float                 # constant 0.0
    normal: tuple[float, float, float]

    @property
    def solution(self) -> str:
        """The planning-solution group, e.g. ``Saw133-1`` -> ``133``."""
        digits = "".join(c for c in self.name[3:].split("-")[0] if c.isdigit())
        return digits or "?"


def _unit(v: tuple[float, float, float]) -> tuple[float, float, float] | None:
    norm = (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) ** 0.5
    if not 0.98 < norm < 1.02:
        return None
    return (v[0] / norm, v[1] / norm, v[2] / norm)


def parse_elements(data: bytes, doc: AdvDocument,
                   dedupe: bool = True) -> list[PlanningElement]:
    """Decode every ``Saw`` / ``Pie`` planning element record.

    A record is accepted only when its trailing 3 doubles form a unit
    vector, which reliably rejects mis-aligned / inactive records.
    """
    section = doc.section(1)
    if section is None:
        return []

    strings = harvest_strings(data[section.offset:section.end],
                              base=section.offset, min_len=4, max_len=24)
    elements: list[PlanningElement] = []
    seen: set[tuple] = set()

    for name_offset, name in strings:
        if name[:3] not in ("Saw", "Pie"):
            continue
        record = name_offset - RECORD_SIZE
        if record < section.offset:
            continue
        tag, element_id = struct.unpack_from("<II", data, record)
        if tag not in _ACTIVE_TAGS:
            continue
        d = struct.unpack_from("<6d", data, record + 8)
        normal = _unit((d[3], d[4], d[5]))
        if normal is None:
            continue

        if dedupe:
            key = (name, round(d[1], 2),
                   tuple(round(x, 4) for x in normal))
            if key in seen:
                continue
            seen.add(key)

        elements.append(PlanningElement(
            name=name,
            kind="saw" if name.startswith("Saw") else "pie",
            tag=tag,
            element_id=element_id,
            fixed=d[0],
            offset=d[1],
            reserved=d[2],
            normal=normal,
        ))
    return elements
