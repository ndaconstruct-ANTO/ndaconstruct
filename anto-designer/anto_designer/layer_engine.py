"""Moteur de calques : superposition de PNG transparents alignés.

Backend Pillow si disponible (rapide, haute résolution), sinon repli stdlib
(``pnglib``) pour fonctionner et être testé sans aucune dépendance.

Tous les calques d'une collection partagent les mêmes dimensions et le même
point d'origine : la cohérence du personnage est ainsi garantie par construction.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from . import pnglib

try:  # backend rapide optionnel
    from PIL import Image  # type: ignore
    _HAS_PIL = True
except ImportError:  # pragma: no cover
    _HAS_PIL = False


def backend_name() -> str:
    return "Pillow" if _HAS_PIL else "stdlib"


class LayerSizeError(ValueError):
    """Un calque n'a pas les dimensions attendues de la collection."""


def composite(layer_paths: list, width: int, height: int,
              background=(255, 255, 255, 0)) -> bytes:
    """Compose les calques (du fond vers l'avant) et retourne des octets PNG.

    ``layer_paths`` doit déjà être ORDONNÉ (arrière-plan d'abord).
    Vérifie que chaque calque respecte width x height.
    """
    if _HAS_PIL:
        return _composite_pil(layer_paths, width, height, background)
    return _composite_stdlib(layer_paths, width, height, background)


def _composite_pil(layer_paths, width, height, background) -> bytes:
    import io

    canvas = Image.new("RGBA", (width, height), tuple(background))
    for p in layer_paths:
        img = Image.open(p).convert("RGBA")
        if img.size != (width, height):
            raise LayerSizeError(f"{p}: {img.size} != {(width, height)}")
        canvas = Image.alpha_composite(canvas, img)
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


def _composite_stdlib(layer_paths, width, height, background) -> bytes:
    import os
    import tempfile

    canvas = pnglib.new_canvas(width, height, tuple(background))
    for p in layer_paths:
        w, h, rgba = pnglib.read_rgba(p)
        if (w, h) != (width, height):
            raise LayerSizeError(f"{p}: {(w, h)} != {(width, height)}")
        pnglib.alpha_over(canvas, rgba)
    fd, tmp = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        pnglib.write_rgba(tmp, width, height, canvas)
        return Path(tmp).read_bytes()
    finally:
        os.unlink(tmp)


def image_hash(png_bytes: bytes) -> str:
    """Hash SHA-256 de l'image finale (détection de doublons stricts)."""
    return hashlib.sha256(png_bytes).hexdigest()
