"""Résolution des chemins de ressources (compatible PyInstaller).

En mode normal : chemin dans le paquet. En mode "gelé" (.exe PyInstaller) :
chemin dans le dossier temporaire d'extraction (sys._MEIPASS).
"""

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(*parts: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS) / "anto_designer"
    else:
        base = Path(__file__).resolve().parent
    return base.joinpath(*parts)


def icon_path() -> str:
    p = resource_path("assets", "icon.ico")
    if not p.exists():
        p = resource_path("assets", "icon.png")
    return str(p) if p.exists() else ""
