"""
One-command builder for the combined single-file sdf_csv_converter executable.

Usage (from the standalone/ folder):
    python build_standalone.py

Cleans previous build artifacts, runs PyInstaller on standalone.spec, and prints
the resulting exe path and size. Requires: pip install pyinstaller pillow.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "standalone.spec")
BUILD_DIR = os.path.join(HERE, "build")
DIST_DIR = os.path.join(HERE, "dist")
EXE_PATH = os.path.join(DIST_DIR, "sdf_csv_converter.exe")


def _clean() -> None:
    for path in (BUILD_DIR, DIST_DIR):
        if os.path.isdir(path):
            print(f"Removing {path}")
            shutil.rmtree(path, ignore_errors=True)


def main() -> int:
    _clean()

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        SPEC,
    ]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=HERE)
    if result.returncode != 0:
        print(f"\nBuild FAILED (PyInstaller exit {result.returncode}).")
        return result.returncode

    if not os.path.isfile(EXE_PATH):
        print(f"\nBuild reported success but exe not found at {EXE_PATH}.")
        return 1

    size_mb = os.path.getsize(EXE_PATH) / (1024 * 1024)
    print("\n" + "=" * 60)
    print("  Build complete")
    print(f"  Executable: {EXE_PATH}")
    print(f"  Size:       {size_mb:.1f} MB")
    print("=" * 60)
    print("  Double-click   -> GUI")
    print("  With arguments -> CLI, e.g.:")
    print("    sdf_csv_converter.exe input.cdxml -o output.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
