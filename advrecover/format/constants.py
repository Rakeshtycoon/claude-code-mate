"""Known GUIDs and magic values for the OctoNus Advisor ``.ADV`` format.

Every constant here was observed in real sample files. See
``docs/ADV_FORMAT.md`` for the evidence behind each one.
"""
from __future__ import annotations

from ..binio.guid import Guid

# Container-level identifiers ------------------------------------------------
ADV_MAGIC = Guid.from_string("C7289BCA-ECD7-459B-AABF-E4423FEF0EFF")
DIRECTORY_MAGIC = Guid.from_string("D2C5B50A-770C-4ED1-82F7-ADFD41A3C2E6")
SUPPORTED_VERSION = 2

# Section class GUIDs --------------------------------------------------------
SECTION_MAIN_MODEL = Guid.from_string("AA334D5D-E429-4C99-B2DC-4C2BEF518995")
SECTION_INDEX_META = Guid.from_string("928794CB-9096-4545-95AE-3CBF593FAE69")
SECTION_SUBDOC = Guid.from_string("866ACCE4-57EC-401E-B0A4-A6D48A687D84")
SECTION_PREVIEWS = Guid.from_string("511059A4-4997-46DA-A7AE-63BD206014A1")

# GUIDs seen nested inside sections (roles still under investigation) --------
NESTED_SUBDOC = Guid.from_string("5A888D07-AB1B-4B63-BA1B-6D11FCC46746")
NESTED_B84937EA = Guid.from_string("B84937EA-2A89-4DCC-9342-168B76CBD989")
NESTED_CLOUD = Guid.from_string("89B2F295-9627-483B-A7A2-00CBA02F27AB")  # 3-D cloud serialization wrapper

#: Human-readable names, keyed by GUID. Used by the diagnostics panel.
GUID_NAMES: dict[Guid, str] = {
    ADV_MAGIC: "ADV container magic",
    DIRECTORY_MAGIC: "End directory",
    SECTION_MAIN_MODEL: "Main model section",
    SECTION_INDEX_META: "Index / metadata section",
    SECTION_SUBDOC: "Sub-document section",
    SECTION_PREVIEWS: "Embedded JPEG previews section",
    NESTED_SUBDOC: "Sub-document (nested)",
    NESTED_B84937EA: "Unclassified nested object",
    NESTED_CLOUD: "3-D point cloud serialization",
}

# ZIP local-file-header signature; section[1] is a concatenation of ZIPs.
ZIP_LFH_MAGIC = b"PK\x03\x04"

#: Role tag per section id (HYPOTHESIS where the payload is not yet decoded).
SECTION_ROLE: dict[int, str] = {
    0: "index_meta",
    1: "main_model",
    3: "subdocument",
    4: "previews",
}

# Coordinates in ``.ADV`` geometry arrays are expressed in microns.
MICRONS_PER_MM = 1000.0

# JPEG / JFIF start-of-image marker, used to carve embedded previews.
JPEG_SOI = b"\xff\xd8\xff"


def guid_name(guid: Guid) -> str:
    """Return a friendly name for a GUID, or the raw GUID string."""
    return GUID_NAMES.get(guid, str(guid))
