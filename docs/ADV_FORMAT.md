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

## 5. Geometry encoding — VERIFIED

Plainly-stored geometry is a contiguous list of **contour records**:

```
repeat:
    u32      point_count
    float32  xyz[point_count * 3]      coordinate unit = microns
```

The `u32 point_count` sits immediately before each point block (its
denormal float value is what naturally delimits the runs). ~45 such records
exist per file, ~360–375 points each.

**Important — verified by PCA:** every contour record is **planar**, and all
records share a *single common plane* (thin-axis extent ≈ 8 µm versus ≈ 8 mm
in-plane). They are a **2-D auxiliary dataset** (a cross-section / saw
diagram), **not** the 3-D rough surface.

A full-section scan in both float32 and float64 finds **zero** volumetric
(non-planar) point arrays. The 3-D rough body, planned polished stones and
saw planes are therefore **not** stored as plain floating-point data — they
live in the block described in §6.

The recovered planar contours are still real, exported geometry; they are
labelled as 2-D auxiliary contours, not presented as the rough surface.

## 6. The opaque block — VERIFIED location, UNDECODED content

The bulk of the main-model section — roughly **26 MB** of the 28 MB sample,
spanning ≈ `0x10000` to ≈ `0x19B0000` — is a high-entropy block at
≈ 8.0 bits/byte. This block holds the 3-D model (see §5). Established by
probing:

* Entropy ≈ 8.0 — at the theoretical maximum; uniform across the whole span.
* **No** embedded JPEG or PNG images.
* **Not** a framed zlib/gzip stream — zlib byte pairs occur only at chance
  frequency and do not decompress.
* No periodic record framing, size table or chunk markers were found.
* A short ASCII marker `"CRL"` appears at the block start (`0x10000`).

Entropy this high and this uniform, with no decodable framing, is consistent
with either a **proprietary compression** scheme or **encryption**. From only
two sample files this block is **not decodable** — doing so realistically
requires the Advisor application/SDK (to observe the decoder) or a much
larger corpus of samples for differential analysis.

Consequence: a reconstruction that pixel-matches the original viewport
cannot be produced from the plain data alone. The **200+ embedded JPEG
previews** (section 4) are themselves rendered views of the planning model
and are the pragmatic source for showing the visualisation today.

## 7. Open questions (next RE iterations)

1. **Decode the opaque ~26 MB block (§6)** — the only route to the true 3-D
   model. Best attacked with the Advisor application/SDK or many samples.
2. Identify the `"CRL"` marker at `0x10000` and any block sub-structure.
3. Meaning / role of the single common plane shared by all contour records.
4. Plane equations for `Saw` planes (normal + offset).
5. Inclusion / internal-feature records.
6. Meaning of `const_a` / `const_b` (61809 / 2359 — constant across samples).

Use `advrecover probe` and `advrecover inspect` to extend this spec; every
finding should be added here with a VERIFIED/HYPOTHESIS tag.
