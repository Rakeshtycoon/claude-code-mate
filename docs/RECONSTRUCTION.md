# Reconstruction Assumptions

This document records every **reconstruction assumption** — choices made
when turning decoded `.ADV` data into 3D geometry. It is deliberately kept
separate from `ADV_FORMAT.md`, which records only **verified binary
findings**. Each item is tagged `DECODED` (straight from file bytes) or
`ASSUMED` (an inference the reconstruction makes).

## Cutting planes (`Saw` elements)

* `DECODED` — each `Saw` element has a unit normal and a signed offset
  (`docs/ADV_FORMAT.md` §6b).
* `ASSUMED` — the plane is `normal · x = offset`; its render centre is
  `offset · normal`. The `fixed` (~54.0) and `reserved` (0.0) record fields
  are treated as non-geometric. If `offset` is later found to be measured
  from a datum other than the origin, only the centre shifts.
* `ASSUMED` — the plane quad size (default 7 mm) is a display choice; the
  real cut extent is bounded by the rough, which is not yet decoded.

## Planned stones (`Pie` elements)

* `DECODED` — each `Pie` element has a unit normal and a signed offset.
* `ASSUMED` — the normal is the stone's **table normal** (its up-axis); the
  solid is oriented by the rotation mapping +Z onto that normal.
* `ASSUMED` — the stone **position** is `offset · normal`.
* `ASSUMED` — the **diameter** is a caller parameter (default 3 mm). Per-
  stone size is *not* present in the decoded 60-byte record; it most likely
  lives in the still-encoded per-element chunk (`ADV_FORMAT.md` §6a).
* `ASSUMED` — the **cut family** is a standard round brilliant. The file
  does not (yet) expose a per-element cut code; `cut_family` is selectable
  and the generator is extensible (`advrecover/gem/cuts.py`).

## Brilliant-cut generator (`advrecover/gem`)

* `ASSUMED` — proportions follow Tolkowsky-style ideal values
  (`STANDARD_ROUND_BRILLIANT`): table 56 %, crown angle 34.5°, pavilion
  angle 40.75°, girdle 3 %, culet 0.7 %.
* The generated mesh is **manifold and watertight** (verified by tests:
  every edge shared by exactly 2 triangles; Euler characteristic = 2).
* Geometry is parametric — driven entirely by `CutSpec`; no real per-stone
  proportions are claimed.

## Rough body

* `ASSUMED` / proxy — the "rough body" layer is a convex hull / marching-
  cubes surface of the recovered contour template. The contour template is
  `DECODED` data but is **shared across stones** (`ADV_FORMAT.md` §5), so it
  is *not* the true scanned rough. It is shown only as a spatial reference
  and is flagged "inferred" in the viewer's debug mode.
* The true scanned rough surface needs the encoded geometry blocks decoded
  (requires the Advisor decoder).

## Units & coordinate frame

* `DECODED` — coordinates are microns; the reconstruction converts to
  millimetres (`scale_to_mm`).
* `ASSUMED` — the reconstruction works in the file's native frame; no
  global re-centring is applied beyond per-stone placement.

## Summary of what is real vs. inferred

| Output | Status |
|--------|--------|
| Saw plane orientation (normal) | DECODED |
| Saw plane offset | DECODED |
| Pie stone orientation (normal) | DECODED |
| Pie stone position | DECODED |
| Pie stone diameter | ASSUMED (parameter) |
| Pie stone cut family / proportions | ASSUMED (round brilliant) |
| Rough body surface | ASSUMED (proxy from shared template) |
