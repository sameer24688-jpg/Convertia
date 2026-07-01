# standalone - combined single-file build

This folder builds **one** portable Windows executable,
`dist/Convertia.exe`, that behaves like a normal desktop app:

- **Double-click** it → the **GUI** opens (splash → launch popup → main window with CSV/SDF output picker).
- **Run it from a terminal with arguments** → it runs the **CLI**.

Ship **`dist/Convertia.zip`** (from `python build_standalone.py --zip`) to colleagues.
The zip includes `Convertia.exe`, `image.png`, and `README.txt`.

It is completely self-contained and does **not** modify the
[`../sdf_csv_converter`](../sdf_csv_converter) package; it imports that package
as a library and reuses its RDKit PyInstaller hook.

For design details (launch dispatch, console attachment, build pipeline, and
comparison with the legacy dual-exe builds), see **[ARCHITECTURE.md](ARCHITECTURE.md)**.

For sharing the exe with other people (SmartScreen, onefile vs onedir, error
logs), see **[DISTRIBUTION.md](DISTRIBUTION.md)**.

## Build

Prerequisites (one-time):

```bash
pip install pyinstaller pillow
```

Then, from this `standalone/` folder:

```bash
python build_standalone.py --zip
```

For locked-down PCs, prefer a folder build:

```bash
python build_standalone.py --onedir --zip
```

The exe is written to `standalone/dist/Convertia.exe` (about 66 MB).
`standalone/dist/image.png` is copied there automatically on build.
First launch is a little slow because a single-file exe unpacks itself to a temp
directory; the GUI splash screen covers that delay.

## GUI

The desktop window (`sdf_csv_converter/gui.py`) provides:

- **Input** — drag and drop SDF, CSV, CDX, or CDXML onto the window, or use **Browse…**
- **Output format** — choose **CSV** or **SDF** (radio buttons)
- **Output file** — browse save path (extension follows selected format)
- **Convert** — high-contrast teal action button
- **Log** — live conversion output

Startup failures write **`convertia_error.log`** beside the exe and show an error dialog.

## Run

GUI (double-click, or):

```bash
dist\Convertia.exe
```

CLI (same exe, with arguments):

```bash
dist\Convertia.exe input.cdxml -o output.csv
dist\Convertia.exe library.sdf  -o library.csv
dist\Convertia.exe data.csv     -o data.sdf --smiles-col SMILES
dist\Convertia.exe --version
dist\Convertia.exe --help
```

CLI output supports **stdout/stderr redirection** (`> file`, `2> log`) because the
exe uses the Windows console subsystem. On the GUI path the console window is
hidden immediately after launch (a brief flash may appear on cold start).

## Conversion fidelity

The combined exe runs the **same parser** as the Python package and legacy
builds. All distributions share these behaviors (see also the main
[`README.md`](../sdf_csv_converter/README.md)):

### Free-text labels (page text)

- ChemDraw **compound names** (IUPAC captions under each structure) are read from
  ``chemicalproperty`` elements and written to the **`Title`** column.
- Other page-level ``<t>`` text (compound IDs like `PROJ-42`, notes) is assigned
  to the **nearest** page-level structure fragment by coordinates (heuristic).
- Output columns: **`Title`** (compound name), **`Annotations`** (other assigned
  text), **`CompoundID`** (first code-like label detected).
- **Limitation:** dense or overlapping SAR plates may still mis-associate
  non-name labels — verify `CompoundID` and `Annotations` in the output.

### Structure ordering

- CDXML/CDX rows are emitted in **document order** (single-threaded parse).
- Every row carries **`XmlIndex`** (0-based, monotonic) so sequence is always
  recoverable downstream.
- CSV metadata columns (`XmlIndex`, `Title`, `CompoundID`, ...) appear first.
- RDKit computed columns include `CLogP` (JPLogP atom-contribution lipophilicity,
  not Wildman–Crippen logP) and `NumStereoCenters` (stereogenic atom count).
- `--workers` does not reorder CDX/CDXML output.

Regression tests: [`../tests/test_cdx_table8.py`](../tests/test_cdx_table8.py).

## Relationship to `sdf_csv_converter`

**`standalone/` does not contain a second copy of the converter.** At build time,
PyInstaller freezes the [`sdf_csv_converter/`](../sdf_csv_converter/) package from
the repository root into `Convertia.exe`. The standalone folder only provides the
launcher (`app_entry.py`), console handling, and build specs.

| Location | What it is |
|----------|------------|
| [`sdf_csv_converter/`](../sdf_csv_converter/) | **Source of truth** — edit Python here |
| `standalone/dist/Convertia.exe` | Onefile build (GUI + CLI) |
| `standalone/dist/Convertia/` | Onedir build (folder + `Convertia.exe`) |
| ~~`standalone/Convertia/`~~ | **Obsolete** — do not use; removed on rebuild |

Rebuild after changing `sdf_csv_converter`:

```bash
cd standalone
python build_standalone.py --both    # onefile + onedir
python check_source_sync.py          # confirm dist matches source
```

`standalone/dist/` does **not** hold a second copy of the Python source — PyInstaller freezes `sdf_csv_converter/` into the exe at build time. `SOURCE_STAMP.txt` in `dist/` records SHA-256 hashes of every package file so you can verify sync.

## Files

```
standalone/
  app_entry.py         Combined entry point (GUI when no args, CLI with args)
  startup_errors.py    Startup failure log + message box
  win_console.py       Console hide (GUI) + UTF-8 stdio (CLI)
  generate_assets.py   Build icons/splash/logo/popup from ../Convertia.png
  standalone.spec      PyInstaller onefile spec
  standalone_onedir.spec  PyInstaller folder spec (locked-down PCs)
  version_info.txt     Windows version/product metadata
  build_standalone.py  Clean + build + optional zip
  DISTRIBUTION.md      Sharing and troubleshooting for end users
  ARCHITECTURE.md      Packaging design (launch flow, build pipeline)
  assets/
    app.ico            Application icon
    splash.png         PyInstaller splash
    logo.png           GUI header image
    image.png          Launch popup image
  dist/                Build output
                         Convertia.exe      onefile (GUI + CLI)
                         Convertia/         onedir folder build
                         image.png, README.txt, Convertia.zip
  build/               PyInstaller work dir (safe to delete)
```

## Rebranding

Replace `../Convertia.png` and run `python generate_assets.py` to refresh
`assets/app.ico`, `assets/splash.png`, and `assets/logo.png`, or let
`build_standalone.py` regenerate them automatically when the source image changes.
To change the displayed version/company/product strings, edit `version_info.txt`.

## Size note

~66 MB is expected: the exe embeds CPython, RDKit, and OpenBabel. A smaller file
is only possible by dropping one of those dependencies. Installing
[UPX](https://upx.github.io/) and putting it on `PATH` before building will
compress it further (the spec already sets `upx=True`).

## License & acknowledgements

| Document | Scope |
|----------|--------|
| **[`LICENSE`](../LICENSE)** | MIT — `standalone/` launcher scripts and build tooling |
| **[`ACKNOWLEDGEMENTS.md`](../ACKNOWLEDGEMENTS.md)** | Credits (RDKit, CDK/JPLogP, Open Babel, ChemDraw format) |
| **[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)** | Redistribution guidance for `Convertia.exe` |

Project source code: **MIT**. Executable builds bundle RDKit (BSD), JPLogP (LGPL),
OpenBabel (GPL v2 when included), Python (PSF), and other libraries — see
**`THIRD_PARTY_NOTICES.md`** before redistribution.
