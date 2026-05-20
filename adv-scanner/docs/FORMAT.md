# `.adv` File Format — Reverse-Engineering Notes

Status: **Phase 1 — partial, evidence-based.** Everything below was derived
by analysing a real sample (`2548-564-A.adv`, 47,694,840 bytes) with the
tools in this repo. Claims are graded:

- **[CONFIRMED]** — verified by decoding actual data.
- **[STRONG]** — multiple consistent signals, not yet byte-proven.
- **[OPEN]** — hypothesis; needs more samples or vendor data.

This document deliberately does **not** invent structure. Where the format
is not yet understood it says so.

---

## 1. Top-level layout `[CONFIRMED]`

The `.adv` file is a single-stream serialized object graph (no central
directory). For the analysed sample:

| Region              | Offset range            | Size     | Entropy | Content |
|---------------------|-------------------------|----------|---------|---------|
| `header + body`     | `0 – 32,013,434`        | 30.5 MB  | ~7.3    | Header, then a large uncompressed high-entropy block |
| `xray_slices`       | `32,013,434 – 45,379,863` | 12.7 MB | 7.74    | **299** grayscale JPEG slices, 1024×1280 |
| `intermediate`      | `45,379,863 – 47,034,387` | 1.6 MB  | 6.59    | Undecoded binary block |
| `preview_thumbnails`| `47,034,387 – 47,694,692` | 645 KB  | 7.47    | **~200** RGB JPEG thumbnails, 98×98 |
| `trailer`           | `47,694,692 – 47,694,840` | 148 B   | 5.23    | Tail record |

The slice/thumbnail runs are located by the marker-aware JPEG carver
(`advkit.parsers.jpeg`), not by guesswork — each stream is validated by a
full marker walk to its EOI plus a sane SOF.

## 2. Header `[CONFIRMED]`

Little-endian throughout. Fields verified against the sample:

| Offset | Type        | Value (sample)                         | Meaning |
|--------|-------------|----------------------------------------|---------|
| `0`    | GUID (16 B) | `c7289bca-ecd7-459b-aabf-e4423fef0eff` | Class / format identifier |
| `16`   | u32         | `2`                                    | Format version |
| `20`   | u32         | `filesize − 24`                        | Size field A |
| `24`   | u32         | `filesize − 76`                        | Size field B |
| `32`   | GUID (16 B) | `aa334d5d-e429-4c99-b2dc-4c2bef518995` | Secondary object GUID |
| `60`   | FILETIME (8 B) | `2026-04-03T21:49:53Z`              | Scan timestamp (Windows FILETIME) |
| `68`   | f64         | `1.842`                                | Calibration scalar (voxel spacing candidate) `[STRONG]` |
| `76–123` | f64[]     | mostly `-1.0` / `0.0`                  | AABB / transform slots, sentinel-initialised `[STRONG]` |

After the fixed block come **u32-length-prefixed strings** (a classic
MFC/`CString` serialization). Discovered in the sample:

- `"168001688475"` — job / scan id (also the source `.adv` base name)
- `"Fast"` — scan mode
- `"e88f7313-c21e-73c9-a03a-20f8ef3ebcde"` — scan UUID (appears twice)

The header also contains a run of mixed u32 fields (counts, dimensions,
and several large values in the 0.5–32 M range that look like internal
offsets) — see `[OPEN]` below.

## 3. Internal X-ray slices `[CONFIRMED]`

- 299 baseline JPEG streams, **1024×1280, 1 component (grayscale)**.
- Stored back-to-back with **no padding** between them.
- These are the internal scan images described in the business brief
  ("~300 X-ray slices"). Standard JFIF — the embedded Huffman/quantisation
  tables are the textbook tables, which is what first revealed the file
  contains JPEGs.
- One slice in the sample (index 32) is **truncated/corrupt** — it fails to
  decode. The parser flags it (`AdvFile.damaged_slices`) and the volume
  builder interpolates it from neighbours instead of crashing.

## 4. Preview thumbnails `[STRONG]`

- ~200 JPEG streams, **98×98, 3 components (RGB)**.
- Each is preceded by a **76-byte record** = nine f64 values forming a
  3×3 matrix (identity in the sample → orientation/rotation) plus a u32.
- Interpretation: multi-angle preview renders / photographs of the rough
  stone, each tagged with a view orientation.

## 5. The 30.5 MB leading body block `[OPEN]`

This is the main unknown.

- **Not** zlib/lz4/zstd compressed — no decodable streams found; the 427
  `78 9c` byte pairs are below random expectation, i.e. coincidental.
- High, fairly uniform entropy (~7.3–7.6).
- Brute-forcing image strides yields no sharp adjacent-row correlation
  peak, so it is not a simple raw `width×height` image stack.
- Working hypotheses (need more samples to decide):
  1. The merged **voxel volume** (raw `uint8`/`uint16`), possibly tiled or
     block-shuffled — which would defeat a naive stride search.
  2. A second image stack in a non-JFIF codec.
  3. The laser **outer-surface** scan (point cloud / mesh) stored in a
     packed binary form.

`adv-analyzer discover` is the tool built specifically to keep chipping at
this region.

## 6. Reverse-engineering assumptions

- Little-endian, 32-bit-offset oriented (Windows/MFC origin — GUIDs,
  FILETIME, `CString`-style strings all point that way).
- The container is **append-structured**: header → body → slice run →
  aux run. No seek table is required to extract the imagery.
- A real `.adv` may legitimately deviate (different slice count, dims,
  extra sections). The parser treats unknown regions as opaque `Region`s
  rather than failing, so it degrades gracefully on unseen revisions.

## 7. How these findings were obtained

Reproduce with:

```
adv-analyzer inspect  sample.adv     # section map + header
adv-analyzer entropy  sample.adv     # entropy profile
adv-analyzer discover sample.adv     # structure discovery on the body block
adv-analyzer hexdump  sample.adv --offset 0 --length 512
```
