# `.ADV` File Format — Reverse-Engineered Specification

Status: **v0.1 — derived from real samples.** Every field below is marked
`VERIFIED` (observed consistently across both sample files) or `HYPOTHESIS`
(plausible but not yet proven). Nothing here is guessed without evidence.

Producer: **OctoNus Advisor 7.601 Professional Edition** (diamond rough
planning software). Confirmed from the application window title in the
screen-recordings supplied alongside the samples.

Samples used:

| File | Size | Stone | Matching video |
|------|------|-------|----------------|
| `f7864efb-967.adv` | 28,307,011 B | `330-967(GA)(WH)` | `5f69c808-967.mp4` |
| `b8968c0b-978.adv` | 18,842,959 B | `330-978(GA)(WH)` | *(none — video A is 330-959)* |

All multi-byte integers are **little-endian**. Floats are IEEE-754
**float32 little-endian** unless noted.

---

## 1. Container layout

```
+0x00  GUID    magic            VERIFIED  {C7289BCA-ECD7-459B-AABF-E4423FEF0EFF}
+0x10  u32     version          VERIFIED  = 2
+0x14  u32     footer_offset_a  VERIFIED  points 24 B before EOF (into entry table)
+0x18  u32     directory_offset VERIFIED  points to the end directory GUID
+0x1C  u32     reserved         VERIFIED  = 0
+0x20  ...     Section #1 payload begins (main model)
```

GUIDs are stored in Microsoft mixed-endian layout (`bytes_le`): first three
fields little-endian, last 8 bytes big-endian.

## 2. End directory

Located at `directory_offset` (near EOF):

```
GUID    directory magic   VERIFIED  {D2C5B50A-770C-4ED1-82F7-ADFD41A3C2E6}
u32     flags             VERIFIED  = 0
u32     payload_size      VERIFIED  = 0x34 (covers entry_count + entries)
u32     entry_count       VERIFIED  = 4
entry_count x SectionEntry:
    u32  section_id       VERIFIED
    u32  file_offset      VERIFIED  absolute offset of the section
    u32  reserved         VERIFIED  = 0
```

## 3. Sections

Each section begins with a 16-byte **class GUID**. Section byte ranges are
derived by sorting all section offsets plus `directory_offset`.

| id | GUID | Role | Confidence |
|----|------|------|------------|
| 1 | `{AA334D5D-E429-4C99-B2DC-4C2BEF518995}` | Main model (geometry + planning) | VERIFIED |
| 0 | `{928794CB-9096-4545-95AE-3CBF593FAE69}` | Index / metadata block | VERIFIED guid, HYPOTHESIS role |
| 3 | `{866ACCE4-57EC-401E-B0A4-A6D48A687D84}` | Sub-document (nests `{5A888D07-…}`) | VERIFIED guid, HYPOTHESIS role |
| 4 | `{511059A4-4997-46DA-A7AE-63BD206014A1}` | Embedded JPEG preview images | VERIFIED (JFIF `FF D8 FF E0` found) |

## 4. Main model section (id 1)

Header begins immediately after the section GUID (file offset `0x30`):

```
u32   tag           VERIFIED  = 9
u32   const_a       VERIFIED  = 61809  (identical in both samples -> a
                                        format constant, NOT a point count)
u32   const_b       VERIFIED  = 2359   (identical in both samples -> constant)
u64   timestamp     VERIFIED  Windows FILETIME (creation time)
float[] transform   HYPOTHESIS  rotation/bounds block
...
u32 = 0xFFFFFFFF    VERIFIED  sentinel preceding the metadata string block
```

### Metadata string block

Strings are **length-prefixed**: `u32 length` + `length` ASCII bytes
(`0xFFFFFFFF` length = null string). Verified strings, in order:

* Stone id — `330-967(GA)(WH)` / `330-978(GA)(WH)`
* `DV`
* `P77-JK` — cut/plan code
* `Accurate` — scan model accuracy mode
* Document UUID — e.g. `0eecb8c9-f14a-456a-9fac-ef161e7134b7`

### Planning tree

The string table further down enumerates the planning operations:

* `Saw<n>-<m>` — **saw / cutting planes** (where the rough is cut)
* `Pie<n>-<m>` — **pieces** (planned polished stones)
* `Mea` — measurement

## 5. Geometry encoding — VERIFIED (across 20 sample files)

Plainly-stored geometry is a contiguous list of **contour records**:

```
repeat:
    u32      point_count
    float32  xyz[point_count * 3]      coordinate unit = microns
```

The `u32 point_count` sits immediately before each point block. ~45 such
records exist per file, ~360–375 points each.

**Verified by PCA + SHA-256 comparison across 20 files:**

* Every contour record is **planar**; all records share a single common
  plane (thin-axis extent ≈ 8 µm vs ≈ 8 mm in-plane).
* The contour bytes are **identical across completely different stones** —
  e.g. `978`≡`985`, `330-3826`≡`330-3830`, `967`≡`330-3858`,
  `330-3820`≡`330-4332` all hash-match. There are only a handful of
  distinct variants.

Therefore the contour block is a **shared cut-template library** (a standard
facet/cross-section diagram selected per cut type) — it is **not** per-stone
geometry. A full-section scan in float32 *and* float64 finds **zero**
volumetric point arrays. The real rough/polished/plane meshes are not stored
as plain floating-point data; they are in the encoded regions of §6.

## 6. File block map — VERIFIED by entropy segmentation

The main-model section is **not** one monolithic block. Fine-grained entropy
segmentation (`advrecover segment`) reveals a consistent layout across all
sampled files. Offsets below are for `967.adv`; other files keep the
pattern and differ only in block sizes.

| Range | Size | Entropy | Block kind | Decodable? |
|-------|------|---------|------------|------------|
| `0x000000–0x00E000` | 57 KB | ~3.0 | header / metadata / strings | **yes** — done |
| `0x010000–0x0B0000` | 640 KB | ~7.99 | high-entropy block A | no — encoded |
| `0x0B0000–0x2B0000` | 2.0 MB | ~6.28 | plain float32 contour template | **yes** — decoded |
| `0x2C0000–0xC00000` | ~9.7 MB | ~7.97 | large high-entropy block | no — encoded |
| `0xC00000–0xC60000` | 393 KB | ~5.7 | structured (planning tree) | partly — strings |
| `0xCA0000–0x18B0000` | ~12 MB | 7.2–7.6 | ~350 per-element chunks | partial — §6a |
| `0x18B0000–EOF` | ~0.7 MB | mixed | trailing data + zero padding | partial |

**Encrypted or compressed? — answered by a uniformity test.** Reference:
true-random / encrypted data scores chi² ≈ 258 (a byte histogram of 256
bins). Measured on `967.adv`:

| Region | entropy | chi² | serial-corr | verdict |
|--------|---------|------|-------------|---------|
| `0x010000` block | 7.995 | 3,780 | +0.03 | **not encrypted** — structured |
| `0x2C0000` 9.7 MB block | 7.985 | 92,824 | +0.00 | **not encrypted** — structured |
| per-element chunk body | 7.496 | 115,424 | **+0.28** | **not encrypted** — raw structured data |

The high-entropy blocks are therefore **not encrypted** and **not** framed
with any standard codec (zlib/gzip/bz2/lzma/lz4/zstd all fail at every
offset). They are a **proprietary encoding** — most likely an arithmetic/
range-coded stream or packed scan imagery (the per-element body's +0.28
serial correlation rules out both compression and encryption).

> The `"CRL"` bytes noted in an earlier revision were a **coincidence** —
> present in only 9 of 18 files, at random offsets. Not a magic number.

Conclusion: the true 3-D meshes live in the proprietary-encoded regions.
Decoding them realistically requires the Advisor application/DLLs to observe
the decoder. Sample-only analysis has now been pushed to its limit: 20 files
pinned the structure precisely but cannot reveal the codec itself.

## 6a. Per-element chunk table — PARTIALLY DECODED

The `0xCA0000–0x18B0000` region is a table of per-element records, one per
`Saw`/`Pie` planning element. `advrecover chunks` segments it:

* **347 chunks** in `967.adv`, **137** in `978.adv`
  (~33–39 KB median) — consistent with the ~430 / ~309 planning elements.
* Each chunk = a **low-entropy header** (~2–4 KB) + a **high-entropy
  compressed body** (entropy ≈ 7.5).
* Region-level chunk headers were observed to contain meaningful constants:
  `3.14159` (π), `0.785398` (π/4) and `±1.0` doubles — i.e. **rotation /
  orientation parameters** for the planned element.
* The compressed bodies still need the decoder (§7.1).

`advrecover chunks <a> --compare <b>` performs differential analysis across
two files — the tool to run first when more samples arrive.

## 6b. Planning-element records — DECODED (Path B)

Each `Saw` / `Pie` planning element name in the planning tree is **preceded
by a fixed 60-byte record** (verified across the 20-file sample set):

```
offset  type     field
+0x00   u32      tag           84 / 85 / 86 for active records
+0x04   u32      element_id    sequential id
+0x08   f64      fixed         constant ~54.0 (reference angle / reserved)
+0x10   f64      offset        signed plane offset, in microns (±~3200)
+0x18   f64      reserved      constant 0.0
+0x20   f64[3]   normal        unit normal vector  (VERIFIED |n| == 1.0)
+0x38   u32      marker        == 1
+0x3C   u32      name_len      MFC string length, then the name bytes
```

This is enough for a **parametric reconstruction without the codec**: a
`Saw` element is the cutting plane `normal · x == offset`; a `Pie` element
is a planned stone's orientation + position. Element names group into
planning *solutions* (`Saw133-1` → solution `133`).

`advrecover planning` builds and exports this: each element becomes a plane
quad, optionally filtered to one solution (`--solution 133`). It produces
real OBJ/STL geometry traced entirely to decoded records — the rough
*scanned* surface still needs the §6 codec, but the cut planning is
recovered.

## 7. Open questions (next RE iterations)

1. **Decode the high-entropy blocks (§6)** — the scanned rough/polished
   meshes; needs the Advisor decoder (the data is *not* encrypted, so this
   is tractable with the DLLs).
2. Confirm the meaning of the `fixed` (≈54.0) field and whether `offset` is
   a distance from origin or along another datum.
3. Align the ~347 per-element chunks (§6a) to the named elements (§6b).
4. Meaning / role of the single common plane shared by all contour records.
5. Inclusion / internal-feature records.
6. Meaning of `const_a` / `const_b` (61809 / 2359 — constant across samples).

Use `advrecover segment`, `probe` and `diff` to extend this spec; every
finding should be added here with a VERIFIED/HYPOTHESIS tag.
