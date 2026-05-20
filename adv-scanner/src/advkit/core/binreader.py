"""Memory-mapped binary reader for large .adv files.

The .adv container can exceed 500 MB, so the whole pipeline is built on a
memory-mapped view: the OS pages data in on demand and nothing is copied
until a caller explicitly slices a region. All multi-byte integers in the
.adv format observed so far are little-endian.
"""
from __future__ import annotations

import mmap
import os
import struct
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass(frozen=True)
class Region:
    """A named, half-open byte range [start, end) inside a file."""

    name: str
    start: int
    end: int
    kind: str = "unknown"
    note: str = ""

    @property
    def size(self) -> int:
        return self.end - self.start

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return (
            f"Region({self.name!r}, {self.start}..{self.end}, "
            f"size={self.size}, kind={self.kind!r})"
        )


class BinaryReader:
    """Read-only, memory-mapped cursor over a binary file.

    The reader never mutates the file. Slicing returns plain ``bytes`` only
    for the requested window, keeping peak RAM bounded regardless of file
    size.
    """

    def __init__(self, path: str | os.PathLike):
        self.path = os.fspath(path)
        self._file = open(self.path, "rb")
        self.size = os.fstat(self._file.fileno()).st_size
        if self.size == 0:
            # mmap rejects empty files; fall back to an empty buffer.
            self._mm: mmap.mmap | bytes = b""
        else:
            self._mm = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)

    # -- lifecycle ---------------------------------------------------------
    def close(self) -> None:
        if isinstance(self._mm, mmap.mmap):
            self._mm.close()
        self._file.close()

    def __enter__(self) -> "BinaryReader":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- raw access --------------------------------------------------------
    def slice(self, start: int, length: int) -> bytes:
        """Return ``length`` bytes starting at ``start`` (clamped to EOF)."""
        if start < 0 or start > self.size:
            raise ValueError(f"offset {start} outside file of size {self.size}")
        end = min(start + length, self.size)
        return bytes(self._mm[start:end])

    @property
    def buffer(self):
        """The underlying ``mmap`` (or ``bytes`` for an empty file).

        Both support ``find`` and integer indexing, which is everything the
        scanners need, while keeping access lazy/paged for large files.
        """
        return self._mm

    def find(self, needle: bytes, start: int = 0) -> int:
        """First offset of ``needle`` at/after ``start`` or -1."""
        if isinstance(self._mm, bytes):
            return self._mm.find(needle, start)
        return self._mm.find(needle, start)

    # -- typed scalar reads (little-endian) --------------------------------
    def u8(self, off: int) -> int:
        return self._mm[off]

    def u16(self, off: int) -> int:
        return struct.unpack_from("<H", self._mm, off)[0]

    def u32(self, off: int) -> int:
        return struct.unpack_from("<I", self._mm, off)[0]

    def i32(self, off: int) -> int:
        return struct.unpack_from("<i", self._mm, off)[0]

    def u64(self, off: int) -> int:
        return struct.unpack_from("<Q", self._mm, off)[0]

    def f32(self, off: int) -> float:
        return struct.unpack_from("<f", self._mm, off)[0]

    def f64(self, off: int) -> float:
        return struct.unpack_from("<d", self._mm, off)[0]

    def guid(self, off: int) -> str:
        """Read a 16-byte GUID and format it canonically.

        .adv stores GUIDs in the Microsoft mixed-endian layout (first three
        groups little-endian, last two big-endian).
        """
        raw = self.slice(off, 16)
        d1, d2, d3 = struct.unpack_from("<IHH", raw, 0)
        d4 = raw[8:10]
        d5 = raw[10:16]
        return (
            f"{d1:08x}-{d2:04x}-{d3:04x}-"
            f"{d4.hex()}-{d5.hex()}"
        )

    def pascal_string(self, off: int) -> tuple[str, int]:
        """Read a length-prefixed string: u32 length + raw bytes.

        Returns the decoded string and the offset just past it. Used for the
        job id, scan-mode and UUID fields in the .adv header.
        """
        length = self.u32(off)
        raw = self.slice(off + 4, length)
        return raw.decode("latin-1", errors="replace"), off + 4 + length


@contextmanager
def open_reader(path: str | os.PathLike):
    """Context-managed :class:`BinaryReader`."""
    reader = BinaryReader(path)
    try:
        yield reader
    finally:
        reader.close()
