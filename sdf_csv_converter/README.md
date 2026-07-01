# sdf_csv_converter

Convert between SDF, CSV, CDX, and CDXML. **Chemical connectivity and ChemDraw metadata are preserved; 2D drawing layout is not.**

---

## Quick Start

**Recommended (single combined app)** — double-click `standalone/dist/Convertia.exe` or share `standalone/dist/Convertia.zip`. The same file runs the CLI when launched from a terminal with arguments (stdout/stderr redirect supported). CDXML output includes per-structure **`Annotations`** / **`CompoundID`** (coordinate-assigned page text) and monotonic **`XmlIndex`** row ordering. See [Standalone combined .exe](#standalone-combined-exe), [`../standalone/README.md`](../standalone/README.md#conversion-fidelity), and [`../standalone/ARCHITECTURE.md`](../standalone/ARCHITECTURE.md).

**GUI** — double-click [`Convertia.bat`](Convertia.bat) in this folder (or `standalone/dist/Convertia.exe`). During development: `python -m sdf_csv_converter.gui`. **Drag and drop** an input file onto the window, or use **Browse…**; choose **CSV** or **SDF** output format, set the output path, then click **Convert**.

**CLI** -- open a terminal and run:

```bash
Convertia.exe input.sdf -o output.csv
Convertia.exe input.csv -o output.sdf --smiles-col SMILES
Convertia.exe table.cdxml -o table.sdf
Convertia.exe table.cdx   -o table.csv       # requires OpenBabel
```

> **Distribution options:** (1) the combined single-file exe in [`../standalone/`](../standalone/) (~66 MB, GUI + CLI in one file, CLI redirect works), or (2) two separate exes built from this package: `sdf_csv_converter_gui.exe` (windowed, GUI only) and `sdf_csv_converter.exe` (console, for scripting). All use the **same parser** — identical label assignment, `XmlIndex` ordering, and chemistry. See [Distribution and CLI output](#distribution-and-cli-output).

---

## Supported Conversions

| Input / Output | SDF | CSV |
|:---|---:|:---:|
| SDF (.sdf) | -- | Yes |
| CSV (.csv) | Yes | -- |
| CDXML (.cdxml) | Yes | Yes |
| CDX (.cdx) [+] | Yes | Yes |

> [+] CDX binary requires OpenBabel (`pip install openbabel`). Export as CDXML from ChemDraw to avoid this dependency.

---

## What's Preserved vs Reconstructed

| Data | Preserved | Reconstructed (RDKit) |
|------|:---:|:---:|
| Atoms, bonds, connectivity | Yes | |
| Abbreviations / nicknames (OMe, Ph, Boc...) | Yes -- expanded to full atoms from ChemDraw's embedded fragment | |
| R-groups (R, R1, R2...) | Yes -- as dummy atoms with map numbers (`[*:1]`) | |
| Molecule titles (in-fragment text) | Yes | |
| Atom label *text* | Yes (used to build connectivity) | |
| ChemDraw properties (`ChemDraw_*` columns) | Yes | |
| Page text / compound IDs (e.g. PROJ-42) | Assigned to nearest structure by coordinates | |
| Compound names (IUPAC captions) | Yes — via ChemDraw ``chemicalproperty`` links | |
| Row order (`XmlIndex` column) | Yes (document order) | |
| SMILES | | Yes (canonical, may differ from CDX) |
| Molecular weight, formula, CLogP, stereocenters | | Yes (computed) |
| 3D coordinates (--3d) | | Yes (ETKDG + MMFF) |
| **2D coordinates, label placement, bond styles, arrows, color** | | **Not retained** |

> Single-element atom labels are used to build the structure (e.g. `OH` -> oxygen). Multi-atom abbreviations (Ph, OMe, Boc) are now **expanded into their real atoms** using the expansion ChemDraw embeds in the file, so `Formula`/`MolecularWeight`/`SMILES` are correct. R-groups become dummy atoms carrying their map number. Drawn label *positions* are still not retained, and multi-attachment linker nicknames are not expanded -- see [Known Limitations](#known-limitations).

---

## Output Columns: Ordering & Property Sources

### Row ordering

- CDXML/CDX -> CSV/SDF emits rows in **document order**, and every row carries an explicit **`XmlIndex`** column (0-based) plus an internal `page_index`, so the original sequence is always recoverable even if a downstream tool re-sorts the file.
- Parsing is **single-threaded** for the CDX/CDXML paths, so order is never scrambled. The `--workers` option is accepted for compatibility but has **no effect** on CDX/CDXML conversion (it does not currently parallelize the SDF/CSV paths either).

### Property sources (no silent overwrites)

CSV columns / SDF tags come from two distinct sources and are kept in separate namespaces:

| Source | Naming | Examples |
|--------|--------|----------|
| RDKit (computed) | bare names | `SMILES`, `MolecularWeight`, `Formula`, `CLogP`, `TPSA`, `NumStereoCenters`, ... |
| ChemDraw (from CDXML) | `ChemDraw_` prefix | `ChemDraw_LogP`, `ChemDraw_MeltingPoint` |
| Parser metadata | bare names | `XmlIndex`, `Title`, `CompoundID`, `Annotations` |

Because ChemDraw values are prefixed, they can never overwrite the RDKit-computed columns (previously both used `MolecularWeight`/`LogP`, so ChemDraw label templates like `"Molecular Weight: "` clobbered the real numbers). Empty ChemDraw label templates are dropped entirely.

The RDKit lipophilicity column **`CLogP`** is computed with **JPLogP** (Plante & Werner, J Cheminform 2018) — an atom-contribution model ported from CDK. It is **not** RDKit Wildman–Crippen `MolLogP` (logP/SlogP) and **not** BioByte/ACD CLogP. If ChemDraw stores its own CLogP in the file, that value appears separately as **`ChemDraw_CLogP`**.

### Column order in CSV

1. Metadata: `XmlIndex`, `Title`, `CompoundID`, `Annotations` (only those present)
2. RDKit standard descriptors (`SMILES`, `MolecularWeight`, `Formula`, `CLogP`, `TPSA`, `NumHAcceptors`, `NumHDonors`, `NumRotatableBonds`, `NumHeavyAtoms`, `NumStereoCenters`)
3. Other discovered properties (sorted)
4. `ChemDraw_*` properties (sorted, grouped last)

---

## Known Limitations

| Severity | Limitation | Workaround |
|:---:|---|---|
| Critical | 2D drawing elements (coordinates, bond styles, arrows, colors) are not preserved | Export structures as CDXML from ChemDraw, use the CSV for data |
| Critical | Complex stereochemistry may not survive roundtrip | Verify stereo after conversion; RDKit stereo handling improves each release |
| Medium | Multi-attachment nicknames (linkers/superatoms with 2+ attachment points, e.g. a drawn `-OCH2O-` bridge) are not expanded -- they collapse to a single atom (graceful fallback) | Draw such linkers as explicit atoms in ChemDraw before export |
| Medium | A bare abbreviation label with no embedded expansion fragment falls back to a single carbon for unknown groups | Re-type the abbreviation in ChemDraw so it carries its expansion, or draw the group out explicitly |
| High | Page text -> structure assignment uses coordinates only for *non-name* captions (compound IDs, notes). Compound **names** are read from ChemDraw ``chemicalproperty`` ``BasisObjects`` links. Dense plates may still mis-associate non-name labels | Check `Title`, `CompoundID`, and `Annotations` columns |
| Critical | CDX binary requires OpenBabel (separate install); CDXML/SDF/CSV work without it | `pip install openbabel` or export as CDXML from ChemDraw |
| High | CSV/SDF multiline fields may be fragile with malformed inputs | Use `--strict` flag to fail on raw newlines instead of silently escaping |
| High | PyInstaller `.exe` may have DLL bundling issues with RDKit or OpenBabel | Run `pyinstaller build.spec` or use the Python package directly |
| Medium | Canonical SMILES from RDKit may differ from original CDX representation | Both SMILES represent the same molecule; use a canonicalizer if matching is needed |
| Medium | `--workers` does not currently parallelize conversion (CDX/CDXML parsing is single-threaded to preserve row order; SDF/CSV paths are also sequential today) | Safe to omit; it is accepted but a no-op. Performance is dominated by RDKit property computation -- use `--no-properties` for large files |

---

## CLI Reference

```
sdf_csv_converter <input> -o <output> [options]

Options:
  --from {sdf,csv,cdx,cdxml}   Force input format
  --to {sdf,csv}               Force output format
  --smiles-col NAME            CSV SMILES column (default: "SMILES")
  --workers N                  Accepted but currently a no-op (see Performance)
  --3d                         Generate 3D coordinates
  --v3000                      Write SDF in V3000 format
  --no-properties              Skip RDKit property computation
  --max-scan N                 Max molecules to process (0 = all)
  --chunk-size N               Molecules per parallel chunk (default: 100)
  --strict                     Fail on input errors instead of skipping
  --log-file PATH              Write errors/warnings to file
  --verbose, -v                Verbose output
  --version                    Show version
```

### Examples

```bash
# SDF to CSV with metadata
sdf_csv_converter.exe library.sdf -o library.csv

# CSV to SDF with 3D coordinates
sdf_csv_converter.exe compounds.csv -o compounds.sdf --smiles-col Structure --3d

# CDXML to SDF (preserves titles, labels, ChemDraw properties)
sdf_csv_converter.exe Table-1.cdxml -o Table-1.sdf

# CDXML to CSV (all metadata as columns)
sdf_csv_converter.exe Table-1.cdxml -o Table-1.csv

# Fast conversion (skip property computation)
sdf_csv_converter.exe huge.sdf -o huge.csv --no-properties

# Strict mode -- fail on malformed CSV fields
sdf_csv_converter.exe data.csv -o data.sdf --strict
```

---

## Architecture

```
 +-- CLI (.exe) ----------------+  +-- GUI (.exe) -----------------+
 |  main.py                     |  |  gui.py                       |
 |    +-- cli.py (argparse)     |  |    +-- tkinter file pickers   |
 |                              |  |    +-- drag-and-drop input  |
 |                              |  |         + options + log view  |
 +--------------+---------------+  +--------------+----------------+
                |                                 |
         +------+---------------------------------+------+
         |           Core conversion engine              |
         |                                               |
         |  SDF <-> CSV (streaming, 2-pass columns)      |
         |  +-- sdf_to_csv.py   (sanitize + RDKit props) |
         |  +-- csv_to_sdf.py   (V2000/V3000, optional 3D)
         |                                               |
         |  CDX/CDXML -> SDF/CSV                         |
 |  +-- cdx_parser.py   (tree-based, ns-agnostic)|
 |  |   +-- Page-level fragments (+ groups)       |
 |  |   +-- Expands nickname fragments (OMe, Ph) |
 |  |   +-- R-groups -> dummy atoms ([*:1])      |
 |  |   +-- Atom labels (OH, NH, Me, F...)       |
 |  |   +-- Bond stereo (Display -> BondDir)     |
         |  |   +-- NumHydrogens -> explicit H           |
         |  |   +-- CDX binary -> CDXML via OpenBabel    |
         |  +-- cdx_to_sdf.py   (CDX->CDXML->SDF)        |
         |  +-- cdx_to_csv.py   (CDX->CDXML->CSV)        |
         |                                               |
         |  Shared utilities                             |
         |  +-- molecule_processor.py  (RDKit: SMILES,   |
         |  |   MW, formula, CLogP, TPSA, 3D embedding)   |
         |  +-- stream_utils.py (multiprocessing, tqdm,  |
         |      newline escaping, validation)             |
         +-----------------------------------------------+
```

### CDXML Parser Details

The CDXML parser (`cdx_parser.py`) uses tree-based XML parsing (not streaming iterparse) for reliable parent-child detection:

1. **Namespace-agnostic** -- Works with both namespaced CDXML (`xmlns="..."`) and bare tags
2. **Page-level structures** -- Processes `<fragment>` elements that are direct children of `<page>`, or direct children of page-level `<group>` elements (ChemDraw often wraps each structure in a group), as separate structures
3. **Nickname / abbreviation expansion** -- Atoms drawn as Me, OMe, Ph, Boc, ... carry ChemDraw's full expansion as an embedded `<fragment>` with an `ExternalConnectionPoint` marking the attachment. The parser flattens these into the parent structure and rewires the bond onto the attachment atom, so the real chemistry reaches the output. Single-attachment only; multi-attachment linkers fall back to a single atom
4. **R-groups** -- Labels `R`/`R1`/`R2` and `GenericNickname` nodes become RDKit dummy atoms (atomic number 0) with atom-map numbers (e.g. `[*:1]`)
5. **Atom label resolution** -- Maps CDXML labels (OH, NH, CH3, N, O, F, Br) to atomic numbers using a safe lookup table (no RDKit post-condition violations)
6. **Bond stereo** -- `Display` attributes (WedgedHash, Bold, Dashed) mapped to RDKit `BondDir` (BEGINWEDGE, BEGINDASH)
7. **Hydrogen handling** -- `NumHydrogens` attribute sets explicit H count on RDKit atoms
8. **CDX binary** -- Falls back to OpenBabel for binary `.cdx` files, with:
   - **Empty molecule filtering** -- Skips 0-atom molecules that OpenBabel may produce from drawing elements
   - **Consecutive-empty guard** -- Detects broken CDX files (e.g., ChemDraw 25.5) that cause OpenBabel to loop infinitely, and terminates after 50 consecutive empty reads
   - **Duplicate detection** -- Prevents re-reading the same molecule via atom/bond hash comparison
9. **Coordinate-based text assignment** -- Page-level `<t>` text (compound IDs, captions) is assigned to the nearest fragment by position rather than duplicated onto every structure; a `CompoundID` is detected from code-like labels
10. **Explicit ordering** -- Each structure carries `xml_index`/`page_index`; the `XmlIndex` column makes row order recoverable
11. **Property namespacing** -- ChemDraw ChemProp values are emitted as `ChemDraw_*` so they never overwrite RDKit-computed columns; empty label templates are dropped

---

## Performance

- **Streaming**: Molecules are parsed one at a time; memory is constant regardless of file size
- **Two-pass column discovery**: SDF-to-CSV scans property names before writing, ensuring consistent CSV headers
- **Single-threaded**: Conversion is currently sequential. `--workers` is accepted for compatibility but has no effect; CDX/CDXML parsing is deliberately single-threaded to preserve row order.

Tune for your data:
| Dataset | Recommended |
|---------|-------------|
| < 100K molecules | defaults |
| 100K-1M | `--chunk-size 500` |
| > 1M | `--chunk-size 1000 --no-properties` (RDKit property computation dominates runtime) |

---

## Build from Source

```bash
pip install -r requirements.txt
python -m sdf_csv_converter --help
```

### Standalone combined .exe (recommended)

One portable Windows executable with **GUI on double-click** and **CLI when given arguments** (Convertia branding, icon, splash, launch popup). Built from a separate folder that does not modify this package:

```bash
pip install pyinstaller pillow
cd ../standalone
python build_standalone.py
# Output: standalone/dist/sdf_csv_converter.exe (~66 MB)
```

Details: [`../standalone/README.md`](../standalone/README.md) and [`../standalone/ARCHITECTURE.md`](../standalone/ARCHITECTURE.md).

The combined exe uses `console=True` in [`standalone/standalone.spec`](../standalone/standalone.spec) so CLI redirection works; the GUI path hides the console window on launch.

### Distribution and CLI output

All distributions run the same conversion engine. Differences are **packaging only**:

| How you run | GUI | CLI `> redirect` / pipes | Notes |
|-------------|:---:|:---:|-------|
| `python -m sdf_csv_converter` | No | Yes | Development / scripting |
| [`standalone/dist/Convertia.exe`](../standalone/dist/Convertia.exe) | Double-click | **Yes** | Recommended single-file app |
| `sdf_csv_converter/dist/sdf_csv_converter.exe` (legacy) | No | Yes | `build.spec`, `console=True` |
| `sdf_csv_converter/dist/sdf_csv_converter_gui.exe` (legacy) | Double-click | No | `sdf_csv_converter_gui.spec`, `console=False` — not for scripted CLI |

### Build separate CLI + GUI .exe (legacy)

From this `sdf_csv_converter/` folder. The CLI spec uses **`console=True`** (redirect works); the GUI spec uses **`console=False`** (windowed only):

```bash
pip install pyinstaller
cd sdf_csv_converter

# CLI .exe
pyinstaller --onefile --name sdf_csv_converter --collect-all rdkit --collect-all openbabel --hidden-import tqdm main.py --additional-hooks-dir=hooks

# GUI .exe
pyinstaller --onefile --windowed --name sdf_csv_converter_gui --collect-all rdkit --collect-all openbabel --hidden-import tqdm --hidden-import tkinter gui.py --additional-hooks-dir=hooks

# Output: dist/sdf_csv_converter.exe, dist/sdf_csv_converter_gui.exe (~117 MB each)
```

Or use the spec files: `pyinstaller build.spec` (`console=True`, CLI) and `pyinstaller sdf_csv_converter_gui.spec` (`console=False`, GUI-only)

---

## Project Files

```
NA/
+-- sdf_csv_converter/           Core Python package (conversion engine)
|   +-- main.py, cli.py          CLI entry point and argument parsing
|   +-- gui.py                   GUI window (tkinter; CSV/SDF output picker)
|   +-- cdx_parser.py            CDXML parser (nickname expansion, R-groups, ordering)
|   +-- molecule_processor.py    RDKit property engine (SMILES, MW, CLogP, 3D)
|   +-- clogp.py                 JPLogP CLogP calculator (distinct from Wildman–Crippen logP)
|   +-- jplogp_weights.py        JPLogP model coefficients (CDK/LGPL)
|   +-- stream_utils.py          I/O, column ordering, tqdm, validation
|   +-- sdf_to_csv.py, csv_to_sdf.py   SDF <-> CSV converters
|   +-- cdx_to_sdf.py, cdx_to_csv.py   CDX/CDXML -> SDF/CSV converters
|   +-- CHANGELOG.md             Release notes
|   +-- requirements.txt         Python dependencies
|   +-- build.spec               PyInstaller spec (console CLI exe)
|   +-- sdf_csv_converter_gui.spec   PyInstaller spec (windowed GUI exe)
|   +-- hooks/hook-rdkit.py      PyInstaller hook for RDKit DLLs
|   +-- dist/                    Legacy separate exes (~117 MB each)
|   +-- README.md
+-- standalone/                  Combined single-file exe build (recommended)
|   +-- app_entry.py             Dual-mode launcher (GUI / CLI)
|   +-- win_console.py           Console attach + UTF-8 for CLI mode
|   +-- standalone.spec          PyInstaller onefile spec (icon, splash, version)
|   +-- build_standalone.py      One-command builder
|   +-- ARCHITECTURE.md          Standalone packaging architecture
|   +-- README.md                Build and run instructions
|   +-- assets/                  app.ico, splash.png
|   +-- dist/Convertia.exe       Combined app (~66 MB)
+-- tests/                       Unit + integration tests (python -m unittest discover tests)
|   +-- fixtures/                Synthetic CDXML fixtures (OMe, Ph, Boc, R-groups)
+-- ACKNOWLEDGEMENTS.md          Credits (RDKit, CDK/JPLogP, Open Babel, ChemDraw format)
+-- LICENSE                      MIT license (project source code)
+-- THIRD_PARTY_NOTICES.md       Bundled dependency licenses and redistribution guidance
```

---

## License & acknowledgements

| Document | Scope |
|----------|--------|
| **[`LICENSE`](../LICENSE)** | MIT — original code in this package (`cdx_parser`, converters, GUI, etc.) |
| **[`clogp.py`](clogp.py) / [`jplogp_weights.py`](jplogp_weights.py)** | LGPL v2.1+ — JPLogP port adapted from [CDK](https://github.com/cdk/cdk) / Lhasa Limited ([Plante & Werner, 2018](https://doi.org/10.1186/s13321-018-0316-5)) |
| **[`ACKNOWLEDGEMENTS.md`](../ACKNOWLEDGEMENTS.md)** | Full credits (RDKit, Open Babel, Python, ChemDraw CDXML format) |
| **[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)** | What applies when you **redistribute** `Convertia.exe` (BSD + LGPL + possible GPL) |

Pre-built executables bundle third-party libraries (RDKit, OpenBabel, Python,
etc.) under their own terms. Read **`THIRD_PARTY_NOTICES.md`** before sharing
binaries — especially if OpenBabel (GPL v2) is included in the build.
