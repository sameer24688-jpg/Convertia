# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for a **onedir** Convertia build (recommended for sharing).

Unlike the onefile build, this does not unpack to %TEMP% on every launch, which
avoids failures on PCs that block PyInstaller temp extraction.
"""
import os

from PyInstaller.utils.hooks import collect_all

HERE = SPECPATH
NA_ROOT = os.path.dirname(HERE)
PKG_HOOKS = os.path.join(NA_ROOT, "sdf_csv_converter", "hooks")

ICON = os.path.join(HERE, "assets", "app.ico")
VERSION_FILE = os.path.join(HERE, "version_info.txt")
ASSETS_DIR = os.path.join(HERE, "assets")

datas, binaries, hiddenimports = [], [], []
for asset_name in ("app.ico", "logo.png", "image.png"):
    asset_path = os.path.join(ASSETS_DIR, asset_name)
    if os.path.isfile(asset_path):
        datas.append((asset_path, "assets"))
for pkg in ("rdkit", "openbabel", "tqdm", "windnd"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

hiddenimports += [
    "win_console",
    "startup_errors",
    "sdf_csv_converter",
    "sdf_csv_converter.main",
    "sdf_csv_converter.cli",
    "sdf_csv_converter.gui",
    "sdf_csv_converter.sdf_to_csv",
    "sdf_csv_converter.csv_to_sdf",
    "sdf_csv_converter.cdx_to_sdf",
    "sdf_csv_converter.cdx_to_csv",
    "sdf_csv_converter.cdx_parser",
    "sdf_csv_converter.molecule_processor",
    "sdf_csv_converter.clogp",
    "sdf_csv_converter.jplogp_weights",
    "sdf_csv_converter.stream_utils",
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
    "tkinter",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "tkinter.ttk",
    "windnd",
]

a = Analysis(
    ["app_entry.py"],
    pathex=[NA_ROOT, HERE],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[PKG_HOOKS],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "scipy",
        "pandas",
        "IPython",
        "jupyter",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "zmq",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Convertia",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
    version=VERSION_FILE,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Convertia",
)
