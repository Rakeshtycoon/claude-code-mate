"""``adv-analyzer`` - command-line front end for the advkit toolkit.

Subcommands:
  inspect      structural report (header, sections, slices, entropy)
  report       same analysis emitted as JSON
  hexdump      annotated hex view of any region
  entropy      sliding-window entropy profile
  discover     brute-force structure discovery on a raw region
  slices       export internal X-ray slices as PNG
  thumbnails   export preview thumbnails as PNG
  volume       reconstruct and save the 3D voxel volume
  inclusions   detect internal inclusions and report them
  surface      extract an isosurface mesh (STL/OBJ/PLY)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from advkit.core.log import configure, get_logger
from advkit.parsers import (
    AdvFile,
    detect_signatures,
    entropy_profile,
    hexdump,
)

_log = get_logger("cli")


# -- helpers --------------------------------------------------------------
def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024 or unit == "GB":
            return f"{n:.1f}{unit}" if unit != "B" else f"{n}B"
        n /= 1024
    return f"{n:.1f}GB"


def _open(path: str) -> AdvFile:
    if not os.path.isfile(path):
        sys.exit(f"error: no such file: {path}")
    return AdvFile.open(path)


# -- subcommands ----------------------------------------------------------
def cmd_inspect(args) -> int:
    adv = _open(args.file)
    h = adv.header
    print(f"ADV FILE: {adv.path}")
    print(f"  size              {adv.size} ({_human(adv.size)})")
    print("HEADER")
    print(f"  class GUID        {h.class_guid}")
    print(f"  secondary GUID    {h.secondary_guid}")
    print(f"  version           {h.version}")
    print(f"  size fields       {h.size_field_1}, {h.size_field_2} "
          f"(file-24, file-76)")
    print(f"  scan time         {h.scan_time}")
    print(f"  calibration       {h.calibration:.6f}")
    print(f"  metadata strings  {h.strings}")
    print(f"SECTIONS ({len(adv.sections)})")
    for s in adv.sections:
        ent = adv.region_entropy(s)
        print(f"  {s.name:<20} {s.start:>10}..{s.end:<10} "
              f"{_human(s.size):>9}  H={ent:.2f}  {s.kind}")
        if s.note:
            print(f"  {'':<20} -> {s.note}")
    print("CONTENT")
    print(f"  X-ray slices      {adv.slice_count}  (1024x1280 grayscale JPEG)")
    if adv.damaged_slices:
        print(f"  damaged slices    {adv.damaged_slices}  <-- corrupt/incomplete")
    print(f"  preview thumbs    {len(adv.thumbnails)}  (98x98 RGB JPEG)")
    sigs = detect_signatures(adv.reader.buffer, 0, min(adv.size, 4096))
    print(f"  header signatures {sigs if sigs else 'none'}")
    adv.close()
    return 0


def cmd_report(args) -> int:
    adv = _open(args.file)
    summary = adv.summary()
    summary["section_entropy"] = {
        s.name: round(adv.region_entropy(s), 3) for s in adv.sections
    }
    adv.close()
    print(json.dumps(summary, indent=2, default=str))
    return 0


def cmd_hexdump(args) -> int:
    adv = _open(args.file)
    print(hexdump(adv.reader.buffer, args.offset, args.length))
    adv.close()
    return 0


def cmd_entropy(args) -> int:
    adv = _open(args.file)
    prof = entropy_profile(adv.reader.buffer, window=args.window)
    print(f"entropy profile  window={_human(args.window)}  "
          f"{len(prof)} windows")
    prev = None
    for w in prof:
        cls = w.classification
        marker = "  " if cls == prev else "* "
        print(f" {marker}{w.offset:>10}  H={w.entropy:.2f}  {cls}")
        prev = cls
    adv.close()
    return 0


def cmd_discover(args) -> int:
    from advkit.volume.discover import brute_force_dimensions, profile_block

    adv = _open(args.file)
    region = adv.section(args.section) if args.section else adv.sections[0]
    if region is None:
        adv.close()
        sys.exit(f"error: no section named {args.section!r}")
    block = adv.reader.slice(region.start, min(region.size, args.bytes))
    print(f"DISCOVER  section={region.name}  "
          f"{region.start}..{region.end}  sampled {_human(len(block))}")
    prof = profile_block(block, region.start)
    print(f"  profile: {prof.verdict}  (H={prof.entropy:.2f}, "
          f"zero={prof.zero_fraction:.3f}, ascii={prof.printable_fraction:.3f})")
    print("  candidate image widths (adjacent-row correlation):")
    for g in brute_force_dimensions(block, max_width=args.max_width):
        print(f"    width={g.width:<5} bpp={g.bytes_per_pixel}  "
              f"corr={g.row_correlation:.4f}")
    adv.close()
    return 0


def cmd_slices(args) -> int:
    adv = _open(args.file)
    os.makedirs(args.out, exist_ok=True)
    limit = args.limit or adv.slice_count
    written = 0
    for i in range(min(limit, adv.slice_count)):
        s = adv.slices[i]
        try:
            img = adv.slice_image(i)
            img.save(os.path.join(args.out, f"slice_{i:04d}.png"))
            written += 1
        except Exception as exc:  # noqa: BLE001
            _log.warning("slice %d not exported: %s", i, exc)
    print(f"exported {written}/{min(limit, adv.slice_count)} slices to {args.out}")
    if adv.damaged_slices:
        print(f"damaged (skipped): {adv.damaged_slices}")
    adv.close()
    return 0


def cmd_thumbnails(args) -> int:
    import io
    from PIL import Image

    adv = _open(args.file)
    os.makedirs(args.out, exist_ok=True)
    written = 0
    for i in range(len(adv.thumbnails)):
        try:
            img = Image.open(io.BytesIO(adv.thumbnail_bytes(i)))
            img.save(os.path.join(args.out, f"thumb_{i:04d}.png"))
            written += 1
        except Exception as exc:  # noqa: BLE001
            _log.warning("thumbnail %d not exported: %s", i, exc)
    print(f"exported {written}/{len(adv.thumbnails)} thumbnails to {args.out}")
    adv.close()
    return 0


def cmd_volume(args) -> int:
    from advkit.volume.slices import SliceStack

    adv = _open(args.file)
    stack = SliceStack(adv)
    vol = stack.build_volume(downsample=args.downsample)
    stats = stack.stats(vol)
    print(f"volume {stats.shape}  dtype={stats.dtype}  "
          f"voxels={stats.voxel_count}")
    print(f"  intensity  min={stats.min} max={stats.max} "
          f"mean={stats.mean:.1f}")
    if args.out:
        if args.out.endswith(".npy"):
            stack.save_npy(vol, args.out)
        else:
            stack.save_raw(vol, args.out)
        print(f"  saved -> {args.out}")
    adv.close()
    return 0


def cmd_inclusions(args) -> int:
    from advkit.inclusion.detector import detect
    from advkit.volume.slices import SliceStack

    adv = _open(args.file)
    stack = SliceStack(adv)
    vol = stack.build_volume(downsample=args.downsample)
    result = detect(vol, body_threshold=args.threshold,
                    min_voxels=args.min_voxels, max_darkness=args.max_darkness)
    print(f"INCLUSION DETECTION  volume={vol.shape}  "
          f"downsample={args.downsample}")
    print(f"  body threshold    {result.body_threshold}  (air/stone split)")
    print(f"  stone body voxels {result.body_voxels}")
    print(f"  inclusions found  {result.count}")
    print(f"  defect voxels     {result.total_defect_voxels} "
          f"({result.defect_fraction * 100:.4f}% of body)")
    for inc in result.inclusions[:args.top]:
        cz, cy, cx = inc.centroid
        print(f"    #{inc.label:<4} {inc.severity:<8} "
              f"voxels={inc.voxel_count:<7} "
              f"centroid=({cz:.0f},{cy:.0f},{cx:.0f})")
    if args.json:
        with open(args.json, "w", encoding="ascii") as fh:
            json.dump(result.as_dict(), fh, indent=2)
        print(f"  full report -> {args.json}")
    adv.close()
    return 0


def cmd_surface(args) -> int:
    from advkit.mesh.surface import export_mesh, extract_surface
    from advkit.volume.slices import SliceStack

    adv = _open(args.file)
    stack = SliceStack(adv)
    vol = stack.build_volume(downsample=args.downsample)
    mesh = extract_surface(vol, iso_level=args.iso, step=args.step)
    print(f"surface mesh  vertices={mesh.vertex_count}  "
          f"faces={mesh.face_count}  watertight={mesh.is_watertight()}")
    export_mesh(mesh, args.out)
    print(f"  saved -> {args.out}")
    adv.close()
    return 0


# -- argument parser ------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="adv-analyzer",
        description="Reverse-engineering & analysis toolkit for .adv "
                    "diamond-scan files.",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    p.add_argument("-q", "--quiet", action="store_true", help="warnings only")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("inspect", help="structural report")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_inspect)

    sp = sub.add_parser("report", help="structural report as JSON")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_report)

    sp = sub.add_parser("hexdump", help="hex view of a region")
    sp.add_argument("file")
    sp.add_argument("--offset", type=int, default=0)
    sp.add_argument("--length", type=int, default=512)
    sp.set_defaults(func=cmd_hexdump)

    sp = sub.add_parser("entropy", help="sliding-window entropy profile")
    sp.add_argument("file")
    sp.add_argument("--window", type=int, default=262144)
    sp.set_defaults(func=cmd_entropy)

    sp = sub.add_parser("discover", help="brute-force structure discovery")
    sp.add_argument("file")
    sp.add_argument("--section", help="section name (default: first)")
    sp.add_argument("--bytes", type=int, default=4_000_000,
                    help="bytes to sample from the section")
    sp.add_argument("--max-width", type=int, default=2048)
    sp.set_defaults(func=cmd_discover)

    sp = sub.add_parser("slices", help="export X-ray slices as PNG")
    sp.add_argument("file")
    sp.add_argument("-o", "--out", default="slices")
    sp.add_argument("--limit", type=int, default=0, help="0 = all")
    sp.set_defaults(func=cmd_slices)

    sp = sub.add_parser("thumbnails", help="export preview thumbnails as PNG")
    sp.add_argument("file")
    sp.add_argument("-o", "--out", default="thumbnails")
    sp.set_defaults(func=cmd_thumbnails)

    sp = sub.add_parser("volume", help="reconstruct the 3D voxel volume")
    sp.add_argument("file")
    sp.add_argument("-o", "--out", help="output .npy or .raw")
    sp.add_argument("--downsample", type=int, default=4)
    sp.set_defaults(func=cmd_volume)

    sp = sub.add_parser("inclusions", help="detect internal inclusions")
    sp.add_argument("file")
    sp.add_argument("--downsample", type=int, default=4)
    sp.add_argument("--threshold", type=int, default=None,
                    help="air/stone body threshold (default: Otsu)")
    sp.add_argument("--max-darkness", type=int, default=None,
                    help="only count enclosed voxels at/below this intensity")
    sp.add_argument("--min-voxels", type=int, default=8)
    sp.add_argument("--top", type=int, default=15)
    sp.add_argument("--json", help="write full JSON report here")
    sp.set_defaults(func=cmd_inclusions)

    sp = sub.add_parser("surface", help="extract an isosurface mesh")
    sp.add_argument("file")
    sp.add_argument("-o", "--out", default="surface.stl")
    sp.add_argument("--downsample", type=int, default=4)
    sp.add_argument("--iso", type=float, default=None)
    sp.add_argument("--step", type=int, default=1)
    sp.set_defaults(func=cmd_surface)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure(verbose=args.verbose, quiet=args.quiet)
    try:
        return args.func(args)
    except KeyboardInterrupt:  # pragma: no cover
        return 130


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
