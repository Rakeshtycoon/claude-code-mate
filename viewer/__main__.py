"""Entry point: `python -m viewer` launches the desktop viewer."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def main(argv: list[str] | None = None) -> int:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("STL TO STN Viewer")
    app.setOrganizationName("STL TO STN")

    window = MainWindow()
    window.show()

    # Allow CLI: `python -m viewer file1.stl file2.stl`
    for path in app.arguments()[1:]:
        window.load_file(path)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
