"""16-byte Microsoft GUID handling (mixed-endian `bytes_le` layout)."""
from __future__ import annotations

import uuid


class Guid:
    """A 16-byte GUID as stored on disk (Microsoft ``bytes_le`` layout)."""

    __slots__ = ("raw",)

    def __init__(self, raw: bytes):
        if len(raw) != 16:
            raise ValueError(f"GUID must be 16 bytes, got {len(raw)}")
        self.raw = bytes(raw)

    @classmethod
    def from_string(cls, text: str) -> "Guid":
        """Parse a canonical GUID string, with or without braces."""
        return cls(uuid.UUID(text.strip("{}")).bytes_le)

    @property
    def uuid(self) -> uuid.UUID:
        return uuid.UUID(bytes_le=self.raw)

    def is_zero(self) -> bool:
        return self.raw == b"\x00" * 16

    def __str__(self) -> str:
        return "{%s}" % str(self.uuid).upper()

    def __repr__(self) -> str:
        return f"Guid('{self}')"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Guid) and other.raw == self.raw

    def __hash__(self) -> int:
        return hash(self.raw)
