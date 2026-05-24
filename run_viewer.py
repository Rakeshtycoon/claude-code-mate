"""PyInstaller entry point for the STL TO STN viewer.

Kept at the project root (outside the `viewer` package) so PyInstaller
can run it as a top-level script. The package itself still uses
relative imports for `python -m viewer` development use.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from viewer.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("STL TO STN Viewer")
    app.setOrganizationName("STL TO STN")

    window = MainWindow()
    window.show()

    for path in app.arguments()[1:]:
        window.load_file(path)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
