# Convertia

![Convertia](Convertia.png)

Standalone Windows utility for **CDXML, CDX, SDF, and CSV** chemical file
conversions. Packaged as a **single dual-mode executable** — double-click for
the GUI, or run from a terminal with arguments for the CLI.

Powered by **RDKit** (structures and descriptors) with coordinate-based page-text
assignment for ChemDraw exports.

## Quick links

| Path | Description |
|------|-------------|
| [`standalone/`](standalone/) | **Recommended** — build the combined `Convertia.exe` (~66 MB) |
| [`sdf_csv_converter/`](sdf_csv_converter/) | Core Python package, legacy dual-exe builds, full documentation |
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

Build or download `standalone/dist/Convertia.exe` (with `image.png` beside it for the launch popup), then double-click for
the GUI or run:

```bash
Convertia.exe input.cdxml -o output.csv
```

See [`standalone/README.md`](standalone/README.md) for build instructions.

## License

MIT — see [`LICENSE`](LICENSE). Executable builds bundle third-party libraries;
see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
