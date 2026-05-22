"""Tests for entropy segmentation and the block map."""
import os

from advrecover.re_tools.segment import block_map, render_segments, segment_file


def _mixed_blob() -> bytes:
    zeros = b"\x00" * 32768                       # padding
    structured = (b"ABCD" * 8192)                 # low entropy
    compressed = os.urandom(32768)                # near-max entropy
    return zeros + structured + compressed


def test_segment_file_splits_regions():
    segments = segment_file(_mixed_blob(), window=4096)
    kinds = {s.kind for s in segments}
    assert "padding" in kinds
    assert "compressed" in kinds


def test_padding_has_zero_confidence():
    segments = segment_file(b"\x00" * 65536, window=4096)
    assert all(s.kind == "padding" for s in segments)
    assert all(s.geometry_confidence == 0.0 for s in segments)


def test_compressed_block_low_confidence():
    segments = segment_file(os.urandom(65536), window=4096)
    assert all(s.kind == "compressed" for s in segments)
    assert all(s.geometry_confidence < 0.2 for s in segments)


def test_block_map_is_confidence_sorted():
    segments = block_map(_mixed_blob(), window=4096)
    confidences = [s.geometry_confidence for s in segments]
    assert confidences == sorted(confidences, reverse=True)


def test_render_is_text():
    out = render_segments(segment_file(_mixed_blob(), window=4096))
    assert "FILE SEGMENTS" in out
