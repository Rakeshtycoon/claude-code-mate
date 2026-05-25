"""Tkinter GUI entry point for STN READER."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from stn_reader import __version__
from stn_reader.parser import StnParseError, parse_stn_file


class StnReaderApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"STN READER v{__version__}")
        self.geometry("720x480")
        self._build_menu()
        self._build_layout()

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Open .stn...", command=self._on_open)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menubar)

    def _build_layout(self) -> None:
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="No file loaded.", anchor="w").pack(fill=tk.X)
        self.info = tk.Text(frame, height=20, wrap="word", state=tk.DISABLED)
        self.info.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

    def _on_open(self) -> None:
        path = filedialog.askopenfilename(
            title="Open STN file",
            filetypes=[("STN files", "*.stn"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            model = parse_stn_file(path)
        except StnParseError as exc:
            messagebox.showerror("Failed to open .stn", str(exc))
            return

        self.info.configure(state=tk.NORMAL)
        self.info.delete("1.0", tk.END)
        self.info.insert(
            tk.END,
            f"File: {model.source_path}\n"
            f"Size: {model.byte_size} bytes\n"
            f"Header (first 16 bytes): {model.header!r}\n",
        )
        self.info.configure(state=tk.DISABLED)


def main() -> None:
    StnReaderApp().mainloop()


if __name__ == "__main__":
    main()
