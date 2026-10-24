"""Draw the installer's wizard images from the app icon (run by build_installer.ps1).

Usage: python packaging/make_wizard_images.py <out_dir>
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ICON = Path(__file__).resolve().parents[1] / "src" / "kaiwa" / "desktop" / "assets" / "kaiwa-full-icon.png"
PANEL = (23, 26, 33)  # the icon's own dark tile
WHITE = (255, 255, 255)


def _icon(size: int) -> Image.Image:
    return Image.open(ICON).convert("RGBA").resize((size, size), Image.LANCZOS)


def _on(bg: tuple[int, int, int], size: tuple[int, int], icon: int, top: int | None = None) -> Image.Image:
    canvas = Image.new("RGB", size, bg)
    mark = _icon(icon)
    x = (size[0] - icon) // 2
    y = (size[1] - icon) // 2 if top is None else top
    canvas.paste(mark, (x, y), mark)
    return canvas


def main(out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    # Inno picks the closest size for the screen's scaling; 100% and 200% here.
    for scale, suffix in ((1, ""), (2, "-2x")):
        # Welcome/finish panel: 164x314 at 100%.
        _on(PANEL, (164 * scale, 314 * scale), 116 * scale, top=75 * scale).save(out / f"wizard-large{suffix}.bmp")
        # Corner mark on the inner pages: 55x58 at 100%.
        _on(WHITE, (55 * scale, 58 * scale), 52 * scale).save(out / f"wizard-small{suffix}.bmp")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "build/installer")
