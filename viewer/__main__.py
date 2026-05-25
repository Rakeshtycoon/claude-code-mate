"""Entry point: `python -m viewer` launches the desktop STN viewer.

Uses absolute imports so this file can also serve as a PyInstaller entry
point (PyInstaller runs entry scripts as `__main__`, which breaks
relative imports).
"""

from __future__ import annotations

import sys
from pathlib import Path

# When PyInstaller runs this file as the bundled entry script, the
# `viewer` package may not be on sys.path. Add the parent directory so
# `from viewer.main_window import ...` always resolves.
_parent = str(Path(__file__).resolve().parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from PySide6.QtWidgets import QApplication  # noqa: E402

from viewer.main_window import MainWindow  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("STN READER")
    app.setOrganizationName("STN READER")

    window = MainWindow()
    window.show()

    for path in app.arguments()[1:]:
        window.load_file(path)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
