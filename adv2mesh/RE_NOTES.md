# .ADV Format — Reverse-Engineering Notes

Recovered by heuristic analysis of two sample files
(`1d599c2a-985.adv`, `b4e33bf2-1188.adv`). The format is **undocumented**;
everything below is empirical. `1d599c2a-985.adv` is the reference file
the parser is calibrated against.

Origin: **Sarine "Advisor"** rough-diamond planning project, fed by
**Galaxy ("GLX")** inclusion-scan data. Strong identifiers: the `.ADV`
extension, `GLX`/`GLX-1` strings, and process-stage metadata keys
(`WeightAfterBruting`, `…AfterPavil.4/8/16`, `…AfterCrown.4/8/16`).

## Global conventions

| Property | Finding |
|----------|---------|
| Endianness | little-endian throughout |
| Integers | `uint32` counts/offsets, `uint64` footer offsets |
| Strings | `int32` length prefix + raw ASCII (no NUL terminator) |
| GUIDs | 16-byte Microsoft layout, used as type tags |
| Timestamps | Windows `FILETIME` (`uint64`, 100 ns since 1601) |
| Geometry floats | `float32` (rough mesh), `float64` (silhouettes, planes) |
| Container compression | none — only embedded JPEG payloads |

## Container layout

```
0x00  guid[16]   magic  c7289bca-ecd7-459b-aabf-e4423fef0eff
0x10  u32        format version (=2)
0x14  u32        -> footer chunk-table entries (EOF-24)
0x18  u32        -> footer section start       (EOF-76)
0x1C  u32        reserved
0x20  ...        root scene object / payload

footer @ [0x18]:
  guid[16]   section guid
  u32        reserved
  u32        table byte size
  u32        entry count
  entry[N]   { u32 chunk_id ; u64 file_offset }
```

Chunk ids: `0` object directory · `1` root scene (@0x20) ·
`3` metadata · `4` thumbnail JPEGs.

## Chunk 3 — metadata

Flat run of length-prefixed strings forming entries
`(label, dotted.key, [unit], [type-code], value)`. Recovered keys include
`stone.RoughWeight`, `Stone.color`, `Stone.clarity`,
`Result.N.{Shapename,PartWeight,PartUsage,PolishWeightDouble,ValueNoComma}`,
`ResultGroup.Cur.Sum.WeightAfter*`, `inclusions.count.meshes`.

## Geometry (payload region: 0x20 .. first embedded JPEG)

**float32 contour chain** — the rough diamond.
Record header (9 bytes): `u32 tag · u8 0x01 · u32 vertex_count`,
followed by `vertex_count × 3 float32`. Records are packed contiguously
and drift off any fixed alignment ⇒ must be parsed **sequentially**.

**float64 contour arrays** — silhouette / cross-section outlines.
`vertex_count × 3 float64`; mostly planar loops.

> Validation against the scanner imagery showed the float32 contours are
> per-angle silhouettes; lofting them twists the surface. A **visual-hull**
> builder is the correct fix — `geometry.MeshBuilder` is an interface so
> one can be added without touching callers.

## Cutting / saw planes  (reference file `…-985`)

Each `Saw*`/`Pie*` object embeds a 6 × `float64` record:

```
f64 const_field      = 50.0   (fixed)
f64 offset           signed distance from rough centroid
f64 blade_thickness  = 0.0    (idealised zero-kerf)
f64 nx, ny, nz       unit normal
```

Plane equation, `C` = rough centroid: **`n · X = n · C + offset`**
(verified: 277/277 planes land inside the rough).

> **Format variant:** `b4e33bf2-1188.adv` does *not* use the `50.0`
> constant — its plane sub-record is laid out differently and is not yet
> decoded. The extractor keys on the `50.0` signature and returns 0
> planes (with a warning) rather than emitting false positives.

## Planned polished diamonds

~2.4–3.2 KB records keyed by a length-prefixed `"ROUND"` string. Each
carries shape, scanner (`GLX`/`GLX-1`), colour (`WH`), polish-orientation
mode (`Manual`), embedded saw planes, and a 7–10 point bounding cage.
The brilliant facet mesh itself is **parametric, not stored**.

## Inclusions — not recoverable

`inclusions.count.meshes` reports 1602 (985) / 3060 (1188) inclusion
meshes. They live inside a ~720 KB **proprietary-compressed** blob
(high entropy ≈ 7.98, byte-biased, no standard codec decodes it). The
converter locates and reports the blob but cannot extract its geometry.

## Open items

- Decode the `…-1188` cutting-plane variant.
- Crack the inclusion compression codec.
- Replace contour lofting with visual-hull reconstruction.
- Resolve absolute units (currently a ±30 % carat-based estimate).
