"""
Verify standalone/dist was built from the current sdf_csv_converter source.

Usage (from standalone/):
    python check_source_sync.py

Exit 0 if dist SOURCE_STAMP.txt matches current package hashes; exit 1 if stale or missing.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NA_ROOT = os.path.dirname(HERE)
PKG_DIR = os.path.join(NA_ROOT, "sdf_csv_converter")
STAMP_NAME = "SOURCE_STAMP.txt"
STAMP_CANDIDATES = (
    os.path.join(HERE, "dist", STAMP_NAME),
    os.path.join(HERE, "dist", "Convertia", STAMP_NAME),
)


def _current_manifest() -> dict[str, str]:
    from build_standalone import _package_source_manifest

    _version, manifest = _package_source_manifest()
    return manifest


def _read_stamp_manifest(path: str) -> dict[str, str]:
    manifest: dict[str, str] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            m = re.match(r"^  ([0-9a-f]{64})  (.+)$", line)
            if m:
                manifest[m.group(2)] = m.group(1)
    return manifest


def main() -> int:
    stamp_path = next((p for p in STAMP_CANDIDATES if os.path.isfile(p)), "")
    if not stamp_path:
        print("No SOURCE_STAMP.txt in standalone/dist — rebuild required:")
        print("  cd standalone && python build_standalone.py --both")
        return 1

    built = _read_stamp_manifest(stamp_path)
    current = _current_manifest()

    if not built:
        print(f"Stamp file is empty or unreadable: {stamp_path}")
        return 1

    missing = sorted(set(current) - set(built))
    extra = sorted(set(built) - set(current))
    changed = sorted(
        rel for rel in current if rel in built and built[rel] != current[rel]
    )

    if not missing and not extra and not changed:
        print("OK — standalone/dist matches sdf_csv_converter source.")
        print(f"Stamp: {stamp_path}")
        return 0

    print("OUT OF SYNC — sdf_csv_converter changed since last dist build.")
    print(f"Stamp: {stamp_path}")
    if changed:
        print("\nModified since build:")
        for rel in changed:
            print(f"  {rel}")
    if missing:
        print("\nNew files (not in build):")
        for rel in missing:
            print(f"  {rel}")
    if extra:
        print("\nRemoved from source (still in stamp):")
        for rel in extra:
            print(f"  {rel}")
    print("\nRebuild to sync:")
    print("  cd standalone && python build_standalone.py --both")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
