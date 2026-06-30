# Acknowledgements

Convertia / `sdf_csv_converter` builds on open cheminformatics libraries, published
algorithms, and community tooling. We are grateful to the authors and maintainers
listed below.

This project is maintained as a **free public tool**, not a commercial product.
It is our way of passing forward the benefit we received from open science and
open-source cheminformatics.

## Cheminformatics runtimes

| Project | Role in Convertia | License |
|---------|-------------------|---------|
| [RDKit](https://www.rdkit.org/) | Structure parsing, SMILES, descriptors (MW, TPSA, HBD/HBA, stereo centers, etc.) | [BSD 3-Clause](https://github.com/rdkit/rdkit/blob/master/license.txt) |
| [Open Babel](https://openbabel.org/) | Optional CDX binary → structure conversion (when installed / bundled) | [GPL v2](https://github.com/openbabel/openbabel/blob/master/COPYING) |
| [Python](https://www.python.org/) | Language runtime (embedded in PyInstaller builds) | [PSF License](https://docs.python.org/3/license.html) |

## JPLogP / CLogP (adapted from CDK)

The **`CLogP`** column uses **JPLogP**, an atom-contribution lipophilicity model
donated by **Lhasa Limited** and distributed with the
[Chemistry Development Kit (CDK)](https://github.com/cdk/cdk).

| Item | Detail |
|------|--------|
| **Source files (this repo)** | [`sdf_csv_converter/clogp.py`](sdf_csv_converter/clogp.py), [`sdf_csv_converter/jplogp_weights.py`](sdf_csv_converter/jplogp_weights.py) |
| **Upstream** | `org.openscience.cdk.qsar.descriptors.molecular.JPlogPDescriptor` (CDK) |
| **License** | [GNU LGPL v2.1+](https://github.com/cdk/cdk/blob/main/LICENSE) (adapted / ported to Python) |
| **Publication** | Plante, J.; Werner, S. *J. Cheminform.* **2018**, *10*, 61. [doi:10.1186/s13321-018-0316-5](https://doi.org/10.1186/s13321-018-0316-5) |

JPLogP is **not** BioByte/ACD CLogP (proprietary) and **not** RDKit Wildman–Crippen
`MolLogP`. ChemDraw-stored CLogP values, when present, appear as **`ChemDraw_CLogP`**
in output.

## Other bundled / build dependencies

| Project | Role | License |
|---------|------|---------|
| [tqdm](https://github.com/tqdm/tqdm) | Progress output | [MPL 2.0 / MIT](https://github.com/tqdm/tqdm/blob/master/LICENCE) |
| [PyInstaller](https://pyinstaller.org/) | Standalone `.exe` packaging | [GPL v2 + exception](https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt) |
| [Pillow](https://python-pillow.org/) | Icon / splash asset generation (build time) | [HPND](https://github.com/python-pillow/Pillow/blob/main/LICENSE) |

## ChemDraw and CDXML

Convertia reads **CDXML** and **CDX** files exported from
[ChemDraw](https://www.revvity.com/products/software/chemdraw) (PerkinElmer / Revvity).
ChemDraw is a trademark of its respective owners. This project is **not** affiliated
with, endorsed by, or sponsored by Revvity. The native CDXML parser in
`sdf_csv_converter/cdx_parser.py` is **original MIT-licensed code** in this
repository; it interprets file formats and embedded ChemDraw data — it does not
ship ChemDraw software or proprietary BioByte calculators.

## Convertia project code

Original parsing, conversion pipeline, GUI, and standalone launcher code in this
repository (excluding the JPLogP port above) is **MIT-licensed** — see
[`LICENSE`](LICENSE).

For redistribution obligations when shipping binaries, see
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
