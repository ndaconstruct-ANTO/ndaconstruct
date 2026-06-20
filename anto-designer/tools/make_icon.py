"""Génère l'icône de marque d'Anto Designer (PNG + ICO multi-tailles).

100% bibliothèque standard (via ``anto_designer.pnglib``). Produit :
  anto_designer/assets/icon.png   (256x256)
  anto_designer/assets/icon.ico   (16/32/48/256)
"""

from __future__ import annotations

import os
import struct
import sys
import tempfile
from pathlib import Path

# Permet d'exécuter ce script directement (double-clic) : on ajoute la racine.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from anto_designer import pnglib
from anto_designer.branding import BRANDING

ASSETS = Path(__file__).resolve().parent.parent / "anto_designer" / "assets"
S = 256


def _hex(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


def _set(buf, w, x, y, rgba):
    if 0 <= x < w and 0 <= y < w:
        o = (y * w + x) * 4
        buf[o], buf[o + 1], buf[o + 2], buf[o + 3] = rgba


def _rect(buf, w, x0, y0, x1, y1, rgba):
    for y in range(max(0, y0), min(w, y1)):
        for x in range(max(0, x0), min(w, x1)):
            _set(buf, w, x, y, rgba)


def _ellipse(buf, w, cx, cy, rx, ry, rgba):
    for y in range(cy - ry, cy + ry + 1):
        for x in range(cx - rx, cx + rx + 1):
            if rx and ry and ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                _set(buf, w, x, y, rgba)


def _rounded_bg(buf, w, rgba, radius):
    _rect(buf, w, radius, 0, w - radius, w, rgba)
    _rect(buf, w, 0, radius, w, w - radius, rgba)
    for cx, cy in ((radius, radius), (w - radius, radius),
                   (radius, w - radius), (w - radius, w - radius)):
        _ellipse(buf, w, cx, cy, radius, radius, rgba)


def draw_icon() -> bytearray:
    t = BRANDING.theme
    primary = _hex(t["primary"])
    gold = _hex(t["accent"])
    tan = (235, 200, 140, 255)
    dark = (40, 30, 60, 255)

    buf = pnglib.new_canvas(S, S, (0, 0, 0, 0))
    _rounded_bg(buf, S, primary, 56)            # fond violet arrondi
    # mini lionceau
    _ellipse(buf, S, 100, 96, 22, 26, tan)      # oreille G
    _ellipse(buf, S, 156, 96, 22, 26, tan)      # oreille D
    _ellipse(buf, S, 128, 120, 64, 60, tan)     # tête
    _ellipse(buf, S, 108, 116, 9, 12, dark)     # oeil G
    _ellipse(buf, S, 148, 116, 9, 12, dark)     # oeil D
    _ellipse(buf, S, 128, 140, 10, 8, dark)     # museau
    # socle doré (barre de marque)
    _rect(buf, S, 64, 196, 192, 212, gold)
    return buf


def _downscale(src, sw, dw):
    dst = pnglib.new_canvas(dw, dw, (0, 0, 0, 0))
    for y in range(dw):
        sy = y * sw // dw
        for x in range(dw):
            sx = x * sw // dw
            so = (sy * sw + sx) * 4
            do = (y * dw + x) * 4
            dst[do:do + 4] = src[so:so + 4]
    return dst


def _png_bytes(w, buf) -> bytes:
    fd, tmp = tempfile.mkstemp(suffix=".png"); os.close(fd)
    try:
        pnglib.write_rgba(tmp, w, w, buf)
        return Path(tmp).read_bytes()
    finally:
        os.unlink(tmp)


def _write_ico(path: Path, images: list) -> None:
    # images : [(size, png_bytes)]
    n = len(images)
    header = struct.pack("<HHH", 0, 1, n)
    entries = b""
    offset = 6 + 16 * n
    blobs = b""
    for size, data in images:
        bsize = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", bsize, bsize, 0, 0, 1, 32,
                               len(data), offset)
        offset += len(data)
        blobs += data
    path.write_bytes(header + entries + blobs)


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    big = draw_icon()
    pnglib.write_rgba(ASSETS / "icon.png", S, S, big)
    images = []
    for size in (16, 32, 48, 256):
        buf = big if size == S else _downscale(big, S, size)
        images.append((size, _png_bytes(size, buf)))
    _write_ico(ASSETS / "icon.ico", images)
    print("Icône générée :", ASSETS / "icon.ico", "et", ASSETS / "icon.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
