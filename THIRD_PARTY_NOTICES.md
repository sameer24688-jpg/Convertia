# Third-party notices

This document explains **what licenses apply** when you use or redistribute
Convertia source code or pre-built executables.

> **Short answer:** Using Convertia yourself is straightforward. **Redistributing
> `Convertia.exe` to others** requires complying with several upstream licenses
> (BSD, LGPL, and possibly GPL). The project’s own code is MIT, but the bundled
> binary is a **combined work**. See [Redistribution safety](#redistribution-safety)
> below.

---

## Project license (original code)

This repository’s **original source code** is licensed under the
[MIT License](LICENSE) (see [`LICENSE`](LICENSE)).

**Exception — JPLogP port:** [`sdf_csv_converter/clogp.py`](sdf_csv_converter/clogp.py)
and [`sdf_csv_converter/jplogp_weights.py`](sdf_csv_converter/jplogp_weights.py) are
**adapted from CDK** (JPLogP) and are licensed under the
[GNU Lesser General Public License v2.1 or later](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html).
They are marked in file headers. When you redistribute those files or binaries that
embed them, LGPL terms apply to that portion (source availability, license notice,
and modification notices).

---

## Runtime dependencies (bundled in `.exe` builds)

| Component | Role | License | Notes |
|-----------|------|---------|-------|
| [Python](https://www.python.org/) | Language runtime (embedded by PyInstaller) | [PSF License](https://docs.python.org/3/license.html) | Bundled in standalone and legacy exes |
| [RDKit](https://www.rdkit.org/) | Cheminformatics (structures, descriptors, SMILES) | [BSD 3-Clause](https://github.com/rdkit/rdkit/blob/master/license.txt) | Required; retain copyright notice |
| [CDK JPLogP](https://github.com/cdk/cdk) (ported) | `CLogP` via JPLogP atom-contribution model | [LGPL v2.1+](https://github.com/cdk/cdk/blob/main/LICENSE) | See [`clogp.py`](sdf_csv_converter/clogp.py), [`jplogp_weights.py`](sdf_csv_converter/jplogp_weights.py) |
| [OpenBabel](https://openbabel.org/) | CDX binary → structure conversion | [GPL v2](https://github.com/openbabel/openbabel/blob/master/COPYING) | Optional at runtime for `.cdx`; **bundled in exes** if the build collected it |
| [tqdm](https://github.com/tqdm/tqdm) | Progress bars | [MPL 2.0 / MIT](https://github.com/tqdm/tqdm/blob/master/LICENCE) | Bundled in exes |

## Build-time only (not shipped in the app logic)

| Component | Role | License |
|-----------|------|---------|
| [PyInstaller](https://pyinstaller.org/) | Creates standalone executables | [GPL v2 with exception](https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt) |
| [Pillow](https://python-pillow.org/) | Icon/splash asset processing during standalone build | [HPND / PIL license](https://github.com/python-pillow/Pillow/blob/main/LICENSE) |

## Parser and CDXML handling (this repository)

CDXML parsing, nickname expansion, coordinate-based text assignment, and CSV/SDF
output are implemented in [`sdf_csv_converter/`](sdf_csv_converter/) and are
**MIT-licensed** project code (except the JPLogP files noted above). Abbreviation
expansion uses only data embedded in ChemDraw files — no third-party CDXML parser
source is incorporated.

---

## Redistribution safety

This is **not legal advice**. For production or commercial redistribution, confirm
with your organization’s counsel. The following is a practical engineering summary.

### Using Convertia yourself (internal R&D, no redistribution)

| Scenario | Typical risk |
|----------|----------------|
| Run `python -m sdf_csv_converter` on your machine | **Low** — comply with upstream terms for installed packages |
| Double-click `Convertia.exe` locally | **Low** — same as above |
| Publish results (CSVs/SDFs) you generated | **Low** — output data is yours; no license “infects” your data |

### Sharing the source repository (GitHub)

| Scenario | Typical risk |
|----------|----------------|
| Clone / fork / share this GitHub repo | **Low** — MIT + LGPL (JPLogP files) + notices are already included |
| MIT allows commercial use of **project code**; LGPL requires preserving JPLogP file notices and source |

### Redistributing `Convertia.exe` to colleagues or customers

| Bundled component | Obligation (summary) |
|-------------------|----------------------|
| **MIT project code** | Include MIT copyright and permission notice |
| **RDKit (BSD)** | Retain RDKit copyright and license notice |
| **JPLogP port (LGPL)** | Provide LGPL text; provide corresponding source for `clogp.py` / `jplogp_weights.py` (this public repo satisfies that); state changes (Java→Python port) |
| **OpenBabel (GPL v2)** — if included in build | **Strongest copyleft:** combined executable may be treated as a GPL work; offer complete corresponding source for GPL-covered parts (OpenBabel + possibly entire bundle per GPL interpretation) |
| **Python (PSF)** | Standard embedded-Python attribution |

**Safest binary redistribution practices for this project:**

1. Ship **`Convertia.zip`** with `README.txt`, [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md), and a link to this **source repository**.
2. Include [`ACKNOWLEDGEMENTS.md`](ACKNOWLEDGEMENTS.md) or its summary in the zip.
3. If you need **minimal copyleft exposure**, build without OpenBabel installed and document that **`.cdx` binary input is unsupported** in that build (CDXML still works).
4. Do **not** claim the executable is “MIT-only” — it is a **multi-license bundle**.

### What is *not* claimed

- Convertia does **not** include or redistribute **BioByte / ACD CLogP** (proprietary).
- Convertia is **not** affiliated with ChemDraw / Revvity.
- Computed **`CLogP`** is **JPLogP** (open literature + CDK/LGPL), not ChemDraw’s commercial CLogP.

---

## OpenBabel and redistribution

If you distribute a PyInstaller-built executable that includes OpenBabel (the
default build collects it when installed), **GPL v2 obligations apply to that
binary as a whole**, including providing corresponding source or an offer for
source for the GPL-covered portions, in addition to retaining notices for MIT,
BSD, and LGPL components.

If you need a **reduced-copyleft** redistribution story for binaries:

- Omit OpenBabel from the build environment and document that **CDX binary**
  input is unsupported in that build, **or**
- Ship source and comply with GPL v2 for the combined executable.

---

## Upstream license texts

Full license texts are maintained by each upstream project. When in doubt, refer
to the version of each package installed in your build environment and its
packaged `LICENSE` / `COPYING` file.

See also [`ACKNOWLEDGEMENTS.md`](ACKNOWLEDGEMENTS.md) for citations and credits.
