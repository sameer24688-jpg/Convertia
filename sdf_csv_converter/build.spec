# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for sdf_csv_converter.
Builds a single-file .exe with RDKit, OpenBabel, and tqdm bundled.

Troubleshooting:
- RDKit DLLs: --collect-all rdkit handles most, hook-rdkit.py covers the rest
- OpenBabel DLLs: --collect-all openbabel handles .dll and .obf plugin files
- If build fails with missing DLL, check that pip install openbabel succeeded
"""
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

# Collect RDKit files
rdkit_datas, rdkit_binaries, rdkit_hiddenimports = collect_all("rdkit")

# Collect OpenBabel files
try:
    ob_datas, ob_binaries, ob_hiddenimports = collect_all("openbabel")
except Exception:
    ob_datas, ob_binaries, ob_hiddenimports = [], [], []

# Collect tqdm
try:
    tqdm_datas, tqdm_binaries, tqdm_hiddenimports = collect_all("tqdm")
except Exception:
    tqdm_datas, tqdm_binaries, tqdm_hiddenimports = [], [], []

# Merge
all_datas = rdkit_datas + ob_datas + tqdm_datas
all_binaries = rdkit_binaries + ob_binaries + tqdm_binaries
all_hiddenimports = (
    rdkit_hiddenimports
    + ob_hiddenimports
    + tqdm_hiddenimports
    + [
        "rdkit.Chem",
        "rdkit.Chem.AllChem",
        "rdkit.Chem.Descriptors",
        "rdkit.Chem.Crippen",
        "rdkit.Chem.Lipinski",
        "rdkit.Chem.rdMolDescriptors",
        "rdkit.Chem.rdmolops",
        "rdkit.RDLogger",
        "openbabel",
        "openbabel.openbabel",
        "tqdm",
    ]
)

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
    hookspath=["hooks"],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
        "pandas",
        "IPython",
        "jupyter",
        "PyQt6",
        "zmq",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="sdf_csv_converter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)