"""
GUI wrapper for sdf_csv_converter.
Double-click to run — no command line needed.

Provides:
- File picker for input (SDF, CSV, CDX, CDXML)
- File picker for output (automatically detected format)
- Optional settings (workers, 3D, V3000, SMILES column)
- Convert button with live progress output
"""
import os
import sys
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Ensure the package directory is importable
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, os.path.dirname(_script_dir))

from sdf_csv_converter import sdf_to_csv, csv_to_sdf, cdx_to_sdf, cdx_to_csv

# Supported extensions
INPUT_EXTS = [
    ("All supported", "*.sdf *.csv *.cdx *.cdxml"),
    ("SDF files", "*.sdf"),
    ("CSV files", "*.csv"),
    ("CDX files", "*.cdx"),
    ("CDXML files", "*.cdxml"),
    ("All files", "*.*"),
]
OUTPUT_EXTS = [
    ("SDF files", "*.sdf"),
    ("CSV files", "*.csv"),
]


def _detect_format(path: str) -> str:
    """Detect format from extension."""
    if not path:
        return ""
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    return ext


class ConverterGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("SDF/CSV/CDX Converter")
        root.geometry("650x520")
        root.resizable(True, True)

        # ── Styles ──
        style = ttk.Style()
        style.theme_use("clam")

        main = ttk.Frame(root, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        # ── Input file ──
        ttk.Label(main, text="Input File", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        in_frame = ttk.Frame(main)
        in_frame.pack(fill=tk.X, pady=(4, 0))
        self.in_path = tk.StringVar()
        ttk.Entry(in_frame, textvariable=self.in_path).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(in_frame, text="Browse...", command=self._browse_input).pack(side=tk.RIGHT, padx=(6, 0))

        # Info
        self.in_info = tk.StringVar(value="")
        ttk.Label(main, textvariable=self.in_info, foreground="gray", font=("Segoe UI", 8)).pack(anchor=tk.W, pady=(0, 10))

        # ── Output file ──
        ttk.Label(main, text="Output File", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        out_frame = ttk.Frame(main)
        out_frame.pack(fill=tk.X, pady=(4, 0))
        self.out_path = tk.StringVar()
        ttk.Entry(out_frame, textvariable=self.out_path).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(out_frame, text="Browse...", command=self._browse_output).pack(side=tk.RIGHT, padx=(6, 0))

        self.out_info = tk.StringVar(value="")
        ttk.Label(main, textvariable=self.out_info, foreground="gray", font=("Segoe UI", 8)).pack(anchor=tk.W, pady=(0, 10))

        # ── Options ──
        opts_frame = ttk.LabelFrame(main, text="Options", padding=8)
        opts_frame.pack(fill=tk.X, pady=(0, 10))

        # Row 1
        r1 = ttk.Frame(opts_frame)
        r1.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(r1, text="SMILES Column:").pack(side=tk.LEFT)
        self.smiles_col = tk.StringVar(value="SMILES")
        ttk.Entry(r1, textvariable=self.smiles_col, width=16).pack(side=tk.LEFT, padx=4)
        ttk.Label(r1, text="Workers:").pack(side=tk.LEFT, padx=(12, 0))
        self.workers = tk.IntVar(value=0)
        ttk.Spinbox(r1, from_=0, to=32, textvariable=self.workers, width=5).pack(side=tk.LEFT, padx=4)

        # Row 2 — checkboxes
        r2 = ttk.Frame(opts_frame)
        r2.pack(fill=tk.X)
        self.gen_3d = tk.BooleanVar(value=False)
        ttk.Checkbutton(r2, text="3D coordinates", variable=self.gen_3d).pack(side=tk.LEFT)
        self.v3000 = tk.BooleanVar(value=False)
        ttk.Checkbutton(r2, text="V3000 SDF", variable=self.v3000).pack(side=tk.LEFT, padx=12)
        self.no_props = tk.BooleanVar(value=False)
        ttk.Checkbutton(r2, text="No computed properties", variable=self.no_props).pack(side=tk.LEFT)

        # ── Convert button ──
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        self.convert_btn = ttk.Button(btn_frame, text="▶ Convert", command=self._convert)
        self.convert_btn.pack(fill=tk.X, ipady=4)

        # ── Output log ──
        ttk.Label(main, text="Log", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        log_frame = ttk.Frame(main)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(log_frame, height=8, wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scroll.set)

        # Redirect stdout/stderr to log
        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr
        sys.stdout = _LogRedirect(self, "stdout")
        sys.stderr = _LogRedirect(self, "stderr")

        # ── Status bar ──
        self.status = tk.StringVar(value="Ready")
        ttk.Label(main, textvariable=self.status, relief=tk.SUNKEN, anchor=tk.W,
                  font=("Segoe UI", 8), padding=(6, 2)).pack(fill=tk.X)

    # ── File dialogs ──
    def _browse_input(self):
        path = filedialog.askopenfilename(title="Select input file", filetypes=INPUT_EXTS)
        if path:
            self.in_path.set(path)
            fmt = _detect_format(path)
            self.in_info.set(f"Format: {fmt.upper() if fmt else 'unknown'}")
            # Auto-suggest output name
            if not self.out_path.get():
                base, _ = os.path.splitext(path)
                if fmt in ("sdf", "cdx", "cdxml"):
                    self.out_path.set(base + ".csv")
                else:
                    self.out_path.set(base + ".sdf")

    def _browse_output(self):
        path = filedialog.asksaveasfilename(title="Save output as", filetypes=OUTPUT_EXTS,
                                             defaultextension=".csv")
        if path:
            self.out_path.set(path)
            fmt = _detect_format(path)
            self.out_info.set(f"Format: {fmt.upper() if fmt else 'unknown'}")

    # ── Conversion ──
    def _convert(self):
        in_file = self.in_path.get().strip()
        out_file = self.out_path.get().strip()

        if not in_file:
            messagebox.showerror("Error", "Please select an input file.")
            return
        if not out_file:
            messagebox.showerror("Error", "Please select an output file.")
            return
        if not os.path.exists(in_file):
            messagebox.showerror("Error", f"Input file not found:\n{in_file}")
            return

        in_fmt = _detect_format(in_file)
        out_fmt = _detect_format(out_file)
        if not in_fmt or not out_fmt:
            messagebox.showerror("Error", "Could not detect file formats.\nUse .sdf, .csv, .cdx, or .cdxml extensions.")
            return

        self.convert_btn.config(state=tk.DISABLED, text="Converting...")
        self.status.set("Running...")
        self.log_text.delete(1.0, tk.END)

        thread = threading.Thread(target=self._run_conversion, args=(in_file, out_file, in_fmt, out_fmt),
                                  daemon=True)
        thread.start()

    def _run_conversion(self, in_file, out_file, in_fmt, out_fmt):
        try:
            print(f"Converting: {in_fmt.upper()} → {out_fmt.upper()}")
            print(f"Input:  {in_file}")
            print(f"Output: {out_file}")
            print("-" * 50)

            if in_fmt in ("cdx", "cdxml") and out_fmt == "sdf":
                stats = cdx_to_sdf.convert_cdx_to_sdf(
                    input_path=in_file, output_path=out_file,
                    workers=self.workers.get(),
                    generate_3d=self.gen_3d.get(),
                    use_v3000=self.v3000.get(),
                    no_properties=self.no_props.get(),
                )
            elif in_fmt in ("cdx", "cdxml") and out_fmt == "csv":
                stats = cdx_to_csv.convert_cdx_to_csv(
                    input_path=in_file, output_path=out_file,
                    workers=self.workers.get(),
                    no_properties=self.no_props.get(),
                )
            elif in_fmt == "sdf" and out_fmt == "csv":
                stats = sdf_to_csv.convert_sdf_to_csv(
                    input_path=in_file, output_path=out_file,
                    workers=self.workers.get(),
                    no_properties=self.no_props.get(),
                )
            elif in_fmt == "csv" and out_fmt == "sdf":
                stats = csv_to_sdf.convert_csv_to_sdf(
                    input_path=in_file, output_path=out_file,
                    smiles_col=self.smiles_col.get(),
                    workers=self.workers.get(),
                    generate_3d=self.gen_3d.get(),
                    use_v3000=self.v3000.get(),
                )
            else:
                print(f"ERROR: Unsupported conversion: {in_fmt} → {out_fmt}")
                self.root.after(0, lambda: self.convert_btn.config(state=tk.NORMAL, text="▶ Convert"))
                self.root.after(0, lambda: self.status.set("Error — unsupported conversion"))
                return

            print("-" * 50)
            print(f"  Total:    {stats.get('total', 0)}")
            print(f"  Success:  {stats.get('success', 0)}")
            print(f"  Failed:   {stats.get('failed', 0)}")
            if stats.get("skipped", 0) > 0:
                print(f"  Skipped:  {stats.get('skipped', 0)}")
            print()
            print("Conversion complete!")
            self.root.after(0, lambda: self.status.set("Done ✓"))
            self.root.after(0, lambda: messagebox.showinfo(
                "Done",
                f"Conversion complete!\n\n"
                f"Total: {stats.get('total', 0)}\n"
                f"Success: {stats.get('success', 0)}\n"
                f"Failed: {stats.get('failed', 0)}"
            ))
        except Exception as e:
            traceback.print_exc()
            self.root.after(0, lambda: self.status.set("Error ✗"))
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.root.after(0, lambda: self.convert_btn.config(state=tk.NORMAL, text="▶ Convert"))


class _LogRedirect:
    """Redirects print/write to the GUI log text widget."""
    def __init__(self, gui: ConverterGUI, tag: str):
        self.gui = gui
        self.tag = tag

    def write(self, s: str):
        if s and s.strip():
            self.gui.log_text.after(0, lambda: self._append(s))

    def _append(self, s: str):
        self.gui.log_text.insert(tk.END, s)
        self.gui.log_text.see(tk.END)

    def flush(self):
        pass


def main():
    root = tk.Tk()
    app = ConverterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()