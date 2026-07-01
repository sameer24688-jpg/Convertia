# Distributing Convertia

Convertia is shared **free of charge** for research and everyday cheminformatics
work — not for resale or proprietary repackaging. When you pass the zip to a
colleague, you are sharing a community tool built on open-source foundations.

This guide covers every common reason a shared `.exe` “does not work” on another
PC, and how to avoid each problem.

## What to send

| Package | Best for |
|---------|----------|
| **`dist/Convertia.zip`** (from `python build_standalone.py --zip`) | Easiest sharing |
| **`dist/Convertia.exe` + `dist/image.png`** | One-file install |
| **`dist/Convertia/` folder** (onedir build) | Locked-down PCs, IT environments |

Minimum recipient requirement: **64-bit Windows 10 or 11**. Not Mac/Linux.

Expected one-file size: **~66 MB** (`69,658,371` bytes — verify after transfer).

---

## Step-by-step: build for sharing

```bash
cd standalone
pip install pyinstaller pillow
python build_standalone.py --both --zip   # onefile + onedir + zip
```

Or build only one target:

```bash
python build_standalone.py              # onefile only → dist/Convertia.exe
python build_standalone.py --onedir     # folder only → dist/Convertia/
```

Send **`dist/Convertia.zip`**. Tell recipients to extract the whole folder and run
`Convertia.exe` from inside it.

Include (or link to) **[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)** and
**[`ACKNOWLEDGEMENTS.md`](../ACKNOWLEDGEMENTS.md)** when sharing binaries so recipients
understand bundled licenses (RDKit BSD, JPLogP LGPL, OpenBabel GPL if present).

### Use python.org Python for builds

Do **not** build with Microsoft Store Python if you can avoid it.

1. Install from [python.org](https://www.python.org/downloads/) (check **Add to PATH**).
2. Turn off Windows **App execution aliases** for `python.exe` / `python3.exe`.
3. `pip install rdkit openbabel-wheel pyinstaller pillow`
4. Set `CONVERTIA_PYTHON` to that interpreter, then build.

---

## Recipient troubleshooting

### 1. Windows SmartScreen / antivirus

**Symptoms:** Nothing happens, or “Windows protected your PC”.

**Fix:**
- Right-click `Convertia.exe` → **Properties** → check **Unblock** → Apply.
- On SmartScreen: **More info** → **Run anyway**.
- Confirm file size is still ~66 MB (not truncated by email).

### 2. Quick diagnostic

Open **Command Prompt** in the folder with the exe:

```bat
Convertia.exe --version
```

| Result | Meaning |
|--------|---------|
| Prints `sdf_csv_converter v1.2.1` | Exe runs; if GUI fails, see step 3 |
| SmartScreen / access denied | Blocked by Windows (step 1) |
| Instant exit, no output | Temp extraction blocked (step 4) or corrupt file |

### 3. GUI fails but `--version` works

Startup errors are written to **`convertia_error.log`** next to the exe and a
message box is shown (as of the reliability update).

Common causes:
- Missing Visual C++ runtime on very old Windows → install [VC++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)
- Antivirus quarantined a DLL during onefile unpack

### 4. One-file temp extraction blocked

PyInstaller onefile unpacks to `%TEMP%\_MEIxxxxx`. Some IT policies block this.

**Fix:** Use the **onedir** build (`python build_standalone.py --onedir --zip`) and
share the extracted `Convertia` folder instead of a single exe.

### 5. Slow first launch

First start can take **30–60 seconds**. Wait for the splash / popup / main window.

### 6. Missing `image.png`

The launch **popup** is optional. The converter runs without `image.png` beside
the exe because the image is also bundled inside the app. Include `image.png` only
if you want the external popup file easy to customize.

---

## Functionality checklist (receiver should get all of this)

| Feature | Exe alone | Notes |
|---------|-----------|-------|
| GUI | Yes | Double-click |
| CLI | Yes | `Convertia.exe input.cdxml -o out.csv` |
| SDF ↔ CSV | Yes | |
| CDXML → SDF/CSV | Yes | |
| CDX binary | Yes | OpenBabel bundled |
| Python install required | No | |

---

## Maintainer checklist before each release

1. Build with python.org Python when possible.
2. Run `python build_standalone.py --zip`.
3. Test in an isolated folder:
   ```bat
   mkdir %TEMP%\convertia_test
   copy dist\Convertia.exe %TEMP%\convertia_test\
   %TEMP%\convertia_test\Convertia.exe --version
   ```
4. Note exact byte size in release notes.
5. Optionally code-sign the exe (removes most SmartScreen warnings).
