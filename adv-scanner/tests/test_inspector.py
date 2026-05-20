"""Tests for the low-level binary inspector."""
import struct

from advkit.parsers.inspector import (
    detect_signatures,
    entropy_profile,
    find_repeats,
    hexdump,
    probe_numeric,
    shannon_entropy,
)


def test_entropy_bounds():
    assert shannon_entropy(b"") == 0.0
    assert shannon_entropy(b"\x00" * 1000) == 0.0          # constant -> 0
    full = bytes(range(256)) * 4
    assert abs(shannon_entropy(full) - 8.0) < 1e-9         # uniform -> 8


def test_entropy_profile_windows():
    buf = b"\x00" * 100000 + bytes(range(256)) * 400
    prof = entropy_profile(buf, window=65536)
    assert prof[0].entropy < 1.0
    assert prof[0].classification == "padding/constant"
    assert prof[-1].entropy > 7.0


def test_detect_signatures_finds_magic():
    buf = b"....\x1f\x8b....\x28\xb5\x2f\xfd...."
    hits = dict((name, off) for off, name in detect_signatures(buf))
    assert "gzip" in hits and "zstd" in hits


def test_probe_numeric_identifies_float64():
    values = [float(i) * 0.5 for i in range(200)]
    buf = b"\x00" * 8 + struct.pack("<200d", *values)
    guesses = probe_numeric(buf, 8, len(buf), lo=-1e3, hi=1e3)
    assert guesses["float64"].finite_ratio == 1.0
    assert guesses["float64"].in_range_ratio == 1.0
    assert guesses["float64"].plausible


def test_find_repeats_detects_constant_run():
    buf = b"AB" * 3 + b"\x7f\xff" * 50 + b"CD" * 3
    runs = find_repeats(buf, 0, len(buf), unit=2, min_run=8)
    assert any(token == b"\x7f\xff" and count == 50 for _, count, token in runs)


def test_hexdump_format():
    out = hexdump(b"\x00\x01\x02ABC", 0, 8)
    assert out.startswith("00000000  ")
    assert "|" in out
