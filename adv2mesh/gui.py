"""Tkinter GUI - the entry point used by the packaged .exe.

Non-developers shouldn't need a terminal. This module provides a simple
double-click experience:

    1. Browse... -> pick an .ADV file
    2. (optional) pick an output folder
    3. Convert         -> live log + "Open output folder" when done

The conversion runs on a worker thread so the UI stays responsive.
"""
import logging
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

from .pipeline import convert
from .container import ADVFormatError


# ----------------------------------------------------------------------
# logging - pipe the package logger into the GUI's text widget
# ----------------------------------------------------------------------

class _TextHandler(logging.Handler):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget

    def emit(self, record):
        msg = self.format(record) + "\n"

        def append():
            self.widget.configure(state="normal")
            self.widget.insert("end", msg)
            self.widget.see("end")
            self.widget.configure(state="disabled")

        # marshal back to the Tk main thread
        self.widget.after(0, append)


# ----------------------------------------------------------------------
# main window
# ----------------------------------------------------------------------

class ConverterApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ADV -> 3D Converter  (adv2mesh)")
        self.root.geometry("760x540")
        self.root.minsize(560, 380)
        self.in_path = tk.StringVar()
        self.out_path = tk.StringVar()
        self._build_ui()

    # ---- layout ------------------------------------------------------

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # Input row
        row = tk.Frame(self.root)
        row.pack(fill="x", **pad)
        tk.Label(row, text="Input .ADV file:", width=15, anchor="w").pack(side="left")
        tk.Entry(row, textvariable=self.in_path).pack(side="left", fill="x", expand=True, padx=4)
        tk.Button(row, text="Browse...", command=self._pick_in).pack(side="left")

        # Output row
        row = tk.Frame(self.root)
        row.pack(fill="x", **pad)
        tk.Label(row, text="Output folder:", width=15, anchor="w").pack(side="left")
        tk.Entry(row, textvariable=self.out_path).pack(side="left", fill="x", expand=True, padx=4)
        tk.Button(row, text="Browse...", command=self._pick_out).pack(side="left")

        # Action row
        row = tk.Frame(self.root)
        row.pack(fill="x", **pad)
        self.convert_btn = tk.Button(
            row, text="Convert", command=self._start, width=16,
            bg="#2a8b53", fg="white", font=("Segoe UI", 10, "bold"))
        self.convert_btn.pack(side="left", padx=4)
        self.open_btn = tk.Button(
            row, text="Open output folder", command=self._open_out, state="disabled")
        self.open_btn.pack(side="left", padx=4)
        tk.Button(row, text="About", command=self._about).pack(side="right", padx=4)

        # Log area
        self.log_widget = scrolledtext.ScrolledText(
            self.root, state="disabled", wrap="word",
            font=("Consolas", 9), bg="#0d1117", fg="#d0d7de",
            insertbackground="#d0d7de")
        self.log_widget.pack(fill="both", expand=True, padx=10, pady=4)

        # Status bar
        self.status = tk.Label(self.root, text="Ready. Pick an .ADV file to start.",
                                anchor="w", relief="sunken", bd=1, padx=6)
        self.status.pack(fill="x", side="bottom")

    # ---- file pickers -----------------------------------------------

    def _pick_in(self):
        p = filedialog.askopenfilename(
            title="Select an .ADV file",
            filetypes=[("ADV files", "*.adv *.ADV"), ("All files", "*.*")])
        if p:
            self.in_path.set(p)
            if not self.out_path.get():
                self.out_path.set(os.path.splitext(p)[0] + "_adv2mesh")

    def _pick_out(self):
        p = filedialog.askdirectory(title="Select output folder")
        if p:
            self.out_path.set(p)

    def _open_out(self):
        out = self.out_path.get()
        if not out or not os.path.isdir(out):
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(out)                                  # noqa
            elif sys.platform == "darwin":
                subprocess.Popen(["open", out])
            else:
                subprocess.Popen(["xdg-open", out])
        except Exception as e:
            messagebox.showerror("Cannot open folder", str(e))

    def _about(self):
        messagebox.showinfo(
            "About adv2mesh",
            "ADV -> 3D Converter\n\n"
            "Reads Sarine Advisor / Galaxy .ADV diamond planning files and "
            "exports OBJ, STL and glTF scenes plus a metadata JSON.\n\n"
            "Open-source, stdlib-only Python. See RE_NOTES.md for the "
            "recovered format specification.")

    # ---- conversion -------------------------------------------------

    def _start(self):
        inp = self.in_path.get().strip()
        out = self.out_path.get().strip() or (
            os.path.splitext(inp)[0] + "_adv2mesh")
        if not inp or not os.path.isfile(inp):
            messagebox.showerror("adv2mesh", "Please pick a valid .ADV file.")
            return
        self.out_path.set(out)
        self.convert_btn.configure(state="disabled")
        self.open_btn.configure(state="disabled")
        self.status.configure(text="Converting...")
        self.log_widget.configure(state="normal")
        self.log_widget.delete("1.0", "end")
        self.log_widget.configure(state="disabled")

        # attach a GUI log handler for this run (file handler is added by
        # convert() and removed at the end of it)
        pkg_log = logging.getLogger("adv2mesh")
        pkg_log.setLevel(logging.INFO)
        for h in [h for h in pkg_log.handlers if isinstance(h, _TextHandler)]:
            pkg_log.removeHandler(h)
        gh = _TextHandler(self.log_widget)
        gh.setFormatter(logging.Formatter(
            "%(asctime)s  %(levelname)-7s  %(message)s", "%H:%M:%S"))
        pkg_log.addHandler(gh)

        threading.Thread(target=self._run, args=(inp, out), daemon=True).start()

    def _run(self, inp, out):
        try:
            report = convert(inp, out, loft=True, debug_png=True, verbose=False)
            self.root.after(0, lambda: self._done_ok(report))
        except ADVFormatError as e:
            self.root.after(0, lambda: self._done_err(
                "Not a recognised .ADV file:\n%s" % e))
        except Exception as e:                                       # noqa
            self.root.after(0, lambda: self._done_err(
                "Conversion failed:\n%s" % e))

    def _done_ok(self, report):
        c = report["object_counts"]
        self.status.configure(
            text="Done.  %d cutting planes  -  %d polished  -  inclusions: %s"
            % (c["cutting_planes"], c["polished_diamonds"], c["inclusions"]))
        self.convert_btn.configure(state="normal")
        self.open_btn.configure(state="normal")
        messagebox.showinfo(
            "adv2mesh",
            "Conversion complete.\n\nOutput folder:\n%s" % self.out_path.get())

    def _done_err(self, msg):
        self.status.configure(text="Error.")
        self.convert_btn.configure(state="normal")
        messagebox.showerror("adv2mesh", msg)

    # ---- main --------------------------------------------------------

    def run(self):
        self.root.mainloop()


def main():
    ConverterApp().run()


if __name__ == "__main__":
    main()
