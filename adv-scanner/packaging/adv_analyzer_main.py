"""Entry point for the PyInstaller-built ``adv-analyzer`` executable.

This thin wrapper exists so PyInstaller has a concrete script to analyse;
all real logic lives in :mod:`advkit.tools.cli`.
"""
import sys

from advkit.tools.cli import main

if __name__ == "__main__":
    sys.exit(main())
