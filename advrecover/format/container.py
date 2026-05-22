"""Parser for the ``.ADV`` container: header, end directory, sections.

This is the verified backbone of the format. Anything it cannot interpret is
recorded as an :class:`UnknownBlock` rather than silently dropped.
"""
from __future__ import annotations

from ..binio.reader import BinaryReader
from . import constants as C
from .model import (
    AdvDocument,
    MainModel,
    PreviewImage,
    Section,
    SectionEntry,
    UnknownBlock,
)
from .strings import UUID_RE, harvest_strings, planning_tree


class AdvParseError(Exception):
    """Raised when a file is not a recognisable ``.ADV`` container."""


def parse_file(path: str) -> AdvDocument:
    """Parse a ``.ADV`` file from disk into an :class:`AdvDocument`."""
    with open(path, "rb") as fh:
        data = fh.read()
    return parse_bytes(data, path)


def parse_bytes(data: bytes, path: str = "<memory>") -> AdvDocument:
    """Parse ``.ADV`` bytes into an :class:`AdvDocument`."""
    reader = BinaryReader(data)

    magic = reader.guid()
    if magic != C.ADV_MAGIC:
        raise AdvParseError(f"bad magic {magic}, expected {C.ADV_MAGIC}")

    version = reader.u32()
    footer_offset_a = reader.u32()
    directory_offset = reader.u32()
    reader.u32()  # reserved, always 0 in samples

    doc = AdvDocument(
        path=path,
        file_size=len(data),
        magic=magic,
        version=version,
        directory_offset=directory_offset,
        footer_offset_a=footer_offset_a,
        directory_guid=C.DIRECTORY_MAGIC,
    )
    if version != C.SUPPORTED_VERSION:
        doc.warnings.append(
            f"version {version} differs from verified version {C.SUPPORTED_VERSION}"
        )

    _parse_directory(data, doc)
    _resolve_section_ranges(data, doc)
    _parse_main_model(data, doc)
    _carve_previews(data, doc)
    return doc


def _parse_directory(data: bytes, doc: AdvDocument) -> None:
    if not 0 <= doc.directory_offset < len(data):
        raise AdvParseError(f"directory offset 0x{doc.directory_offset:x} out of range")

    reader = BinaryReader(data, doc.directory_offset)
    dir_guid = reader.guid()
    if dir_guid != C.DIRECTORY_MAGIC:
        doc.warnings.append(f"unexpected directory GUID {dir_guid}")
    doc.directory_guid = dir_guid

    reader.u32()             # flags (0)
    reader.u32()             # payload size
    entry_count = reader.u32()
    if entry_count > 4096:
        raise AdvParseError(f"implausible entry count {entry_count}")

    for _ in range(entry_count):
        doc.entries.append(SectionEntry(reader.u32(), reader.u32(), reader.u32()))


def _resolve_section_ranges(data: bytes, doc: AdvDocument) -> None:
    """Turn directory entries into sections with computed byte ranges."""
    # Boundaries: every section start plus the directory start (upper bound).
    starts = sorted({e.offset for e in doc.entries} | {doc.directory_offset})
    for entry in doc.entries:
        if entry.offset + 16 > len(data):
            doc.warnings.append(f"section id {entry.section_id} offset out of range")
            continue
        end = next((s for s in starts if s > entry.offset), doc.file_size)
        class_guid = BinaryReader(data, entry.offset).guid()
        doc.sections.append(
            Section(
                section_id=entry.section_id,
                offset=entry.offset,
                end=end,
                guid=class_guid,
                role=C.SECTION_ROLE.get(entry.section_id, "unknown"),
            )
        )
    doc.sections.sort(key=lambda s: s.offset)


def _parse_main_model(data: bytes, doc: AdvDocument) -> None:
    section = doc.section(1)
    if section is None or section.guid != C.SECTION_MAIN_MODEL:
        doc.warnings.append("main model section (id 1) missing or mis-tagged")
        return

    reader = BinaryReader(data, section.payload_offset)
    model = MainModel(
        tag=reader.u32(),
        count_a=reader.u32(),
        count_b=reader.u32(),
        timestamp_ticks=reader.u64(),
    )

    # The metadata + planning strings live throughout the section; harvest
    # them from the header region (first 64 KiB is ample for metadata) and
    # the whole section for the planning tree.
    header_strings = harvest_strings(
        data[section.offset:section.offset + 65536], base=section.offset
    )
    model.strings = header_strings
    _assign_metadata(model, header_strings)

    section_bytes = data[section.offset:section.end]
    model.planning_tree = planning_tree(
        harvest_strings(section_bytes, base=section.offset, min_len=4, max_len=32)
    )
    doc.main_model = model


def _assign_metadata(model: MainModel, strings: list[tuple[int, str]]) -> None:
    for _off, text in strings:
        if UUID_RE.match(text) and not model.document_uuid:
            model.document_uuid = text
        elif text.endswith("(WH)") and not model.stone_id:
            model.stone_id = text
        elif text in ("Accurate", "Fast", "Standard") and not model.scan_mode:
            model.scan_mode = text
        elif "-" in text and len(text) <= 12 and not model.plan_code \
                and not text[0].isdigit() and not text.startswith(("Saw", "Pie")):
            model.plan_code = text


def _carve_previews(data: bytes, doc: AdvDocument) -> None:
    """Carve embedded JPEG previews out of section 4."""
    section = doc.section(4)
    if section is None:
        return
    blob = data[section.offset:section.end]
    cursor = 0
    while True:
        soi = blob.find(C.JPEG_SOI, cursor)
        if soi == -1:
            break
        eoi = blob.find(b"\xff\xd9", soi)
        if eoi == -1:
            doc.unknown_blocks.append(
                UnknownBlock(section.offset + soi, len(blob) - soi,
                             "JPEG start without end-of-image marker")
            )
            break
        end = eoi + 2
        doc.previews.append(PreviewImage(section.offset + soi, blob[soi:end]))
        cursor = end
