"""Command-line entry point: python -m stl_to_stn <in> <out>."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .converter import read_stl, write_stn


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="stl_to_stn",
        description="Convert an STL mesh file to the STN (JSON) format.",
    )
    p.add_argument(
        "input",
        help="Path to the input STL file, or '-' to read binary from stdin.",
    )
    p.add_argument(
        "output",
        help="Path to write the STN file, or '-' to write to stdout.",
    )
    p.add_argument(
        "--units",
        default="mm",
        help="Units to record in the STN header (default: mm).",
    )
    p.add_argument(
        "--pretty",
        action="store_true",
        help="Indent the JSON output for readability.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.input == "-":
        mesh = read_stl(sys.stdin.buffer.read())
        source_name = "<stdin>"
    else:
        mesh = read_stl(args.input)
        source_name = Path(args.input).name

    if args.output == "-":
        write_stn(
            mesh,
            sys.stdout,
            source_name=source_name,
            units=args.units,
            pretty=args.pretty,
        )
    else:
        write_stn(
            mesh,
            args.output,
            source_name=source_name,
            units=args.units,
            pretty=args.pretty,
        )

    print(
        f"Converted {source_name}: "
        f"{len(mesh.vertices)} unique vertices, "
        f"{mesh.triangle_count} triangles.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
