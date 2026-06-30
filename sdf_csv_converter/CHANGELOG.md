# Changelog

## Unreleased

### Changed
- **Grouped CDXML structures.** ChemDraw often wraps each structure in a `<group>` under `<page>`. The parser now yields fragments inside page-level groups (in document order), not only direct `<page>` children — fixing plates like `test.cdxml` that previously exported a single row.
- **Slimmer CSV output.** Removed `AtomLabels`, `NumRings`, `FractionCSP3`, and `MaxRingSize` columns; dropped the corresponding RDKit calculators.
- **Simpler GUI.** Removed the Options panel; conversions use sensible defaults (SMILES column `SMILES`, 2D structures, computed properties on).
- **Compound names → Title column.** ChemDraw `chemicalproperty` links assign IUPAC captions to structures reliably (fixes missing/duplicate names on dense plates).
- **No console flash on GUI launch.** Standalone exe built with `console=False`; CLI still attaches or allocates a console via `ensure_console()`.
- **`NumStereoCenters` column.** RDKit `CalcNumAtomStereoCenters` is included in all CSV/SDF property output paths.
- **Renamed `logP` → `CLogP`.** ChemDraw-sourced values remain `ChemDraw_CLogP`.
- **Real CLogP calculation.** `CLogP` now uses JPLogP (atom-contribution, distinct from Wildman–Crippen logP); see `sdf_csv_converter/clogp.py` (LGPL, adapted from CDK).
- **Acknowledgements and licensing docs.** Added `ACKNOWLEDGEMENTS.md`; expanded `THIRD_PARTY_NOTICES.md` with JPLogP LGPL and redistribution guidance.

## 1.2.2 — GUI redesign and distribution hardening

### Added
- **Modern Convertia GUI** — card layout, teal **Convert** button, dark log panel, explicit **CSV / SDF** output format picker.
- **Startup error reporting** — `convertia_error.log` and message box on frozen exe launch failures (`standalone/startup_errors.py`).
- **Distribution package** — `python build_standalone.py --zip` produces `dist/Convertia.zip`; see `standalone/DISTRIBUTION.md`.
- **Onedir build** — `python build_standalone.py --onedir` for locked-down PCs.

### Changed
- GUI imports before console hide to avoid silent double-click failures.
- Launch popup image bundled inside exe (`assets/image.png`); external `dist/image.png` optional.
- Documentation updated for `Convertia.exe`, GUI features, and sharing workflow.

## 1.2.1 — Standalone redirect fix and documentation

### Fixed
- **Combined standalone exe CLI redirect.** `standalone/standalone.spec` uses `console=True` so `> file` and `2> log` work from a terminal. The GUI path hides the console window via `hide_console_window()` so double-click still feels like a desktop app.

### Changed
- Documentation across standalone and main README: conversion fidelity (coordinate-based page-text assignment, `Annotations`/`CompoundID`, `XmlIndex` document ordering) and a distribution/CLI-output comparison table for all build variants.
- Added [`LICENSE`](../LICENSE) (MIT) and [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) for source and binary redistribution compliance.

## 1.2.0 — Abbreviation and R-group expansion

### Added
- **Nickname / abbreviation expansion.** Atoms drawn as Me, OMe, Ph, Boc, ... expand into their real atoms using the expansion ChemDraw embeds in the file (a nested `<fragment>` whose `ExternalConnectionPoint` marks the attachment). The bond that pointed at the abbreviation is rewired onto the attachment atom, and the ECP is dropped, so `Formula`, `MolecularWeight`, and `SMILES` reflect the true structure. Nested nicknames expand recursively.
- **R-group support.** Labels `R`/`R1`/`R2` and `GenericNickname` nodes become RDKit dummy atoms (atomic number 0) carrying their atom-map number, surfaced in SMILES as `[*:1]`, `[*:2]`, ...
- Synthetic CDXML fixtures under `tests/fixtures/` and `tests/test_cdx_expansion.py`.

### Changed
- `_build_rdkit_mol` now consumes flattened atoms and normalized bond specs from `_flatten_fragment`, instead of raw `<b>` elements.

### Known limitations
- **Multi-attachment nicknames** (linkers/superatoms with 2+ `ExternalConnectionPoint`s) are not expanded; they fall back to a single collapsed atom.
- A bare abbreviation label with no embedded expansion fragment still falls back to `_label_to_atomic_num` (single carbon for unknown groups).

## 1.1.0 — CDXML fidelity and output correctness

### Fixed
- **Page text is assigned per-structure.** Page-level `<t>` elements (compound IDs, captions) are matched to the nearest fragment by CDXML coordinates instead of being duplicated onto every structure.
- **No more silent property overwrites.** ChemDraw `ChemProp*` values are emitted under a `ChemDraw_` prefix. Empty ChemDraw label templates are dropped. `MolecularWeight`, `Formula`, and computed lipophilicity (`CLogP` / JPLogP) are always the numeric RDKit-side values.

### Added
- **`XmlIndex` column** (plus internal `page_index`) on CDXML/CDX output.
- **`CompoundID` column** derived from code-like page labels (e.g. `PROJ-42`, `LAB-059`).
- Metadata-first CSV column ordering.
- Unit and integration tests under `tests/`.

### Changed
- Unified CDXML/CDX parsing into `_iter_page_structures`.
- Documentation for preserved vs. reconstructed data, row ordering, and property sources.
- `--workers` documented as a no-op for CDX/CDXML (single-threaded to preserve row order).
