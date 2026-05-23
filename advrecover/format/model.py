"""Plain data classes describing a parsed ``.ADV`` document.

These objects carry *only* decoded data — no parsing logic — so they can be
freely passed to the reconstruction engine, exporter, viewer and tests.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from ..binio.guid import Guid

# Windows FILETIME epoch (1601-01-01) relative to the Unix epoch.
_FILETIME_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)


def filetime_to_datetime(ticks: int) -> datetime | None:
    """Convert a Windows FILETIME (100 ns ticks) to a ``datetime``."""
    if ticks <= 0:
        return None
    try:
        return _FILETIME_EPOCH + timedelta(microseconds=ticks / 10)
    except (OverflowError, OSError):
        return None


@dataclass
class SectionEntry:
    """One row of the end directory."""

    section_id: int
    offset: int
    reserved: int


@dataclass
class Section:
    """A GUID-tagged section with a computed byte range."""

    section_id: int
    offset: int
    end: int
    guid: Guid
    role: str = "unknown"

    @property
    def size(self) -> int:
        return self.end - self.offset

    @property
    def payload_offset(self) -> int:
        """First byte after the 16-byte class GUID."""
        return self.offset + 16


@dataclass
class UnknownBlock:
    """A byte range the parser could not interpret — kept for inspection."""

    offset: int
    size: int
    note: str = ""


@dataclass
class MainModel:
    """Decoded header of the main-model section (id 1)."""

    tag: int = 0
    count_a: int = 0
    count_b: int = 0
    timestamp_ticks: int = 0
    stone_id: str = ""
    plan_code: str = ""
    scan_mode: str = ""
    document_uuid: str = ""
    strings: list[tuple[int, str]] = field(default_factory=list)
    planning_tree: list[str] = field(default_factory=list)

    @property
    def created(self) -> datetime | None:
        return filetime_to_datetime(self.timestamp_ticks)


@dataclass
class PreviewImage:
    """An embedded JPEG preview carved from section 4."""

    offset: int
    data: bytes


@dataclass
class AdvDocument:
    """The complete parsed result for one ``.ADV`` file."""

    path: str
    file_size: int
    magic: Guid
    version: int
    directory_offset: int
    footer_offset_a: int
    directory_guid: Guid
    entries: list[SectionEntry] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    main_model: MainModel | None = None
    previews: list[PreviewImage] = field(default_factory=list)
    clouds: list = field(default_factory=list)        # list[CloudEntry]
    unknown_blocks: list[UnknownBlock] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def section(self, section_id: int) -> Section | None:
        for sec in self.sections:
            if sec.section_id == section_id:
                return sec
        return None
