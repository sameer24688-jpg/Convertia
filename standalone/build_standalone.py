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
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
NA_ROOT = os.path.dirname(HERE)
DIST_DIR = os.path.join(HERE, "dist")
BUILD_DIR = os.path.join(HERE, "build")
ONEFILE_SPEC = os.path.join(HERE, "standalone.spec")
ONEDIR_SPEC = os.path.join(HERE, "standalone_onedir.spec")


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


def _clean() -> None:
    for path in (BUILD_DIR, DIST_DIR):
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


def build(*, onedir: bool, make_zip: bool) -> int:
    python_exe = _select_python()
    print(f"Build Python: {python_exe}")
    _ensure_assets(python_exe)
    _clean()

    spec = ONEDIR_SPEC if onedir else ONEFILE_SPEC
    cmd = [python_exe, "-m", "PyInstaller", "--noconfirm", "--clean", spec]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=HERE)
    if result.returncode != 0:
        print(f"\nBuild FAILED (PyInstaller exit {result.returncode}).")
        return result.returncode

    if onedir:
        exe_path = os.path.join(DIST_DIR, "Convertia", "Convertia.exe")
    else:
        exe_path = os.path.join(DIST_DIR, "Convertia.exe")

    if not os.path.isfile(exe_path):
        print(f"\nBuild reported success but exe not found at {exe_path}.")
        return 1

    _copy_popup_image()
    _write_readme(exe_path)

    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print("\n" + "=" * 60)
    print("  Build complete")
    print(f"  Executable: {exe_path}")
    print(f"  Size:       {size_mb:.1f} MB")
    print("=" * 60)
    print("  Share the whole dist/ folder (or Convertia.zip).")
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
        "--zip",
        action="store_true",
        help="Create dist/Convertia.zip after building",
    )
    args = parser.parse_args()
    return build(onedir=args.onedir, make_zip=args.zip)


if __name__ == "__main__":
    raise SystemExit(main())
