"""Command-line interface for ADV Planning Data Recovery.

Subcommands: ``info``, ``probe``, ``diff``, ``extract``, ``export``,
``batch`` and ``gui``. Every stage of the pipeline is reachable here without
the desktop UI, which also makes the tool scriptable for batch jobs.
"""
from __future__ import annotations

import argparse
import os
import sys
import traceback

from . import __version__
from .format import constants as C
from .format import parse_file
from .format.constants import guid_name


def _log(message: str) -> None:
    print(message, flush=True)


# -- info --------------------------------------------------------------------
def cmd_info(args: argparse.Namespace) -> int:
    doc = parse_file(args.file)
    _log(f"File        {doc.path}")
    _log(f"Size        {doc.file_size:,} bytes")
    _log(f"Magic       {doc.magic}")
    _log(f"Version     {doc.version}")
    _log(f"Directory   0x{doc.directory_offset:08x}")
    _log("Sections:")
    for sec in doc.sections:
        _log(f"  id={sec.section_id}  {sec.role:12s}  "
             f"0x{sec.offset:08x}..0x{sec.end:08x}  "
             f"{sec.size:>12,} B  {guid_name(sec.guid)}")
    mm = doc.main_model
    if mm:
        _log("Main model:")
        _log(f"  stone id    {mm.stone_id}")
        _log(f"  plan code   {mm.plan_code}")
        _log(f"  scan mode   {mm.scan_mode}")
        _log(f"  created     {mm.created}")
        _log(f"  document    {mm.document_uuid}")
        _log(f"  planning    {len(mm.planning_tree)} elements")
        saws = [t for t in mm.planning_tree if t.lower().startswith("saw")]
        pies = [t for t in mm.planning_tree if t.lower().startswith("pie")]
        _log(f"              {len(saws)} saw planes, {len(pies)} pieces")
    _log(f"Previews    {len(doc.previews)} embedded JPEG image(s)")
    for warning in doc.warnings:
        _log(f"WARNING     {warning}")
    return 0


# -- tree --------------------------------------------------------------------
def cmd_tree(args: argparse.Namespace) -> int:
    doc = parse_file(args.file)
    _log(f"{os.path.basename(doc.path)}")
    _log(f"+- container  version {doc.version}")
    for sec in doc.sections:
        _log(f"+- section[{sec.section_id}] {sec.role}  ({sec.size:,} B)")
        _log(f"|    guid {sec.guid}")
        if sec.section_id == 1 and doc.main_model:
            mm = doc.main_model
            _log(f"|    +- metadata: {mm.stone_id} / {mm.plan_code}")
            _log(f"|    +- planning tree ({len(mm.planning_tree)})")
            for name in mm.planning_tree[:args.limit]:
                _log(f"|    |    - {name}")
            if len(mm.planning_tree) > args.limit:
                _log(f"|    |    ... {len(mm.planning_tree) - args.limit} more")
        if sec.section_id == 4:
            _log(f"|    +- {len(doc.previews)} JPEG preview(s)")
    return 0


# -- probe -------------------------------------------------------------------
def cmd_probe(args: argparse.Namespace) -> int:
    from .re_tools.probe import probe_file

    _log(probe_file(args.file).render())
    return 0


# -- segment -----------------------------------------------------------------
def cmd_segment(args: argparse.Namespace) -> int:
    from .re_tools.segment import block_map, render_segments, segment_file

    with open(args.file, "rb") as fh:
        data = fh.read()
    if args.ranked:
        segments = block_map(data, window=args.window)
        _log(render_segments(segments, ranked=True))
    else:
        segments = segment_file(data, window=args.window, min_size=args.window * 2)
        _log(render_segments(segments))
    return 0


# -- chunks ------------------------------------------------------------------
def cmd_chunks(args: argparse.Namespace) -> int:
    from .re_tools.chunks import chunk_table, compare_chunk_tables, render_chunk_table

    with open(args.file, "rb") as fh:
        data = fh.read()
    table = chunk_table(data, region_start=args.start)
    if args.compare:
        with open(args.compare, "rb") as fh:
            other = chunk_table(fh.read(), region_start=args.start)
        for line in compare_chunk_tables(table, other):
            _log(line)
    else:
        _log(render_chunk_table(table, limit=args.limit))
    return 0


# -- survey ------------------------------------------------------------------
def cmd_survey(args: argparse.Namespace) -> int:
    """Structural comparison table across a directory of .adv files."""
    files = sorted(f for f in os.listdir(args.directory)
                   if f.lower().endswith(".adv"))
    if not files:
        _log(f"no .adv files in {args.directory}")
        return 1
    _log(f"{'file':<20}{'size':>12} {'stone_id':<20}{'plan':<9}"
         f"{'elem':>6}{'saw':>5}{'pie':>5}{'prev':>6}")
    for name in files:
        try:
            doc = parse_file(os.path.join(args.directory, name))
            mm = doc.main_model
            tree = mm.planning_tree if mm else []
            saws = sum(1 for t in tree if t.lower().startswith("saw"))
            pies = sum(1 for t in tree if t.lower().startswith("pie"))
            _log(f"{name:<20}{doc.file_size:>12,} "
                 f"{(mm.stone_id if mm else ''):<20}{(mm.plan_code if mm else ''):<9}"
                 f"{len(tree):>6}{saws:>5}{pies:>5}{len(doc.previews):>6}")
        except Exception as exc:  # noqa: BLE001
            _log(f"{name:<20}  ERROR: {exc}")
    return 0


# -- diff --------------------------------------------------------------------
def cmd_diff(args: argparse.Namespace) -> int:
    from .re_tools.diff import common_prefix, diff_regions

    with open(args.file_a, "rb") as fh:
        a = fh.read()
    with open(args.file_b, "rb") as fh:
        b = fh.read()
    _log(f"A {args.file_a} ({len(a):,} B)")
    _log(f"B {args.file_b} ({len(b):,} B)")
    _log(f"identical leading header: {common_prefix(a, b)} bytes")
    regions = diff_regions(a, b, args.min_run)
    _log(f"differing regions (>= {args.min_run} B): {len(regions)}")
    for region in regions[:args.limit]:
        _log(f"  0x{region.offset:08x}  {region.length:,} bytes")
    return 0


# -- extract -----------------------------------------------------------------
def cmd_extract(args: argparse.Namespace) -> int:
    doc = parse_file(args.file)
    os.makedirs(args.out, exist_ok=True)
    stem = os.path.splitext(os.path.basename(args.file))[0]

    for i, preview in enumerate(doc.previews):
        out = os.path.join(args.out, f"{stem}_preview_{i:03d}.jpg")
        with open(out, "wb") as fh:
            fh.write(preview.data)
    _log(f"extracted {len(doc.previews)} preview image(s) to {args.out}")

    meta_path = os.path.join(args.out, f"{stem}_metadata.txt")
    mm = doc.main_model
    with open(meta_path, "w", encoding="utf-8") as fh:
        fh.write(f"stone_id={mm.stone_id if mm else ''}\n")
        fh.write(f"plan_code={mm.plan_code if mm else ''}\n")
        fh.write(f"scan_mode={mm.scan_mode if mm else ''}\n")
        fh.write(f"document_uuid={mm.document_uuid if mm else ''}\n")
        fh.write(f"created={mm.created if mm else ''}\n")
        if mm:
            fh.write("planning_tree=\n")
            for name in mm.planning_tree:
                fh.write(f"  {name}\n")
    _log(f"wrote metadata to {meta_path}")
    return 0


# -- export ------------------------------------------------------------------
def cmd_export(args: argparse.Namespace) -> int:
    from .recon import reconstruct
    from .export import write_obj, write_stl

    doc = parse_file(args.file)
    with open(args.file, "rb") as fh:
        data = fh.read()

    _log(f"reconstructing geometry (method: {args.method}) ...")
    result = reconstruct(data, doc, method=args.method, scale_to_mm=not args.microns)
    for note in result.notes:
        _log(f"  {note}")

    os.makedirs(args.out, exist_ok=True)
    stem = os.path.splitext(os.path.basename(args.file))[0]
    written: list[str] = []

    if args.format in ("obj", "both"):
        obj_path = os.path.join(args.out, f"{stem}.obj")
        write_obj(result, obj_path, include_contours=not args.no_contours,
                  include_point_cloud=args.point_cloud)
        written.append(obj_path)
    if args.format in ("stl", "both"):
        stl_path = os.path.join(args.out, f"{stem}.stl")
        write_stl(result, stl_path)
        written.append(stl_path)

    for path in written:
        _log(f"wrote {path}")
    if not result.meshes and args.format in ("stl", "both"):
        _log("note: STL contains no solids — try --method hull or marching_cubes")
    return 0


# -- batch -------------------------------------------------------------------
def cmd_batch(args: argparse.Namespace) -> int:
    files = [f for f in sorted(os.listdir(args.directory))
             if f.lower().endswith(".adv")]
    if not files:
        _log(f"no .adv files found in {args.directory}")
        return 1
    _log(f"batch converting {len(files)} file(s) ...")
    ok = 0
    for name in files:
        path = os.path.join(args.directory, name)
        try:
            sub = argparse.Namespace(
                file=path, out=args.out, method=args.method, format=args.format,
                microns=False, no_contours=False, point_cloud=False,
            )
            cmd_export(sub)
            ok += 1
        except Exception as exc:  # noqa: BLE001 - batch must not abort
            _log(f"FAILED {name}: {exc}")
    _log(f"batch complete: {ok}/{len(files)} succeeded")
    return 0 if ok == len(files) else 1


# -- gui ---------------------------------------------------------------------
def cmd_gui(args: argparse.Namespace) -> int:
    try:
        from .viewer.app import launch
    except ImportError as exc:
        _log(f"GUI dependencies missing ({exc}). Install: pip install -r requirements.txt")
        return 1
    return launch(args.file)


# -- parser ------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="advrecover",
        description="Reverse-engineering converter and viewer for OctoNus "
                    "Advisor .ADV diamond planning files.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("info", help="print parsed container structure")
    p.add_argument("file")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("tree", help="print the parsed structure as a tree")
    p.add_argument("file")
    p.add_argument("--limit", type=int, default=20, help="planning entries to show")
    p.set_defaults(func=cmd_tree)

    p = sub.add_parser("probe", help="reverse-engineering diagnostics")
    p.add_argument("file")
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("segment", help="entropy segmentation / block map")
    p.add_argument("file")
    p.add_argument("--window", type=int, default=8192, help="entropy window size")
    p.add_argument("--ranked", action="store_true",
                   help="rank segments by geometry confidence instead of file order")
    p.set_defaults(func=cmd_segment)

    p = sub.add_parser("chunks", help="parse the per-element chunk table")
    p.add_argument("file")
    p.add_argument("--start", type=lambda x: int(x, 0), default=0xCA0000,
                   help="region start offset (default 0xCA0000)")
    p.add_argument("--limit", type=int, default=40)
    p.add_argument("--compare", help="second .adv file for differential analysis")
    p.set_defaults(func=cmd_chunks)

    p = sub.add_parser("survey", help="structural comparison across a directory")
    p.add_argument("directory")
    p.set_defaults(func=cmd_survey)

    p = sub.add_parser("diff", help="binary diff of two files")
    p.add_argument("file_a")
    p.add_argument("file_b")
    p.add_argument("--min-run", type=int, default=8)
    p.add_argument("--limit", type=int, default=40)
    p.set_defaults(func=cmd_diff)

    p = sub.add_parser("extract", help="extract preview images and metadata")
    p.add_argument("file")
    p.add_argument("--out", default="extracted")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("export", help="reconstruct geometry and export OBJ/STL")
    p.add_argument("file")
    p.add_argument("--out", default="out")
    p.add_argument("--format", choices=["obj", "stl", "both"], default="both")
    p.add_argument("--method", choices=list(__import__(
        "advrecover.recon", fromlist=["METHODS"]).METHODS),
        default="marching_cubes")
    p.add_argument("--microns", action="store_true", help="keep microns (default mm)")
    p.add_argument("--no-contours", action="store_true")
    p.add_argument("--point-cloud", action="store_true", help="include raw points")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("batch", help="batch convert a directory of .adv files")
    p.add_argument("directory")
    p.add_argument("--out", default="out")
    p.add_argument("--format", choices=["obj", "stl", "both"], default="both")
    p.add_argument("--method", default="marching_cubes")
    p.set_defaults(func=cmd_batch)

    p = sub.add_parser("gui", help="launch the desktop viewer")
    p.add_argument("file", nargs="?", help="optional .adv file to open")
    p.set_defaults(func=cmd_gui)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        _log(f"error: file not found: {exc.filename}")
        return 2
    except Exception as exc:  # noqa: BLE001
        _log(f"error: {exc}")
        if os.environ.get("ADVRECOVER_DEBUG"):
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
