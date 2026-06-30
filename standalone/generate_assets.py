"""
Build standalone/assets from the Convertia logo at the repository root.

Usage (from standalone/):
    python generate_assets.py

Reads ../Convertia.png and writes:
  assets/app.ico    — multi-resolution Windows icon (taskbar, Explorer, GUI)
  assets/splash.png — PyInstaller splash during onefile unpack
  assets/logo.png   — compact header image for the Tk GUI
  assets/image.png  — launch popup (copied beside the exe in dist/ on build)
"""
from __future__ import annotations

import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
NA_ROOT = os.path.dirname(HERE)
SOURCE = os.path.join(NA_ROOT, "Convertia.png")
ASSETS = os.path.join(HERE, "assets")

ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
SPLASH_SIZE = 512
LOGO_WIDTH = 220
POPUP_SIZE = 480


def _load_source() -> Image.Image:
    if not os.path.isfile(SOURCE):
        raise FileNotFoundError(f"Logo not found: {SOURCE}")
    img = Image.open(SOURCE)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    return img


def write_splash(img: Image.Image) -> str:
    os.makedirs(ASSETS, exist_ok=True)
    out = os.path.join(ASSETS, "splash.png")
    splash = img.copy()
    splash.thumbnail((SPLASH_SIZE, SPLASH_SIZE), Image.Resampling.LANCZOS)
    splash.save(out, format="PNG", optimize=True)
    return out


def write_logo(img: Image.Image) -> str:
    os.makedirs(ASSETS, exist_ok=True)
    out = os.path.join(ASSETS, "logo.png")
    logo = img.copy()
    logo.thumbnail((LOGO_WIDTH, LOGO_WIDTH), Image.Resampling.LANCZOS)
    logo.save(out, format="PNG", optimize=True)
    return out


def write_popup(img: Image.Image) -> str:
    os.makedirs(ASSETS, exist_ok=True)
    out = os.path.join(ASSETS, "image.png")
    popup = img.copy()
    popup.thumbnail((POPUP_SIZE, POPUP_SIZE), Image.Resampling.LANCZOS)
    popup.save(out, format="PNG", optimize=True)
    return out


def write_ico(img: Image.Image) -> str:
    os.makedirs(ASSETS, exist_ok=True)
    out = os.path.join(ASSETS, "app.ico")
    icons = []
    for size in ICO_SIZES:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        icons.append(resized)
    icons[0].save(
        out,
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
        append_images=icons[1:],
    )
    return out


def main() -> int:
    img = _load_source()
    splash = write_splash(img)
    logo = write_logo(img)
    popup = write_popup(img)
    ico = write_ico(img)
    print(f"Source:  {SOURCE} ({img.size[0]}x{img.size[1]})")
    print(f"Wrote:   {splash}")
    print(f"Wrote:   {logo}")
    print(f"Wrote:   {popup}")
    print(f"Wrote:   {ico}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
