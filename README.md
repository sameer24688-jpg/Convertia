# Convertia

![Convertia](Convertia.png)

**ChemDraw plate → analysis-ready table.** Convertia batch-converts **CDXML, CDX, SDF, and CSV** into CSV or SDF with structures, descriptors, and ChemDraw metadata in one step.

One **dual-mode Windows executable** (~66 MB): double-click for the GUI, or run from a terminal for scripting. No Python install required for end users.

Powered by **RDKit** (structures and descriptors), **JPLogP** (computed `CLogP` lipophilicity), and ChemDraw-aware parsing (nickname expansion, `chemicalproperty` titles, coordinate-based labels).

---

## Why Convertia?

Most converters treat a ChemDraw export as “just another molecule file.” Convertia is built for **SAR plates and compound libraries** drawn in ChemDraw.

| Capability | Generic tools (Open Babel, simple SDF↔CSV scripts) | Convertia |
|------------|---------------------------------------------------|-----------|
| **ChemDraw CDXML plates** | Often miss grouped structures, page text, and property links | Native CDXML parser; walks `<group>` fragments in document order |
| **Compound names (IUPAC captions)** | Usually lost | Read via ChemDraw `chemicalproperty` / `BasisObjects` → **`Title`** column |
| **Plate labels (IDs, notes)** | Not assigned per structure | **`CompoundID`** and **`Annotations`** via spatial proximity |
| **Abbreviations (OMe, Ph, Boc…)** | Often a single placeholder atom | Expanded from ChemDraw’s **embedded fragment** → correct formula & SMILES |
| **R-groups (R1, R2…)** | Inconsistent or dropped | Dummy atoms with map numbers (`[*:1]`) in SMILES |
| **Row order on dense plates** | Undefined or re-sorted | Monotonic **`XmlIndex`** (0…N−1) matches the drawing |
| **ChemDraw vs computed properties** | Can overwrite each other | Separate namespaces: **`ChemDraw_*`** vs RDKit columns (`CLogP`, `MolecularWeight`, …) |
| **Batch descriptors** | Requires a separate RDKit/KNIME workflow | Built-in: SMILES, MW, formula, CLogP, TPSA, HBD/HBA, rotatable bonds, stereo centers |
| **Distribution** | Install Python, RDKit, Open Babel, or KNIME | Single portable **`Convertia.exe`** (GUI + CLI) |

**Best fit:** you export a **CDXML plate** from ChemDraw and need one spreadsheet or SDF for Excel, Python, or registration — with **names, IDs, and chemistry** intact.

**Not a replacement for:** ChemDraw (2D layout, arrows, colors), enterprise compound registration (ChemAxon, etc.), or general-purpose format translation across dozens of file types. Convertia does **not** round-trip 2D drawings; it extracts **connectivity and data**. See [`sdf_csv_converter/README.md`](sdf_csv_converter/README.md#known-limitations) for details.

---

## Quick links

| Path | Description |
|------|-------------|
| [`standalone/`](standalone/) | **Recommended** — build the combined `Convertia.exe` (~66 MB) |
| [`sdf_csv_converter/`](sdf_csv_converter/) | Core Python package, full documentation, legacy dual-exe builds |
| [`tests/`](tests/) | Unit and integration tests (`python -m unittest discover tests`) |
| [`LICENSE`](LICENSE) | MIT license (project source code) |
| [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) | Bundled dependency licenses (read before redistributing binaries) |

## Quick start (developers)

```bash
pip install -r sdf_csv_converter/requirements.txt
python -m unittest discover tests
python -m sdf_csv_converter input.cdxml -o out.csv
```

## Quick start (end users)

Build or download `standalone/dist/Convertia.zip` (or `Convertia.exe` + `image.png`), then double-click for the GUI or run:

```bash
Convertia.exe input.cdxml -o output.csv
```

The GUI lets you pick **CSV** or **SDF** output before converting. See [`standalone/DISTRIBUTION.md`](standalone/DISTRIBUTION.md) for sharing with colleagues.

See [`standalone/README.md`](standalone/README.md) for build instructions.

## License

MIT — see [`LICENSE`](LICENSE). Executable builds bundle third-party libraries; see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
