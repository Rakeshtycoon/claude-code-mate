"""Reverse-engineering diagnostics: probe, binary diff, entropy segmentation."""
from .chunks import (
    ElementChunk,
    chunk_table,
    compare_chunk_tables,
    find_chunks,
    render_chunk_table,
)
from .diff import DiffRegion, common_prefix, diff_regions
from .probe import ProbeReport, probe, probe_file
from .segment import Segment, block_map, render_segments, segment_file

__all__ = [
    "probe",
    "probe_file",
    "ProbeReport",
    "diff_regions",
    "common_prefix",
    "DiffRegion",
    "segment_file",
    "block_map",
    "render_segments",
    "Segment",
    "chunk_table",
    "find_chunks",
    "compare_chunk_tables",
    "render_chunk_table",
    "ElementChunk",
]
