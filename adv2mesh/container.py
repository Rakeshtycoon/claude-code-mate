"""ADV container parser - file header and footer chunk table.

Recovered container layout (little-endian):

    0x00  guid[16]   file magic: c7289bca-ecd7-459b-aabf-e4423fef0eff
    0x10  u32        format version (observed value: 2)
    0x14  u32        pointer to footer chunk-table entries (== EOF-24)
    0x18  u32        pointer to footer section start       (== EOF-76)
    0x1C  u32        reserved (0)
    0x20  ...        root scene object + payload region

    footer @ [0x18]:
        guid[16]     footer section guid
        u32          reserved
        u32          chunk-table byte size
        u32          entry count
        entry[N]     { u32 chunk_id ; u64 file_offset }

Observed chunk ids:
    0  object directory table (28-byte records)
    1  root scene object (the whole payload, offset 0x20)
    3  metadata / result key-value report
    4  thumbnail JPEG set
"""
from .util import u32, u64, guid

MAGIC = bytes.fromhex("ca9b28c7d7ec9b45aabfe4423fef0eff")

CHUNK_NAMES = {
    0: "object_directory",
    1: "root_scene",
    3: "metadata",
    4: "thumbnails",
}


class ADVFormatError(Exception):
    """Raised when a file does not match the recovered .ADV layout."""


class ADVContainer:
    """Parses the outer container; gives typed access to chunks.

    This is deliberately thin - it only understands the header and the
    footer chunk index. Chunk *content* is decoded by dedicated modules
    so new chunk types can be added without touching this class.
    """

    def __init__(self, data: bytes):
        self.data = data
        if len(data) < 96 or data[:16] != MAGIC:
            raise ADVFormatError(
                "missing .ADV magic c7289bca-... (not an Advisor file?)")
        self.magic = guid(data, 0)
        self.version = u32(data, 0x10)
        self.footer_ptr = u32(data, 0x18)
        self.chunks = {}          # id -> file offset
        self._parse_footer()

    def _parse_footer(self):
        d = self.data
        p = self.footer_ptr
        if p + 28 > len(d):
            raise ADVFormatError("footer pointer out of range")
        self.footer_guid = guid(d, p)
        self.footer_table_size = u32(d, p + 20)
        count = u32(d, p + 24)
        e = p + 28
        for _ in range(count):
            if e + 12 > len(d):
                break
            cid = u32(d, e)
            off = u64(d, e + 4)
            if 0 < off < len(d) or cid == 1:
                self.chunks[cid] = off
            e += 12

    # -- convenience accessors --------------------------------------

    def chunk_offset(self, cid):
        return self.chunks.get(cid)

    def chunk_bytes(self, cid, end=None):
        """Return the raw bytes of a chunk (best-effort slice to next chunk)."""
        off = self.chunks.get(cid)
        if off is None:
            return None
        if end is None:
            later = [o for o in self.chunks.values() if o > off]
            later.append(self.footer_ptr)
            end = min(later)
        return self.data[off:end]

    def summary(self):
        return {
            "magic_guid": self.magic,
            "version": self.version,
            "size": len(self.data),
            "footer_guid": self.footer_guid,
            "chunks": {CHUNK_NAMES.get(k, "chunk_%d" % k): hex(v)
                       for k, v in sorted(self.chunks.items())},
        }
