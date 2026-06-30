# Third-party notices

This project’s **original source code** is licensed under the [MIT License](LICENSE)
(see [`LICENSE`](LICENSE)).

Pre-built executables and installs that bundle dependencies are **not** MIT-only:
they also include third-party libraries listed below. You must comply with each
component’s license when you redistribute those binaries.

## Runtime dependencies (bundled in `.exe` builds)

| Component | Role | License | Notes |
|-----------|------|---------|-------|
| [Python](https://www.python.org/) | Language runtime (embedded by PyInstaller) | [PSF License](https://docs.python.org/3/license.html) | Bundled in standalone and legacy exes |
| [RDKit](https://www.rdkit.org/) | Cheminformatics (structures, descriptors, SMILES) | [BSD 3-Clause](https://github.com/rdkit/rdkit/blob/master/license.txt) | Required |
| [OpenBabel](https://openbabel.org/) | CDX binary → CDXML conversion | [GPL v2](https://github.com/openbabel/openbabel/blob/master/COPYING) | Optional at runtime for `.cdx`; **bundled in exes** if the build collected it |
| [tqdm](https://github.com/tqdm/tqdm) | Progress bars | [MPL 2.0 / MIT](https://github.com/tqdm/tqdm/blob/master/LICENCE) | Bundled in exes |

## Build-time only (not shipped in the app logic)

| Component | Role | License |
|-----------|------|---------|
| [PyInstaller](https://pyinstaller.org/) | Creates standalone executables | [GPL v2 with exception](https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt) |
| [Pillow](https://python-pillow.org/) | Icon/splash asset processing during standalone build | [HPND / PIL license](https://github.com/python-pillow/Pillow/blob/main/LICENSE) |

## Parser and CDXML handling (this repository)

CDXML parsing, nickname expansion, coordinate-based text assignment, and CSV/SDF
output are implemented in [`sdf_csv_converter/`](sdf_csv_converter/) and are
**MIT-licensed** project code. Abbreviation expansion uses only data
embedded in ChemDraw files — no third-party CDXML parser source is incorporated.

## OpenBabel and redistribution

If you distribute a PyInstaller-built executable that includes OpenBabel (the
default build collects it when installed), **GPL v2 obligations apply to that
binary as a whole**, including providing corresponding source or an offer for
source for the GPL-covered portions, in addition to retaining the MIT notice
for this project’s own code.

If you need a MIT-only redistribution story for binaries:

- Omit OpenBabel from the build environment and document that **CDX binary**
  input is unsupported in that build, **or**
- Ship source and comply with GPL v2 for the combined executable.

## Upstream license texts

Full license texts are maintained by each upstream project. When in doubt, refer
to the version of each package installed in your build environment and its
packaged `LICENSE` / `COPYING` file.
