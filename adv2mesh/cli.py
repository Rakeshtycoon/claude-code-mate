"""Command-line interface for adv2mesh.

Usage:
    python -m adv2mesh INPUT.adv [-o OUTDIR] [--no-loft] [--no-debug] [-v]
"""
import argparse
import logging
import sys
import os

from .pipeline import convert
from .container import ADVFormatError


def _add_console_handler():
    """Stream INFO+ to stderr - safe to no-op when stderr is missing (--windowed exe)."""
    log = logging.getLogger("adv2mesh")
    if any(isinstance(h, logging.StreamHandler) and
           not isinstance(h, logging.FileHandler) for h in log.handlers):
        return
    if sys.stderr is None:
        return
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-7s  %(message)s", "%H:%M:%S"))
    log.addHandler(sh)


def main(argv=None):
    _add_console_handler()
    ap = argparse.ArgumentParser(
        prog="adv2mesh",
        description="Convert proprietary .ADV diamond planning files into "
                    "OBJ / STL / glTF scenes with metadata.")
    ap.add_argument("input", help="input .ADV file")
    ap.add_argument("-o", "--out", default=None,
                    help="output directory (default: <input>_adv2mesh)")
    ap.add_argument("--no-loft", action="store_true",
                    help="export the rough as contour lines, not a lofted mesh")
    ap.add_argument("--no-debug", action="store_true",
                    help="skip the debug PNG visualisation")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="verbose (DEBUG) logging")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.input):
        ap.error("input file not found: %s" % args.input)
    out = args.out or (os.path.splitext(args.input)[0] + "_adv2mesh")

    try:
        report = convert(args.input, out,
                          loft=not args.no_loft,
                          debug_png=not args.no_debug,
                          verbose=args.verbose)
    except ADVFormatError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2

    print("\nOK - %d cutting planes, %d polished, output in: %s"
          % (len(report["cutting_planes"]),
             len(report["polished_diamonds"]), out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
