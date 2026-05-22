"""Frozen-executable entry point — opens the desktop viewer.

An optional ``.adv`` path may be passed on the command line / via file
association.
"""
import sys

from advrecover.viewer.app import launch

if __name__ == "__main__":
    sys.exit(launch(sys.argv[1] if len(sys.argv) > 1 else None))
