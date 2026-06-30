# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the combined single-file sdf_csv_converter executable.

Produces one windowed onefile .exe that:
- opens the GUI when double-clicked, and
- runs the CLI when launched with arguments (see app_entry.py / win_console.py).

This spec does NOT modify the sdf_csv_converter package; it imports it from the
repository root and reuses its existing PyInstaller hook for RDKit DLLs.
"""
import os

from PyInstaller.utils.hooks import collect_all

# SPECPATH is injected by PyInstaller and points at this file's directory.
HERE = SPECPATH
NA_ROOT = os.path.dirname(HERE)
PKG_HOOKS = os.path.join(NA_ROOT, "sdf_csv_converter", "hooks")

ICON = os.path.join(HERE, "assets", "app.ico")
SPLASH_IMAGE = os.path.join(HERE, "assets", "splash.png")
VERSION_FILE = os.path.join(HERE, "version_info.txt")

# Collect heavy third-party packages (DLLs, data, hidden imports).
datas, binaries, hiddenimports = [], [], []
for pkg in ("rdkit", "openbabel", "tqdm"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

hiddenimports += [
    # Launcher + converter package modules.
    "win_console",
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
    "sdf_csv_converter.stream_utils",
    # RDKit submodules used at runtime.
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
    # GUI toolkit.
    "tkinter",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "tkinter.ttk",
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

splash = Splash(
    SPLASH_IMAGE,
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    splash.binaries,
    a.binaries,
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
    icon=ICON,
    version=VERSION_FILE,
)
