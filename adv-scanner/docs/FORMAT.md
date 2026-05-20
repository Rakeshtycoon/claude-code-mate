# `.adv` File Format — Reverse-Engineering Notes

Status: **Phase 1 — evidence-based, multi-sample.** Findings were derived
by analysing **5 real samples** (sizes 25–48 MB) with the tools in this
repo, and cross-checking every structural claim across all of them.
Claims are graded:

- **[CONFIRMED]** — verified by decoding actual data.
- **[STRONG]** — multiple consistent signals, not yet byte-proven.
- **[OPEN]** — hypothesis; needs more samples or vendor data.

This document deliberately does **not** invent structure. Where the format
is not yet understood it says so.

---

## 1. Top-level layout `[CONFIRMED]`

The `.adv` file is a single-stream serialized object graph (no central
directory). Across all 5 samples the same five sections appear, in the
same order, with sizes that scale per stone:

| Region              | Content | Notes |
|---------------------|---------|-------|
| `header + body`     | Header, then the serialized 3D model (see §5) | 14–32 MB |
| `xray_slices`       | **300** grayscale JPEG slices, 1024×1280 | always 300 |
| `intermediate`      | Undecoded binary block | 0.7–1.7 MB |
| `preview_thumbnails`| 188–214 RGB JPEG thumbnails, 98×98 | per-stone |
| `trailer`           | Tail record | **always 148 B** |

The slice/thumbnail runs are located by the marker-aware JPEG carver
(`advkit.parsers.jpeg`), not by guesswork — each stream is validated by a
full marker walk to its EOI plus a sane SOF. The 300-slice count and the
148-byte trailer are invariant across every sample.

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
| `68`   | f64         | `1.842` (1.97–2.57 across samples)     | Calibration scalar — varies per stone `[CONFIRMED]` |
| `76–123` | f64[]     | mostly `-1.0` / `0.0`                  | AABB / transform slots, sentinel-initialised `[STRONG]` |

After the fixed block come **u32-length-prefixed strings** (a classic
MFC/`CString` serialization). Discovered in the sample:

- `"168001688475"` — job / scan id (also the source `.adv` base name)
- `"Fast"` — scan mode
- `"e88f7313-c21e-73c9-a03a-20f8ef3ebcde"` — scan UUID (appears twice)

The header also contains a run of mixed u32 fields (counts, dimensions,
and several large values in the 0.5–32 M range that look like internal
offsets) — see `[OPEN]` below.

## 3. Internal X-ray images `[CONFIRMED]`

- **300** baseline JPEG streams, **1024×1280, 1 component (grayscale)** —
  the count is identical in every sample.
- Stored back-to-back with **no padding** between them.
- **These are rotational X-ray projections, not CT cross-sections.**
  Inspecting slices 0/60/120/.../299 shows the *same* stone on a spindle
  at successive rotation angles (its silhouette rotates); the vendor
  videos confirm this is the 2D image the planner scrolls through.
  → Naively stacking them into a Z-volume is **not** geometrically valid;
  a true 3D volume needs tomographic reconstruction (filtered
  back-projection). `advkit.volume` still stacks them as a quick
  visual/QA aid, but that volume is explicitly approximate.
- Standard JFIF — the embedded Huffman/quantisation tables are the
  textbook tables, which is what first revealed the file contains JPEGs.
- Damaged slices occur in real data (e.g. index 32 / index 28 in two
  samples) — they fail to decode. The parser flags them
  (`AdvFile.damaged_slices`).

## 4. Preview thumbnails `[STRONG]`

- ~200 JPEG streams, **98×98, 3 components (RGB)**.
- Each is preceded by a **76-byte record** = nine f64 values forming a
  3×3 matrix (identity in the sample → orientation/rotation) plus a u32.
- Interpretation: multi-angle preview renders / photographs of the rough
  stone, each tagged with a view orientation.

## 5. The body block — serialized 3D model `[STRONG]`

The block between the header and the slice run is **not compressed** (no
zlib/lz4/zstd; the `78 9c` byte pairs are below random expectation) and
**not a raw image stack** (no stride correlation peak). Decoding it across
all 5 samples shows it is a **serialized 3D scene** — the laser-scanned
outer surface mesh of the rough diamond, plus connectivity and raster
data. Identified buffer types:

- **Vertex buffers** `[CONFIRMED]` — contiguous arrays of `float64` XYZ
  coordinates. Values are mixed-sign and within ±~30,000 (microns → a
  centred few-mm model). Verified by reading triangles' indices back
  against them.
- **Face buffers** `[CONFIRMED]` — `uint32` triangle lists framed as
  `[3][i0][i1][i2]`, 16 bytes per triangle; the constant `3` is the
  per-face vertex count. Reliably detected (the framing is unambiguous).
  Samples carry ~12 face buffers of a near-constant ~12,300 triangles
  each → the mesh is stored in fixed-size chunks.
- **Index/connectivity buffers** `[STRONG]` — runs of small `uint32`
  values (adjacency / edge lists).
- **Raster regions** `[OPEN]` — ~1024-wide 16-bit areas (entropy ~5–6,
  30–55 % zeros) — candidate depth maps or a voxel slab.

Verified buffer details:

- **Face chunks** are fixed runs of ~13,492 (or ~21,267) triangles,
  separated by 14-byte records; `[3][i0][i1][i2]` u32, 16 B each. Face
  indices reach ~70,000 → the rough-stone mesh has ~70k vertices.
- **Vertex chunks** are blocks of f64 XYZ (e.g. 8,995 verts ≈ 215,880 B).
  The geometry is stored **twice** in the body block.
- Extracting all vertex chunks and exporting them gives a clean point
  cloud of the rough-diamond surface (`adv-analyzer geometry --export`).

**Surface mesh reconstruction** `[STRONG]`: the body block stores the
rough-stone mesh as a global f64 XYZ vertex pool followed by the u32
triangle chunks. The pool is interrupted by short separators that drift
the byte alignment off the 8-byte grid; recovering it as the
concatenation of every f64 coordinate run (each trimmed to whole
vertices) in the window before the faces yields a vertex array large
enough for all triangle indices. The pool ends immediately before the
faces, so the last *N* vertices (N = max index + 1) are the referenced
set. `assemble_surface_mesh` / `adv-analyzer geometry --export-mesh`
produce this mesh (OBJ/PLY/STL/GLB). It is **best-effort** — a few
triangulation artefacts remain where a separator's exact length could
not be pinned down.

Still `[OPEN]`:
- Exact separator framing (would remove the residual mesh artefacts).
- Isolating the individual **inclusion** sub-meshes (the green objects in
  the planner) from the rough-stone mesh — the body block is a multi-
  object scene and at least one object class uses a different vertex
  record layout.

`adv-analyzer geometry` reports/exports vertex clouds and the surface
mesh; `adv-analyzer discover` continues probing the raster regions.

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
adv-analyzer geometry sample.adv     # mesh vertex/face buffers in the body
adv-analyzer discover sample.adv     # structure discovery on raw regions
adv-analyzer hexdump  sample.adv --offset 0 --length 512
```
