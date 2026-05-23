"""Module entry point: GUI when launched without arguments, CLI otherwise.

`python -m adv2mesh`              -> opens the Tkinter GUI
`python -m adv2mesh file.adv -o`  -> CLI conversion
"""
import sys


def _run():
    if len(sys.argv) > 1:
        from .cli import main
        return main()
    try:
        from .gui import main as gui_main
    except Exception as e:                                          # noqa
        # tkinter missing or display unavailable -> fall back to CLI help
        print("GUI unavailable (%s); use the command line:" % e,
              file=sys.stderr)
        from .cli import main
        return main(["-h"])
    gui_main()
    return 0


if __name__ == "__main__":
    sys.exit(_run())
