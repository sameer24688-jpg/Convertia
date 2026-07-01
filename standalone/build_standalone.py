"""
One-command builder for the Convertia standalone executable.

Usage (from the standalone/ folder):
    python build_standalone.py              # onefile (default)
    python build_standalone.py --onedir   # folder build (best for sharing)
    python build_standalone.py --zip      # also create dist/Convertia.zip

Set CONVERTIA_PYTHON to force a specific Python interpreter for the build.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
NA_ROOT = os.path.dirname(HERE)
PKG_DIR = os.path.join(NA_ROOT, "sdf_csv_converter")
DIST_DIR = os.path.join(HERE, "dist")
BUILD_DIR = os.path.join(HERE, "build")
ONEFILE_SPEC = os.path.join(HERE, "standalone.spec")
ONEDIR_SPEC = os.path.join(HERE, "standalone_onedir.spec")
STAMP_NAME = "SOURCE_STAMP.txt"


def _is_store_python(exe: str) -> bool:
    lowered = exe.replace("/", "\\").lower()
    return "windowsapps" in lowered or "pythonsoftwarefoundation" in lowered


def _python_has_build_deps(exe: str) -> bool:
    if not os.path.isfile(exe):
        return False
    probe = (
        "import importlib.util; "
        "mods=('rdkit','PyInstaller'); "
        "missing=[m for m in mods if importlib.util.find_spec(m) is None]; "
        "import sys; "
        "print('ok' if not missing else 'missing:' + ','.join(missing)); "
        "sys.exit(0 if not missing else 1)"
    )
    result = subprocess.run([exe, "-c", probe], capture_output=True, text=True)
    return result.returncode == 0


def _candidate_pythons() -> list[str]:
    env = os.environ.get("CONVERTIA_PYTHON")
    if env:
        return [env]

    found: list[str] = []
    py_launcher = shutil.which("py")
    if py_launcher:
        result = subprocess.run(
            [py_launcher, "-0p"],
            capture_output=True,
            text=True,
            check=False,
        )
        for line in result.stdout.splitlines():
            if "python.exe" in line.lower():
                path = line.rsplit(" ", 1)[-1].strip()
                if path and path not in found:
                    found.append(path)

    for path in (
        sys.executable,
        r"C:\Program Files\Python312\python.exe",
        r"C:\Program Files\Python311\python.exe",
        r"C:\Program Files\Python310\python.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python312\python.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python311\python.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python310\python.exe"),
    ):
        if path and path not in found:
            found.append(path)
    return found


def _select_python() -> str:
    good: list[str] = []
    store: list[str] = []
    for exe in _candidate_pythons():
        if not _python_has_build_deps(exe):
            continue
        if _is_store_python(exe):
            store.append(exe)
        else:
            good.append(exe)
    if good:
        return good[0]
    if store:
        print(
            "WARNING: Only Microsoft Store Python with build deps was found.\n"
            "         Exes built this way may fail on other PCs.\n"
            "         Prefer python.org Python: https://www.python.org/downloads/\n"
            f"         Using: {store[0]}\n"
        )
        return store[0]
    raise SystemExit(
        "No Python with rdkit + PyInstaller found.\n"
        "Install from python.org, then:\n"
        "  pip install pyinstaller pillow openbabel-wheel rdkit"
    )


def _ensure_assets(python_exe: str) -> None:
    source = os.path.join(NA_ROOT, "Convertia.png")
    ico = os.path.join(HERE, "assets", "app.ico")
    if os.path.isfile(source) and (
        not os.path.isfile(ico)
        or os.path.getmtime(source) > os.path.getmtime(ico)
    ):
        print("Regenerating assets from Convertia.png ...")
        subprocess.run(
            [python_exe, os.path.join(HERE, "generate_assets.py")],
            check=True,
        )


def _clean(*, dist: bool = True) -> None:
    paths = [BUILD_DIR]
    if dist:
        paths.extend((DIST_DIR, os.path.join(HERE, "Convertia")))
    for path in paths:
        if os.path.isdir(path):
            print(f"Removing {path}")
            shutil.rmtree(path, ignore_errors=True)


def _copy_popup_image() -> None:
    popup_src = os.path.join(HERE, "assets", "image.png")
    if not os.path.isfile(popup_src):
        return
    for folder in (
        DIST_DIR,
        os.path.join(DIST_DIR, "Convertia"),
    ):
        if os.path.isdir(folder):
            dst = os.path.join(folder, "image.png")
            shutil.copy2(popup_src, dst)
            print(f"  Popup image: {dst}")


def _write_readme(exe_path: str) -> None:
    readme = os.path.join(os.path.dirname(exe_path), "README.txt")
    size = os.path.getsize(exe_path)
    with open(readme, "w", encoding="utf-8") as fh:
        fh.write(
            "Convertia — chemical format conversion suite\n"
            "============================================\n\n"
            f"Executable size: {size:,} bytes\n\n"
            "Quick test (Command Prompt):\n"
            "  Convertia.exe --version\n\n"
            "GUI: double-click Convertia.exe\n"
            "CLI: Convertia.exe input.cdxml -o output.csv\n\n"
            "CSV columns (CDXML/CDX):\n"
            "  XmlIndex, Title, CompoundID, Annotations,\n"
            "  SMILES, MolecularWeight, Formula, CLogP, TPSA,\n"
            "  NumHAcceptors, NumHDonors, NumRotatableBonds, NumHeavyAtoms,\n"
            "  NumStereoCenters\n\n"
            "CLogP is computed with JPLogP (atom-contribution lipophilicity),\n"
            "not RDKit Wildman-Crippen logP. ChemDraw file values, if any,\n"
            "appear as ChemDraw_CLogP.\n\n"
            "Licenses: MIT project code; JPLogP (LGPL); bundled exe also uses\n"
            "RDKit (BSD) and may include OpenBabel (GPL). See GitHub repo\n"
            "THIRD_PARTY_NOTICES.md and ACKNOWLEDGEMENTS.md.\n\n"
            "If Windows blocks the app:\n"
            "  1. Right-click Convertia.exe -> Properties -> Unblock (if shown)\n"
            "  2. Or click 'More info' on SmartScreen, then 'Run anyway'\n\n"
            "If startup fails, open convertia_error.log in this folder.\n"
        )
    print(f"  Readme:      {readme}")


def _zip_distribution() -> str:
    archive = os.path.join(DIST_DIR, "Convertia.zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(DIST_DIR):
            for name in files:
                if name == "Convertia.zip":
                    continue
                path = os.path.join(root, name)
                zf.write(path, os.path.relpath(path, DIST_DIR))
    print(f"  Zip package: {archive}")
    return archive


def _package_source_manifest() -> tuple[str, dict[str, str]]:
    """Return (package version, relative_path -> sha256) for sdf_csv_converter sources."""
    version = "unknown"
    init_py = os.path.join(PKG_DIR, "__init__.py")
    if os.path.isfile(init_py):
        with open(init_py, encoding="utf-8") as fh:
            for line in fh:
                if line.strip().startswith("__version__"):
                    version = line.split("=", 1)[1].strip().strip("\"'")
                    break

    manifest: dict[str, str] = {}
    for root, _dirs, files in os.walk(PKG_DIR):
        if "dist" in root.split(os.sep) or "__pycache__" in root:
            continue
        for name in sorted(files):
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, NA_ROOT).replace("\\", "/")
            digest = hashlib.sha256()
            with open(path, "rb") as fh:
                for chunk in iter(lambda: fh.read(65536), b""):
                    digest.update(chunk)
            manifest[rel] = digest.hexdigest()
    return version, manifest


def _format_source_stamp(version: str, manifest: dict[str, str]) -> str:
    built = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "Convertia source stamp",
        "======================",
        f"Package version: {version}",
        f"Built from:      {NA_ROOT}",
        f"Build time:      {built}",
        "",
        "sdf_csv_converter is the single source of truth.",
        "standalone/dist/* exes bundle this package at build time.",
        "After editing sdf_csv_converter, rebuild:",
        "  cd standalone && python build_standalone.py --both",
        "",
        "File SHA-256:",
    ]
    for rel, digest in sorted(manifest.items()):
        lines.append(f"  {digest}  {rel}")
    lines.append("")
    return "\n".join(lines)


def _write_source_stamp(version: str, manifest: dict[str, str]) -> None:
    text = _format_source_stamp(version, manifest)
    for folder in (
        DIST_DIR,
        os.path.join(DIST_DIR, "Convertia"),
    ):
        if os.path.isdir(folder):
            path = os.path.join(folder, STAMP_NAME)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            print(f"  Source stamp: {path}")


def _write_launcher_bats() -> None:
    """Copy Windows launchers beside each distribution exe."""
    pkg_bat = os.path.join(PKG_DIR, "Convertia.bat")
    if os.path.isfile(pkg_bat):
        dst = os.path.join(DIST_DIR, "Convertia.bat")
        shutil.copy2(pkg_bat, dst)
        print(f"  Launcher:    {dst}")

    onedir = os.path.join(DIST_DIR, "Convertia")
    if os.path.isdir(onedir):
        bat = os.path.join(onedir, "Convertia.bat")
        with open(bat, "w", encoding="utf-8", newline="\r\n") as fh:
            fh.write(
                "@echo off\r\n"
                "setlocal\r\n"
                'cd /d "%~dp0"\r\n'
                'if "%~1"=="" (\r\n'
                '  start "" "%~dp0Convertia.exe"\r\n'
                ") else (\r\n"
                '  "%~dp0Convertia.exe" %*\r\n'
                "  if errorlevel 1 pause\r\n"
                ")\r\n"
            )
        print(f"  Launcher:    {bat}")


def build(*, onedir: bool, make_zip: bool, both: bool = False) -> int:
    python_exe = _select_python()
    print(f"Build Python: {python_exe}")
    _ensure_assets(python_exe)
    _clean(dist=True)

    targets: list[tuple[str, bool]] = []
    if both:
        targets = [(ONEDIR_SPEC, True), (ONEFILE_SPEC, False)]
    else:
        targets = [(ONEDIR_SPEC if onedir else ONEFILE_SPEC, onedir)]

    last_exe = ""
    for spec, is_onedir in targets:
        cmd = [python_exe, "-m", "PyInstaller", "--noconfirm", "--clean", spec]
        print("Running:", " ".join(cmd))
        result = subprocess.run(cmd, cwd=HERE)
        if result.returncode != 0:
            print(f"\nBuild FAILED (PyInstaller exit {result.returncode}).")
            return result.returncode
        _clean(dist=False)

        if is_onedir:
            last_exe = os.path.join(DIST_DIR, "Convertia", "Convertia.exe")
        else:
            last_exe = os.path.join(DIST_DIR, "Convertia.exe")

        if not os.path.isfile(last_exe):
            print(f"\nBuild reported success but exe not found at {last_exe}.")
            return 1

    _copy_popup_image()
    version, manifest = _package_source_manifest()
    _write_source_stamp(version, manifest)
    _write_launcher_bats()
    for exe_candidate in (
        os.path.join(DIST_DIR, "Convertia.exe"),
        os.path.join(DIST_DIR, "Convertia", "Convertia.exe"),
    ):
        if os.path.isfile(exe_candidate):
            _write_readme(exe_candidate)

    size_mb = os.path.getsize(last_exe) / (1024 * 1024)
    print("\n" + "=" * 60)
    print("  Build complete")
    if both:
        print(f"  Onefile:    {os.path.join(DIST_DIR, 'Convertia.exe')}")
        print(f"  Onedir:     {os.path.join(DIST_DIR, 'Convertia', 'Convertia.exe')}")
    else:
        print(f"  Executable: {last_exe}")
    print(f"  Size:       {size_mb:.1f} MB (last target)")
    print("=" * 60)
    print("  Share dist/Convertia.exe, dist/Convertia/, or Convertia.zip.")
    print("  Recipients: 64-bit Windows 10/11.")
    if make_zip:
        _zip_distribution()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Convertia standalone exe")
    parser.add_argument(
        "--onedir",
        action="store_true",
        help="Build a folder distribution (more reliable on locked-down PCs)",
    )
    parser.add_argument(
        "--both",
        action="store_true",
        help="Build onefile (dist/Convertia.exe) and onedir (dist/Convertia/) in one run",
    )
    parser.add_argument(
        "--zip",
        action="store_true",
        help="Create dist/Convertia.zip after building",
    )
    args = parser.parse_args()
    if args.both and args.onedir:
        parser.error("Use either --onedir or --both, not both flags together.")
    return build(onedir=args.onedir, make_zip=args.zip, both=args.both)


if __name__ == "__main__":
    raise SystemExit(main())
