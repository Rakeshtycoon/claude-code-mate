"""Typed chunk decoders.

Currently implemented:
  * metadata         (chunk id 3) - key/value result report
  * object_directory (chunk id 0) - 28-byte object index records

To add a new chunk decoder, write a function that takes the chunk's raw
bytes and returns a plain dict/list, then register it in `decode_chunk`.
"""
import re
import struct
from .util import u32, u64, read_ascii


def decode_metadata(blob):
    """Decode the metadata chunk into {dotted.key: value} plus an ordered list.

    The chunk is a flat run of length-prefixed strings. Each logical entry is
    (display label, dotted internal key, unit, value...). We collect every
    string in order, then for each dotted key take the next numeric string
    as its value - robust against the exact per-entry layout.
    """
    strings = []
    i = 0
    n = len(blob)
    while i < n - 4:
        ln = u32(blob, i)
        if 1 <= ln <= 200 and i + 4 + ln <= n:
            chunk = blob[i + 4:i + 4 + ln]
            if all(32 <= b < 127 for b in chunk):
                strings.append(chunk.decode("ascii"))
                i += 4 + ln
                continue
        i += 1

    # Each entry is roughly (label, dotted-key, [unit], [sep], value). The
    # value may be numeric ("0.097") or text ("WH", "ROUND"); units and
    # one-char type codes are skipped.
    kv = {}
    skip = {"ct", "$", "%", " ", "", "#", "!", "&", "(", ")", "'", '"',
            "<", ">", "*", "+"}
    for idx, s in enumerate(strings):
        if "." in s and re.search(r"[A-Za-z]", s):  # dotted internal key
            for nxt in strings[idx + 1:idx + 5]:
                if nxt in skip or len(nxt) <= 1:   # unit / one-char type code
                    continue
                if "." in nxt and re.search(r"[A-Za-z]", nxt):
                    continue                          # next key, value absent
                kv[s] = nxt
                break
    return {"key_values": kv, "strings": strings}


def decode_object_directory(blob):
    """Decode chunk 0 - a table of 28-byte (7 x u32) object index records.

    Field semantics are only partly recovered; record[1] and record[3] are
    file offsets / ids, the rest are type/index counters.
    """
    records = []
    # header: guid(16) + u32 + u32(size) + u32 ; records follow after +4
    base = 32
    while base + 28 <= len(blob):
        rec = struct.unpack_from("<7I", blob, base)
        records.append({
            "field0": rec[0], "ref_a": rec[1], "field2": rec[2],
            "ref_b": rec[3], "field4": rec[4], "field5": rec[5],
            "field6": rec[6],
        })
        base += 28
    return records


def decode_chunk(cid, blob):
    """Dispatch a chunk id to its decoder; returns None for unknown ids."""
    if blob is None:
        return None
    if cid == 3:
        return decode_metadata(blob)
    if cid == 0:
        return decode_object_directory(blob)
    return None
