# Standalone packaging architecture

This document describes how the **combined single-file Windows executable**
(`dist/sdf_csv_converter.exe`) is built and how it behaves at runtime. The
standalone layer is a thin packaging shell around the existing
[`sdf_csv_converter`](../sdf_csv_converter) package; it does not duplicate or
modify conversion logic.

---

## Goals

| Goal | How it is met |
|------|----------------|
| One portable `.exe` for end users | PyInstaller `--onefile` bundles CPython, RDKit, OpenBabel, and the converter package |
| Double-click opens GUI | Console subsystem (`console=True`) with `hide_console_window()` on the GUI path |
| CLI redirect and piping work | Console subsystem inherits parent shell stdout/stderr; UTF-8 via `ensure_console()` |
| Same exe runs CLI from a terminal | `app_entry.py` dispatches on `sys.argv` |
| Do not fork the converter codebase | Imports `sdf_csv_converter.*` from the repo root via `pathex`; reuses `sdf_csv_converter/hooks/` |
| Polished desktop feel | Custom icon, embedded version metadata, splash screen during onefile unpack |

---

## Repository layout

```
NA/
├── sdf_csv_converter/          # Core package (unchanged by standalone build)
│   ├── main.py                 # CLI: argparse + dispatch
│   ├── gui.py                  # GUI: tkinter window
│   ├── cdx_parser.py           # CDXML/CDX parsing
│   ├── hooks/hook-rdkit.py     # PyInstaller RDKit DLL hook (reused)
│   └── ...
└── standalone/                 # Packaging layer (this document)
    ├── app_entry.py            # Frozen entry point: GUI vs CLI
    ├── win_console.py          # Windows console attach + UTF-8 stdio
    ├── standalone.spec         # PyInstaller spec
    ├── version_info.txt        # Windows VSVersionInfo resource
    ├── build_standalone.py     # Clean + build script
    ├── assets/
    │   ├── app.ico             # Multi-resolution application icon
    │   └── splash.png          # Shown while onefile payload unpacks
    └── dist/
        └── sdf_csv_converter.exe
```

---

## Runtime flow

### Launch dispatch

```mermaid
flowchart TD
    start["sdf_csv_converter.exe starts"] --> frozen{"PyInstaller frozen?"}
    frozen -->|yes| bundled["Package already on sys.path"]
    frozen -->|no dev| path["Prepend NA repo root to sys.path"]
    bundled --> args{"len(sys.argv) > 1?"}
    path --> args
    args -->|no| hideConsole["win_console.hide_console_window()"]
    hideConsole --> guiPath["Import sdf_csv_converter.gui.main"]
    args -->|yes| cliPath["win_console.ensure_console()"]
    cliPath --> cliImport["Import sdf_csv_converter.main.main"]
    guiPath --> splashClose["pyi_splash.close() if present"]
    cliImport --> splashClose
    splashClose --> guiRun["gui.main() -> Tk mainloop"]
    splashClose --> cliRun["main() -> argparse + convert"]
```

**Rules:**

- **No arguments** (typical double-click): hide the console window, then run the tkinter GUI.
- **Any arguments** (terminal invocation): ensure UTF-8 console streams, then run the CLI.

The launcher closes the PyInstaller splash **after** heavy imports (RDKit, OpenBabel,
tkinter) complete so the splash covers the slow onefile extraction and module
load, not the idle GUI window.

### CLI console (Windows)

The exe uses PyInstaller's **console** bootloader (`console=True` in
`standalone.spec`), so stdout/stderr pipes from `cmd` / PowerShell are inherited
and redirection (`> file`, `2> log`) works. `ensure_console()` additionally sets
the console code page and Python streams to UTF-8 so Unicode in help text and
the conversion summary (e.g. `→`) does not raise `UnicodeEncodeError` on legacy
cp1252 consoles.

```mermaid
sequenceDiagram
    participant User as Terminal
    participant Entry as app_entry.py
    participant Win as win_console.py
    participant CLI as sdf_csv_converter.main

    User->>Entry: exe file.cdxml -o out.csv
    Entry->>Win: ensure_console()
    Win->>Win: SetConsoleOutputCP UTF-8
    Win->>Win: reconfigure stdout/stderr UTF-8
    Entry->>CLI: main()
    CLI-->>User: progress, summary, errors via inherited pipes
```

On the **GUI** path, `hide_console_window()` calls `ShowWindow(SW_HIDE)` on the
auto-allocated console (frozen exe only). A brief console flash may appear
before hide runs on cold start.

---

## Build pipeline

```mermaid
flowchart LR
    spec["standalone.spec"] --> pi["PyInstaller --onefile"]
    entry["app_entry.py"] --> pi
    pkg["sdf_csv_converter/*"] --> pi
    rdkit["rdkit + openbabel + tqdm"] --> pi
    assets["app.ico + splash.png + version_info.txt"] --> pi
    hook["hooks/hook-rdkit.py"] --> pi
    pi --> exe["dist/sdf_csv_converter.exe"]
```

### `standalone.spec` highlights

| Setting | Value | Rationale |
|---------|-------|-----------|
| `Analysis(..., pathex=[NA_ROOT, HERE])` | Repo root + standalone dir | Resolves `import sdf_csv_converter` without copying source |
| `hookspath=[sdf_csv_converter/hooks]` | Reuse existing RDKit hook | Avoid duplicating DLL collection logic |
| `collect_all("rdkit")` etc. | Bundles DLLs and data files | RDKit/OpenBabel need native libraries at runtime |
| `excludes` | matplotlib, scipy, pandas, Qt, jupyter, zmq | Smaller exe (~66 MB vs ~117 MB for legacy builds) |
| `console=True` | Console bootloader (`run.exe`) | CLI stdout/stderr redirect; GUI path hides console via `hide_console_window()` |
| `Splash(splash.png)` | Tcl/Tk splash during unpack | Masks onefile extraction delay for GUI users |
| `icon=app.ico`, `version=version_info.txt` | Explorer icon + Properties dialog | Desktop-app polish |

### Build command

```bash
cd standalone
python build_standalone.py
```

`build_standalone.py` deletes `build/` and `dist/`, runs
`python -m PyInstaller --noconfirm --clean standalone.spec`, and prints the
output path and size.

---

## Relationship to the core package

The standalone exe is **not** a fork. At runtime it calls the same functions as
the Python package:

| Mode | Entry | Core call |
|------|-------|-----------|
| GUI | `app_entry.run()` (no args) | `sdf_csv_converter.gui.main()` |
| CLI | `app_entry.run()` (with args) | `sdf_csv_converter.main.main()` |

All conversion paths (`sdf_to_csv`, `csv_to_sdf`, `cdx_to_csv`, `cdx_to_sdf`,
`cdx_parser`, `molecule_processor`) live in `sdf_csv_converter/` and are
documented in the main [README](../sdf_csv_converter/README.md) and the core
Architecture section there.

### Conversion fidelity (shared with all distributions)

The standalone exe does not implement parsing itself; it calls the same
`sdf_csv_converter` modules as `python -m sdf_csv_converter` and the legacy exes.

```mermaid
flowchart LR
    pageTexts["Page-level t text"] --> nearest["Nearest fragment by coordinates"]
    nearest --> ann["Annotations column"]
    nearest --> cid["CompoundID column"]
    fragments["Top-level fragments in document order"] --> xmlidx["XmlIndex 0..N-1"]
    xmlidx --> csv["CSV rows in document order"]
```

**Free-text labels:** page text is assigned per-structure (not duplicated to
every row). See `_iter_page_structures` / `_nearest_index` in
[`cdx_parser.py`](../sdf_csv_converter/cdx_parser.py). Dense plates are a known
heuristic limitation — check `Annotations` and `CompoundID` in output.

**Structure ordering:** single-threaded CDX/CDXML parse; every row gets
`XmlIndex`; metadata columns first via `stream_utils.build_ordered_fieldnames`.
Locked by [`tests/test_cdx_table8.py`](../tests/test_cdx_table8.py).

### Comparison with legacy dual-exe builds

| Aspect | `standalone/dist/sdf_csv_converter.exe` | `sdf_csv_converter/dist/*.exe` |
|--------|----------------------------------------|--------------------------------|
| Count | **One** combined exe | Two (CLI + GUI) |
| Subsystem | Console (`run.exe`); hidden on GUI path | CLI: console; GUI: windowed |
| Size | ~66 MB | ~117 MB each |
| CLI redirect (`> file`) | **Yes** | Yes (console exe only) |
| Splash | Yes | No |
| Icon + version metadata | Yes | No (unless added manually) |
| Modifies core package | No | No |

---

## Startup performance

PyInstaller **onefile** executables extract their embedded archive to a temp
directory on every launch. For this project that payload is large (CPython +
RDKit + OpenBabel), so:

- **First launch** after build or after temp cleanup can take several seconds.
- The **GUI splash** (`assets/splash.png`) is shown during extraction and import.
- **Subsequent launches** may be faster if the OS temp cache is warm.

An **onedir** build or a proper installer would remove extraction overhead but
was intentionally out of scope for the portable single-exe deliverable.

---

## Rebranding and versioning

| Asset | File | Effect |
|-------|------|--------|
| Application icon | `assets/app.ico` | Explorer, taskbar, file Properties |
| Splash image | `assets/splash.png` | Shown during GUI/CLI cold start |
| Version strings | `version_info.txt` | Windows file Properties (Product version, Company, etc.) |
| Package version | `sdf_csv_converter/__init__.py` | `--version` CLI output; keep `version_info.txt` in sync |

After changing any asset, rebuild with `python build_standalone.py`.

---

## Dependencies (build-time only)

| Package | Role |
|---------|------|
| `pyinstaller` | Bundles Python app into `.exe` |
| `pillow` | Generates/resizes `app.ico` from source artwork (optional after initial assets exist) |
| `rdkit`, `openbabel`, `tqdm` | Runtime deps collected into the exe (must be installed in the build environment) |

---

## License

- **This repository’s code** (including `standalone/` launcher scripts): [MIT License](../LICENSE).
- **Bundled executables**: see [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) (RDKit BSD, OpenBabel GPL v2 when included, Python PSF, etc.).
