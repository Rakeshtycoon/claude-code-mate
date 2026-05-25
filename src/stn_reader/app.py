"""Tkinter GUI entry point for STN READER."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")

from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk,
)
from matplotlib.figure import Figure

from stn_reader import __version__
from stn_reader.parser import (
    NO_DATA_SENTINEL_U16,
    StnModel,
    StnParseError,
    extract_heightfield_preview,
    parse_stn_file,
)


class StnReaderApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"STN READER v{__version__}")
        self.geometry("1100x720")
        self._current: StnModel | None = None
        self._build_menu()
        self._build_layout()

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(
            label="Open .stn...", command=self._on_open, accelerator="Ctrl+O"
        )
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="About", command=self._on_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)
        self.bind_all("<Control-o>", lambda _e: self._on_open())

    def _build_layout(self) -> None:
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(paned, padding=8)
        paned.add(left, weight=1)

        ttk.Label(left, text="File info", font=("TkDefaultFont", 10, "bold")).pack(
            anchor="w"
        )
        self.info = tk.Text(left, width=44, wrap="word", state=tk.DISABLED)
        self.info.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        right = ttk.Frame(paned, padding=8)
        paned.add(right, weight=3)

        ttk.Label(
            right, text="Heightfield preview", font=("TkDefaultFont", 10, "bold")
        ).pack(anchor="w")

        self.figure = Figure(figsize=(7, 5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Open a .stn file to preview")
        self.ax.set_xlabel("sample index")
        self.ax.set_ylabel("quantised height (u16)")

        self.canvas = FigureCanvasTkAgg(self.figure, master=right)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        NavigationToolbar2Tk(self.canvas, right).update()

        self.status = ttk.Label(self, text="Ready", anchor="w", relief=tk.SUNKEN)
        self.status.pack(fill=tk.X)

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

        self._current = model
        self._render_info(model)
        self._render_preview(model)
        self.status.config(text=f"Loaded {model.source_path.name}")

    def _render_info(self, model: StnModel) -> None:
        h = model.header
        m = model.metadata
        lines = [
            f"File:           {model.source_path.name}",
            f"Path:           {model.source_path}",
            f"Size:           {model.byte_size:,} bytes",
            f"Magic:          0x{h.magic:08x} {'OK' if model.is_valid else 'BAD'}",
            f"File ID:        0x{h.file_id:08x}",
            f"Creation tag:   0x{h.creation_marker:08x}",
            f"Scale factor:   {h.scale_factor:.6g}",
            f"Width count:    {h.width_count}",
            f"Height count:   {h.height_count}",
            f"Format const:   {h.constant_61200}",
            "",
            f"Part number:    {m.part_number or '(none)'}",
            f"Quality tag:    {m.quality_tag or '(none)'}",
            f"Producer:       Stone v{m.producer_version or '?'}",
            f"Build dates:    {len(m.producer_dates)} entries",
        ]
        for d in m.producer_dates[:8]:
            lines.append(f"   - {d}")
        if len(m.producer_dates) > 8:
            lines.append(f"   ... and {len(m.producer_dates) - 8} more")
        lines.extend(
            [
                "",
                f"Body offset:    {model.body_offset}",
                f"Body size:      {model.body_size:,} bytes",
                f"No-data marker: 0x{NO_DATA_SENTINEL_U16:04x}",
            ]
        )

        self.info.configure(state=tk.NORMAL)
        self.info.delete("1.0", tk.END)
        self.info.insert(tk.END, "\n".join(lines))
        self.info.configure(state=tk.DISABLED)

    def _render_preview(self, model: StnModel) -> None:
        data = model.source_path.read_bytes()
        samples = extract_heightfield_preview(data, max_samples=32768)
        self.ax.clear()
        if not samples:
            self.ax.set_title("No height samples decoded")
        else:
            self.ax.plot(samples, linewidth=0.4)
            self.ax.set_title(
                f"{model.source_path.name} - {len(samples):,} samples "
                f"(sentinel 0x{NO_DATA_SENTINEL_U16:04x} masked)"
            )
            self.ax.set_xlabel("sample index")
            self.ax.set_ylabel("quantised height (u16)")
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _on_about(self) -> None:
        messagebox.showinfo(
            "About STN READER",
            f"STN READER v{__version__}\n\n"
            "Windows desktop reader for Stone .stn scan files.\n"
            "Magic 0x00000937 - Producer 'Stone'.",
        )


def main() -> None:
    StnReaderApp().mainloop()


if __name__ == "__main__":
    main()
