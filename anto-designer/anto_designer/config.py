"""Chemins et dossiers de données utilisateur (locaux, jamais cloud)."""

from __future__ import annotations

import os
from pathlib import Path


def data_root() -> Path:
    """Dossier de données utilisateur, configurable via ANTO_DATA_DIR."""
    env = os.environ.get("ANTO_DATA_DIR")
    if env:
        return Path(env)
    # Emplacement par défaut, multi-plateforme.
    if os.name == "nt":  # Windows
        base = Path(os.environ.get("APPDATA", Path.home())) / "AntoDesigner"
    else:
        base = Path.home() / ".anto-designer"
    return base


def ensure_dirs(root: Path | None = None) -> dict:
    """Crée l'arborescence de données et retourne les chemins clés."""
    root = Path(root) if root else data_root()
    paths = {
        "root": root,
        "collections": root / "collections",
        "backups": root / "backups",
        "logs": root / "logs",
        "exports": root / "exports",
        "db": root / "anto_designer.db",
    }
    for key, p in paths.items():
        if key != "db":
            p.mkdir(parents=True, exist_ok=True)
    return paths
