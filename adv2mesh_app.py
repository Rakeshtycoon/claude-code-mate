"""Top-level entry script for PyInstaller.

PyInstaller is happiest when given a plain script (not a package's
__main__.py) - this file is that script. Behaviour is identical to
`python -m adv2mesh`:

    no arguments  -> opens the Tkinter GUI
    arguments     -> command-line conversion

Build a Windows .exe with:

    pyinstaller --onefile --windowed --name adv2mesh \\
                --collect-submodules adv2mesh adv2mesh_app.py
"""
import sys

from adv2mesh.cli import main as cli_main


def main():
    if len(sys.argv) > 1:
        return cli_main()
    try:
        from adv2mesh.gui import main as gui_main
    except Exception as e:                                          # noqa
        print("GUI unavailable (%s); use the command line." % e,
              file=sys.stderr)
        return cli_main(["-h"])
    gui_main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
