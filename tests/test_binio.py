"""Tests for the binary I/O framework."""
import struct

from advrecover.binio import BinaryReader, Guid, shannon_entropy
from advrecover.format.strings import harvest_strings, planning_tree


def test_guid_roundtrip():
    text = "C7289BCA-ECD7-459B-AABF-E4423FEF0EFF"
    guid = Guid.from_string(text)
    assert str(guid) == "{" + text + "}"
    assert Guid.from_string("{" + text + "}") == guid
    assert hash(guid) == hash(Guid(guid.raw))


def test_binary_reader_scalars():
    data = struct.pack("<IHBfQ", 0xDEADBEEF, 0x1234, 0x56, 1.5, 99)
    reader = BinaryReader(data)
    assert reader.u32() == 0xDEADBEEF
    assert reader.u16() == 0x1234
    assert reader.u8() == 0x56
    assert reader.f32() == 1.5
    assert reader.u64() == 99
    assert reader.eof()


def test_binary_reader_seek_and_mfc_string():
    body = b"hello"
    data = struct.pack("<I", len(body)) + body
    reader = BinaryReader(data)
    assert reader.mfc_string() == "hello"
    reader.seek(0)
    assert reader.tell() == 0
    assert reader.peek(2) == data[:2]


def test_harvest_and_planning_tree():
    blob = (struct.pack("<I", 6) + b"Saw1-1"
            + struct.pack("<I", 6) + b"Pie3-1"
            + struct.pack("<I", 4) + b"junk")
    found = harvest_strings(blob)
    texts = [t for _o, t in found]
    assert "Saw1-1" in texts and "Pie3-1" in texts
    tree = planning_tree(found)
    assert tree == ["Saw1-1", "Pie3-1"]


def test_entropy_bounds():
    assert shannon_entropy(b"") == 0.0
    assert shannon_entropy(b"\x00" * 1000) == 0.0
    assert shannon_entropy(bytes(range(256))) > 7.9
