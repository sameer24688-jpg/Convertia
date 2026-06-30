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

_APP_TITLE = "Convertia"

# Modern palette (aligned with Convertia branding)
_BG = "#f0f4f8"
_CARD = "#ffffff"
_ACCENT = "#0d9488"
_ACCENT_HOVER = "#0f766e"
_ACCENT_DISABLED = "#94a3b8"
_TEXT = "#0f172a"
_MUTED = "#64748b"
_BORDER = "#cbd5e1"
_LOG_BG = "#1e293b"
_LOG_FG = "#e2e8f0"


def _setup_theme(root: tk.Tk) -> ttk.Style:
    """Apply a clean, modern ttk theme for Convertia."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=_BG)

    style.configure(".", background=_BG, foreground=_TEXT, font=("Segoe UI", 10))
    style.configure("TFrame", background=_BG)
    style.configure("Card.TFrame", background=_CARD)
    style.configure("Card.TLabel", background=_CARD, foreground=_TEXT)
    style.configure("Heading.TLabel", background=_CARD, foreground=_TEXT, font=("Segoe UI", 11, "bold"))
    style.configure("Muted.TLabel", background=_CARD, foreground=_MUTED, font=("Segoe UI", 9))
    style.configure("Section.TLabel", background=_BG, foreground=_TEXT, font=("Segoe UI", 11, "bold"))
    style.configure("TLabel", background=_BG, foreground=_TEXT)
    style.configure("TEntry", fieldbackground=_CARD, bordercolor=_BORDER, lightcolor=_BORDER, darkcolor=_BORDER)
    style.configure("TButton", padding=(10, 6))
    style.configure("TRadiobutton", background=_CARD, foreground=_TEXT)
    style.configure("TCheckbutton", background=_CARD, foreground=_TEXT)
    style.configure("TLabelframe", background=_BG, bordercolor=_BORDER)
    style.configure("TLabelframe.Label", background=_BG, foreground=_TEXT, font=("Segoe UI", 10, "bold"))
    style.configure("Options.TLabelframe", background=_CARD, bordercolor=_BORDER)
    style.configure("Options.TLabelframe.Label", background=_CARD, foreground=_TEXT, font=("Segoe UI", 10, "bold"))
    return style

def _asset_paths() -> tuple[str | None, str | None]:
    """Return (icon.ico path, logo.png path) for dev and frozen runs."""
    candidates = []
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", "")
        candidates.append(os.path.join(base, "assets"))
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(pkg_dir)
    candidates.extend([
        os.path.join(repo_root, "standalone", "assets"),
        repo_root,
    ])
    icon_path = None
    logo_path = None
    for folder in candidates:
        ico = os.path.join(folder, "app.ico")
        png = os.path.join(folder, "logo.png")
        if icon_path is None and os.path.isfile(ico):
            icon_path = ico
        if logo_path is None and os.path.isfile(png):
            logo_path = png
        if logo_path is None and os.path.isfile(os.path.join(folder, "Convertia.png")):
            logo_path = os.path.join(folder, "Convertia.png")
        if icon_path and logo_path:
            break
    return icon_path, logo_path


def _apply_window_branding(root: tk.Tk) -> str | None:
    root.title(_APP_TITLE)
    icon_path, logo_path = _asset_paths()
    if icon_path:
        try:
            root.iconbitmap(default=icon_path)
        except tk.TclError:
            pass
    return logo_path


def _popup_image_path() -> str | None:
    """Launch popup image: bundled assets first, then beside the exe."""
    candidates = []
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", "")
        candidates.append(os.path.join(base, "assets", "image.png"))
        candidates.append(os.path.join(os.path.dirname(sys.executable), "image.png"))
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(pkg_dir)
    candidates.extend([
        os.path.join(repo_root, "standalone", "assets", "image.png"),
        os.path.join(repo_root, "standalone", "dist", "image.png"),
    ])
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _show_launch_popup(root: tk.Tk) -> None:
    """Show image.png in a centered popup when the GUI starts."""
    path = _popup_image_path()
    if not path:
        return

    root.withdraw()
    popup = tk.Toplevel(root)
    popup.title(_APP_TITLE)
    popup.resizable(False, False)
    icon_path, _ = _asset_paths()
    if icon_path:
        try:
            popup.iconbitmap(default=icon_path)
        except tk.TclError:
            pass

    try:
        photo = tk.PhotoImage(file=path)
    except tk.TclError:
        root.deiconify()
        popup.destroy()
        return

    label = tk.Label(popup, image=photo, borderwidth=0, cursor="hand2")
    label.image = photo
    label.pack()

    hint = ttk.Label(popup, text="Click or press Esc to continue", font=("Segoe UI", 9))
    hint.pack(pady=(0, 8))

    popup.update_idletasks()
    w, h = popup.winfo_reqwidth(), popup.winfo_reqheight()
    sw, sh = popup.winfo_screenwidth(), popup.winfo_screenheight()
    popup.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def close(_event=None) -> None:
        try:
            popup.grab_release()
        except tk.TclError:
            pass
        popup.destroy()
        root.deiconify()

    popup.protocol("WM_DELETE_WINDOW", close)
    label.bind("<Button-1>", close)
    hint.bind("<Button-1>", close)
    popup.bind("<Escape>", close)
    popup.bind("<Return>", close)
    popup.after(4000, close)
    popup.grab_set()
    popup.focus_set()
    popup.wait_window()


def _detect_format(path: str) -> str:
    """Detect format from extension."""
    if not path:
        return ""
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    return ext


class ConverterGUI:
    _CONVERT_LABEL = "Convert"

    def __init__(self, root: tk.Tk):
        self.root = root
        logo_path = _apply_window_branding(root)
        root.geometry("720x680")
        root.minsize(640, 600)
        root.resizable(True, True)
        _setup_theme(root)

        outer = ttk.Frame(root, padding=20)
        outer.pack(fill=tk.BOTH, expand=True)

        if logo_path:
            try:
                self._logo_image = tk.PhotoImage(file=logo_path)
                ttk.Label(outer, image=self._logo_image).pack(anchor=tk.CENTER, pady=(0, 4))
            except tk.TclError:
                pass

        ttk.Label(
            outer,
            text="Chemical format conversion",
            font=("Segoe UI", 10),
            foreground=_MUTED,
        ).pack(anchor=tk.CENTER, pady=(0, 16))

        # ── Input card ──
        in_card = ttk.Frame(outer, style="Card.TFrame", padding=16)
        in_card.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(in_card, text="Input file", style="Heading.TLabel").pack(anchor=tk.W)
        in_frame = ttk.Frame(in_card, style="Card.TFrame")
        in_frame.pack(fill=tk.X, pady=(8, 0))
        self.in_path = tk.StringVar()
        ttk.Entry(in_frame, textvariable=self.in_path).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(in_frame, text="Browse…", command=self._browse_input).pack(side=tk.RIGHT, padx=(8, 0))
        self.in_info = tk.StringVar(value="Select SDF, CSV, CDX, or CDXML")
        ttk.Label(in_card, textvariable=self.in_info, style="Muted.TLabel").pack(anchor=tk.W, pady=(6, 0))

        # ── Output card ──
        out_card = ttk.Frame(outer, style="Card.TFrame", padding=16)
        out_card.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(out_card, text="Output", style="Heading.TLabel").pack(anchor=tk.W)

        fmt_row = ttk.Frame(out_card, style="Card.TFrame")
        fmt_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(fmt_row, text="Format:", style="Card.TLabel").pack(side=tk.LEFT)
        self.out_format = tk.StringVar(value="csv")
        ttk.Radiobutton(
            fmt_row, text="CSV", variable=self.out_format, value="csv",
            command=self._on_out_format_changed,
        ).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Radiobutton(
            fmt_row, text="SDF", variable=self.out_format, value="sdf",
            command=self._on_out_format_changed,
        ).pack(side=tk.LEFT, padx=(12, 0))

        out_frame = ttk.Frame(out_card, style="Card.TFrame")
        out_frame.pack(fill=tk.X, pady=(10, 0))
        self.out_path = tk.StringVar()
        ttk.Entry(out_frame, textvariable=self.out_path).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(out_frame, text="Browse…", command=self._browse_output).pack(side=tk.RIGHT, padx=(8, 0))
        self.out_info = tk.StringVar(value="")
        ttk.Label(out_card, textvariable=self.out_info, style="Muted.TLabel").pack(anchor=tk.W, pady=(6, 0))

        # ── Options ──
        opts_frame = ttk.LabelFrame(outer, text="Options", style="Options.TLabelframe", padding=12)
        opts_frame.pack(fill=tk.X, pady=(0, 16))

        r1 = ttk.Frame(opts_frame, style="Card.TFrame")
        r1.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(r1, text="SMILES column:", style="Card.TLabel").pack(side=tk.LEFT)
        self.smiles_col = tk.StringVar(value="SMILES")
        ttk.Entry(r1, textvariable=self.smiles_col, width=16).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(r1, text="Workers:", style="Card.TLabel").pack(side=tk.LEFT, padx=(16, 0))
        self.workers = tk.IntVar(value=0)
        ttk.Spinbox(r1, from_=0, to=32, textvariable=self.workers, width=5).pack(side=tk.LEFT, padx=(6, 0))

        r2 = ttk.Frame(opts_frame, style="Card.TFrame")
        r2.pack(fill=tk.X)
        self.gen_3d = tk.BooleanVar(value=False)
        ttk.Checkbutton(r2, text="3D coordinates", variable=self.gen_3d).pack(side=tk.LEFT)
        self.v3000 = tk.BooleanVar(value=False)
        ttk.Checkbutton(r2, text="V3000 SDF", variable=self.v3000).pack(side=tk.LEFT, padx=(16, 0))
        self.no_props = tk.BooleanVar(value=False)
        ttk.Checkbutton(r2, text="No computed properties", variable=self.no_props).pack(side=tk.LEFT, padx=(16, 0))

        # ── Convert button (high contrast) ──
        self.convert_btn = tk.Button(
            outer,
            text=self._CONVERT_LABEL,
            command=self._convert,
            bg=_ACCENT,
            fg="#ffffff",
            activebackground=_ACCENT_HOVER,
            activeforeground="#ffffff",
            disabledforeground="#ffffff",
            font=("Segoe UI", 13, "bold"),
            relief=tk.FLAT,
            borderwidth=0,
            cursor="hand2",
            padx=20,
            pady=14,
        )
        self.convert_btn.pack(fill=tk.X, pady=(0, 16))

        # ── Log ──
        ttk.Label(outer, text="Log", style="Section.TLabel").pack(anchor=tk.W)
        log_frame = ttk.Frame(outer)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 10))
        self.log_text = tk.Text(
            log_frame,
            height=8,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg=_LOG_BG,
            fg=_LOG_FG,
            insertbackground=_LOG_FG,
            relief=tk.FLAT,
            padx=8,
            pady=8,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=_BORDER,
            highlightcolor=_ACCENT,
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scroll.set)

        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr
        sys.stdout = _LogRedirect(self, "stdout")
        sys.stderr = _LogRedirect(self, "stderr")

        self.status = tk.StringVar(value="Ready")
        status_bar = tk.Label(
            outer,
            textvariable=self.status,
            bg=_BORDER,
            fg=_MUTED,
            anchor=tk.W,
            font=("Segoe UI", 9),
            padx=10,
            pady=6,
        )
        status_bar.pack(fill=tk.X)

    def _default_out_format_for_input(self, in_fmt: str) -> str:
        if in_fmt == "csv":
            return "sdf"
        return "csv"

    def _on_out_format_changed(self) -> None:
        out_fmt = self.out_format.get()
        path = self.out_path.get().strip()
        if path:
            base, _ = os.path.splitext(path)
            self.out_path.set(f"{base}.{out_fmt}")
        self.out_info.set(f"Output format: {out_fmt.upper()}")

    def _sync_out_format_from_path(self, path: str) -> None:
        fmt = _detect_format(path)
        if fmt in ("csv", "sdf"):
            self.out_format.set(fmt)
            self.out_info.set(f"Output format: {fmt.upper()}")

    # ── File dialogs ──
    def _browse_input(self):
        path = filedialog.askopenfilename(title="Select input file", filetypes=INPUT_EXTS)
        if path:
            self.in_path.set(path)
            fmt = _detect_format(path)
            self.in_info.set(f"Input format: {fmt.upper()}" if fmt else "Unknown input format")
            if fmt:
                self.out_format.set(self._default_out_format_for_input(fmt))
            if not self.out_path.get():
                base, _ = os.path.splitext(path)
                self.out_path.set(f"{base}.{self.out_format.get()}")
            self._on_out_format_changed()

    def _browse_output(self):
        out_fmt = self.out_format.get()
        path = filedialog.asksaveasfilename(
            title="Save output as",
            filetypes=OUTPUT_EXTS,
            defaultextension=f".{out_fmt}",
        )
        if path:
            base, ext = os.path.splitext(path)
            if ext.lower() not in (".csv", ".sdf"):
                path = f"{base}.{out_fmt}"
            self.out_path.set(path)
            self._sync_out_format_from_path(path)

    def _resolve_output_path(self, out_file: str, out_fmt: str) -> str:
        base, ext = os.path.splitext(out_file)
        if ext.lower() != f".{out_fmt}":
            return f"{base}.{out_fmt}"
        return out_file

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
        out_fmt = self.out_format.get().strip().lower()
        if out_fmt not in ("csv", "sdf"):
            messagebox.showerror("Error", "Please select output format: CSV or SDF.")
            return
        out_file = self._resolve_output_path(out_file, out_fmt)
        self.out_path.set(out_file)

        if not in_fmt:
            messagebox.showerror("Error", "Could not detect input format.\nUse .sdf, .csv, .cdx, or .cdxml.")
            return

        self.convert_btn.config(state=tk.DISABLED, text="Converting…", bg=_ACCENT_DISABLED)
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
                self.root.after(0, lambda: self._reset_convert_button())
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
            self.root.after(0, lambda: self._reset_convert_button())

    def _reset_convert_button(self) -> None:
        self.convert_btn.config(state=tk.NORMAL, text=self._CONVERT_LABEL, bg=_ACCENT)


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
    root.withdraw()
    root.update_idletasks()

    if getattr(sys, "frozen", False):
        try:
            from startup_errors import close_pyinstaller_splash

            close_pyinstaller_splash()
        except Exception:
            pass

    _show_launch_popup(root)
    ConverterGUI(root)
    root.deiconify()
    root.mainloop()


if __name__ == "__main__":
    main()