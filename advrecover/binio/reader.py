"""A structured, seekable cursor over an in-memory byte buffer.

The reader is intentionally format-agnostic: it knows how to decode common
primitive types, GUIDs and length-prefixed strings, but nothing about the
``.ADV`` format itself.
"""
from __future__ import annotations

import struct

import numpy as np

from .guid import Guid


class BinaryReader:
    """Little-endian structured reader with a movable cursor."""

    def __init__(self, data: bytes, offset: int = 0):
        self.data = data
        self.pos = offset

    # -- cursor -------------------------------------------------------------
    def __len__(self) -> int:
        return len(self.data)

    def tell(self) -> int:
        return self.pos

    def remaining(self) -> int:
        return len(self.data) - self.pos

    def eof(self) -> bool:
        return self.pos >= len(self.data)

    def seek(self, pos: int) -> "BinaryReader":
        self.pos = pos
        return self

    def skip(self, count: int) -> "BinaryReader":
        self.pos += count
        return self

    # -- raw bytes ----------------------------------------------------------
    def read(self, count: int) -> bytes:
        chunk = self.data[self.pos:self.pos + count]
        if len(chunk) != count:
            raise EOFError(
                f"requested {count} bytes at 0x{self.pos:x}, only {len(chunk)} available"
            )
        self.pos += count
        return chunk

    def peek(self, count: int) -> bytes:
        return self.data[self.pos:self.pos + count]

    # -- scalars ------------------------------------------------------------
    def _unpack(self, fmt: str, size: int):
        value = struct.unpack_from(fmt, self.data, self.pos)[0]
        self.pos += size
        return value

    def u8(self) -> int:
        return self._unpack("<B", 1)

    def u16(self) -> int:
        return self._unpack("<H", 2)

    def u32(self) -> int:
        return self._unpack("<I", 4)

    def u64(self) -> int:
        return self._unpack("<Q", 8)

    def i16(self) -> int:
        return self._unpack("<h", 2)

    def i32(self) -> int:
        return self._unpack("<i", 4)

    def i64(self) -> int:
        return self._unpack("<q", 8)

    def f32(self) -> float:
        return self._unpack("<f", 4)

    def f64(self) -> float:
        return self._unpack("<d", 8)

    # -- compound -----------------------------------------------------------
    def guid(self) -> Guid:
        return Guid(self.read(16))

    def filetime(self) -> int:
        """Read a Windows FILETIME (100 ns ticks since 1601-01-01)."""
        return self.u64()

    def mfc_string(self, encoding: str = "latin-1") -> str | None:
        """Read a ``u32`` length-prefixed string. ``0xFFFFFFFF`` => ``None``."""
        length = self.u32()
        if length == 0xFFFFFFFF:
            return None
        return self.read(length).decode(encoding, errors="replace")

    def array_f32(self, count: int) -> np.ndarray:
        return np.frombuffer(self.read(count * 4), dtype="<f4")

    def array_u32(self, count: int) -> np.ndarray:
        return np.frombuffer(self.read(count * 4), dtype="<u4")

    def view(self, offset: int, size: int) -> "BinaryReader":
        """Return an independent reader over a sub-range of this buffer."""
        return BinaryReader(self.data[offset:offset + size])
