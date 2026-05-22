"""Binary probe — the primary reverse-engineering diagnostic.

Given any ``.ADV`` file (or arbitrary bytes) it reports entropy, GUID
occurrences, string content and float-array geometry, so unknown regions can
be investigated and the format spec extended.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..binio.guid import Guid
from ..binio.hexdump import entropy_profile, shannon_entropy
from ..format import constants as C
from ..format.strings import harvest_strings
from ..recon.scan import overall_bbox, scan_geometry, total_points


@dataclass
class GuidHit:
    guid: Guid
    offset: int
    name: str


@dataclass
class ProbeReport:
    path: str
    size: int
    overall_entropy: float
    entropy_profile: list[tuple[int, float]] = field(default_factory=list)
    guid_hits: list[GuidHit] = field(default_factory=list)
    string_count: int = 0
    sample_strings: list[tuple[int, str]] = field(default_factory=list)
    geometry_runs: int = 0
    geometry_points: int = 0
    geometry_bbox: tuple | None = None

    def render(self) -> str:
        out = [
            f"PROBE  {self.path}",
            f"  size            {self.size:,} bytes",
            f"  overall entropy {self.overall_entropy:.3f} bits/byte",
            "  entropy profile (offset: entropy):",
        ]
        for off, ent in self.entropy_profile:
            bar = "#" * int(ent * 5)
            out.append(f"    0x{off:08x}  {ent:5.2f}  {bar}")
        out.append(f"  GUID occurrences ({len(self.guid_hits)}):")
        for hit in self.guid_hits:
            out.append(f"    0x{hit.offset:08x}  {hit.guid}  {hit.name}")
        out.append(f"  strings: {self.string_count} found")
        for off, text in self.sample_strings:
            out.append(f"    0x{off:08x}  {text!r}")
        out.append(f"  geometry: {self.geometry_runs} float32 XYZ runs, "
                    f"{self.geometry_points:,} points")
        if self.geometry_bbox is not None:
            lo, hi = self.geometry_bbox
            out.append(f"    bbox min={lo.round(1).tolist()} max={hi.round(1).tolist()}")
        return "\n".join(out)


def _scan_known_guids(data: bytes) -> list[GuidHit]:
    hits: list[GuidHit] = []
    for guid, name in C.GUID_NAMES.items():
        cursor = 0
        while True:
            pos = data.find(guid.raw, cursor)
            if pos == -1:
                break
            hits.append(GuidHit(guid, pos, name))
            cursor = pos + 1
    return sorted(hits, key=lambda h: h.offset)


def probe(data: bytes, path: str = "<memory>", entropy_blocks: int = 24,
          max_strings: int = 40) -> ProbeReport:
    """Run every diagnostic over ``data`` and return a :class:`ProbeReport`."""
    strings = harvest_strings(data, min_len=3, max_len=128)
    arrays = scan_geometry(data, min_points=32)
    report = ProbeReport(
        path=path,
        size=len(data),
        overall_entropy=shannon_entropy(data[:1 << 20]),
        entropy_profile=entropy_profile(data, entropy_blocks),
        guid_hits=_scan_known_guids(data),
        string_count=len(strings),
        sample_strings=strings[:max_strings],
        geometry_runs=len(arrays),
        geometry_points=total_points(arrays),
        geometry_bbox=overall_bbox(arrays),
    )
    return report


def probe_file(path: str) -> ProbeReport:
    with open(path, "rb") as fh:
        return probe(fh.read(), path)
