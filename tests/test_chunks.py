"""Tests for the per-element chunk parser."""
import os
import struct

from advrecover.re_tools.chunks import (
    compare_chunk_tables,
    find_chunks,
    render_chunk_table,
)


def _chunked_blob(n: int = 5) -> bytes:
    """n records, each a low-entropy header + a high-entropy body."""
    out = b""
    for i in range(n):
        header = struct.pack("<I", i + 1) + b"\x00" * 4092      # 4 KB, low entropy
        body = os.urandom(32768)                                # 32 KB, max entropy
        out += header + body
    return out


def test_find_chunks_locates_records():
    chunks = find_chunks(_chunked_blob(5), 0, 5 * 36864, window=2048)
    assert len(chunks) == 5
    for i, chunk in enumerate(chunks):
        assert chunk.index == i
        assert chunk.body_entropy > 7.0      # compressed body detected


def test_chunk_header_id_decoded():
    chunks = find_chunks(_chunked_blob(3), 0, 3 * 36864, window=2048)
    assert [c.header_id for c in chunks] == [1, 2, 3]


def test_compare_chunk_tables_reports_differences():
    a = find_chunks(_chunked_blob(3), 0, 3 * 36864, window=2048)
    b = find_chunks(_chunked_blob(3), 0, 3 * 36864, window=2048)
    report = compare_chunk_tables(a, b)
    assert report[0].startswith("chunk count: A=3  B=3")


def test_render_chunk_table_is_text():
    chunks = find_chunks(_chunked_blob(2), 0, 2 * 36864, window=2048)
    assert "PER-ELEMENT CHUNK TABLE" in render_chunk_table(chunks)
