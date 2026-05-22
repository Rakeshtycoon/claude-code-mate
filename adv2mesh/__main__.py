"""Module entry point so `python -m adv2mesh ...` works."""
import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
