# standalone - combined single-file build

This folder builds **one** portable Windows executable,
`dist/sdf_csv_converter.exe`, that behaves like a normal desktop app:

- **Double-click** it -> the **GUI** opens (with a splash screen while it loads).
- **Run it from a terminal with arguments** -> it runs the **CLI**.

It is completely self-contained and does **not** modify the
[`../sdf_csv_converter`](../sdf_csv_converter) package; it imports that package
as a library and reuses its RDKit PyInstaller hook.

For design details (launch dispatch, console attachment, build pipeline, and
comparison with the legacy dual-exe builds), see **[ARCHITECTURE.md](ARCHITECTURE.md)**.

## Build

Prerequisites (one-time):

```bash
pip install pyinstaller pillow
```

Then, from this `standalone/` folder:

```bash
python build_standalone.py
```

The exe is written to `standalone/dist/sdf_csv_converter.exe` (about 66 MB).
First launch is a little slow because a single-file exe unpacks itself to a temp
directory; the GUI splash screen covers that delay.

## Run

GUI (double-click, or):

```bash
dist\sdf_csv_converter.exe
```

CLI (same exe, with arguments):

```bash
dist\sdf_csv_converter.exe input.cdxml -o output.csv
dist\sdf_csv_converter.exe library.sdf  -o library.csv
dist\sdf_csv_converter.exe data.csv     -o data.sdf --smiles-col SMILES
dist\sdf_csv_converter.exe --version
dist\sdf_csv_converter.exe --help
```

CLI output supports **stdout/stderr redirection** (`> file`, `2> log`) because the
exe uses the Windows console subsystem. On the GUI path the console window is
hidden immediately after launch (a brief flash may appear on cold start).

## Conversion fidelity

The combined exe runs the **same parser** as the Python package and legacy
builds. All distributions share these behaviors (see also the main
[`README.md`](../sdf_csv_converter/README.md)):

### Free-text labels (page text)

- ChemDraw page-level `<t>` text (compound IDs like `PROJ-42`, captions) is
  **not** duplicated onto every structure.
- Each text object is assigned to the **nearest** top-level fragment by
  coordinates (heuristic).
- Output columns: **`Annotations`** (all assigned text), **`CompoundID`**
  (first code-like label detected).
- **Limitation:** dense or overlapping SAR plates may mis-associate a label —
  verify these columns in the output.

### Structure ordering

- CDXML/CDX rows are emitted in **document order** (single-threaded parse).
- Every row carries **`XmlIndex`** (0-based, monotonic) so sequence is always
  recoverable downstream.
- CSV metadata columns (`XmlIndex`, `Title`, `CompoundID`, ...) appear first.
- `--workers` does not reorder CDX/CDXML output.

Regression tests: [`../tests/test_cdx_table8.py`](../tests/test_cdx_table8.py).

## Files

```
standalone/
  app_entry.py         Combined entry point (GUI when no args, CLI with args)
  win_console.py       Console hide (GUI) + UTF-8 stdio (CLI)
  standalone.spec      PyInstaller spec (onefile, console subsystem, icon + splash)
  version_info.txt     Windows version/product metadata (keep in sync with __version__)
  build_standalone.py  Clean + build + report size
  ARCHITECTURE.md      Packaging design (launch flow, build pipeline, trade-offs)
  assets/
    app.ico            Multi-resolution app icon (rebrand by replacing this)
    splash.png         GUI splash image
  dist/                Build output (sdf_csv_converter.exe)
  build/               PyInstaller work dir (safe to delete)
```

## Rebranding

Replace `assets/app.ico` (and optionally `assets/splash.png`) with your own
artwork and rebuild. To change the displayed version/company/product strings,
edit `version_info.txt`.

## Size note

~66 MB is expected: the exe embeds CPython, RDKit, and OpenBabel. A smaller file
is only possible by dropping one of those dependencies. Installing
[UPX](https://upx.github.io/) and putting it on `PATH` before building will
compress it further (the spec already sets `upx=True`).

## License

Project source code: **[MIT License](../LICENSE)**.

Executable builds also bundle RDKit, OpenBabel, Python, and other libraries —
see **[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)** before redistribution.
