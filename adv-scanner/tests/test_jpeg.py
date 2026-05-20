"""Tests for the marker-aware JPEG carver."""
import io

import numpy as np
from PIL import Image

from advkit.parsers.jpeg import carve_all, scan_jpeg


def _jpeg(w, h, mode="L", quality=70):
    arr = np.random.default_rng(0).integers(
        0, 256, (h, w) if mode == "L" else (h, w, 3), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr, mode).save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def test_scan_jpeg_measures_exact_length():
    j = _jpeg(64, 48)
    blob = j + b"\xde\xad\xbe\xef" * 100
    result = scan_jpeg(blob, 0)
    assert result is not None
    length, meta = result
    assert length == len(j)
    assert meta["width"] == 64 and meta["height"] == 48
    assert meta["components"] == 1


def test_scan_jpeg_rejects_non_soi():
    assert scan_jpeg(b"not a jpeg at all", 0) is None


def test_carve_all_finds_concatenated_streams():
    streams = [_jpeg(32, 32), _jpeg(40, 24), _jpeg(16, 64, mode="RGB")]
    blob = b"".join(streams)
    found = carve_all(blob)
    assert len(found) == 3
    assert [s.length for s in found] == [len(s) for s in streams]
    assert found[2].components == 3
    # every carved stream must decode cleanly
    for s in found:
        Image.open(io.BytesIO(blob[s.offset:s.end])).load()


def test_carve_all_skips_false_positive_soi():
    # An FF D8 FF triple buried in binary noise must not be mistaken for a JPEG.
    noise = b"\x00\xff\xd8\xff\x11\x22\x33" * 50
    real = _jpeg(48, 48)
    blob = noise + real + noise
    found = carve_all(blob)
    assert len(found) == 1
    assert found[0].width == 48


def test_carve_all_handles_padding_between_streams():
    blob = _jpeg(32, 32) + b"\x00" * 76 + _jpeg(32, 32)
    found = carve_all(blob)
    assert len(found) == 2
