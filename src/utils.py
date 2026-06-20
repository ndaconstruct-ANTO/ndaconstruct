"""Fonctions utilitaires partagées : chargement de configuration, chemins, seeds.

Ce module ne dépend que de la bibliothèque standard et de PyYAML.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict

import yaml

# Racine du projet = dossier parent de src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_path(path: str | os.PathLike) -> Path:
    """Transforme un chemin relatif (de la config) en chemin absolu fiable.

    Les chemins relatifs sont résolus depuis la racine du projet, ce qui rend
    le programme indépendant du dossier courant d'où on le lance.
    """
    p = Path(path)
    if p.is_absolute():
        return p
    return (PROJECT_ROOT / p).resolve()


def load_yaml(path: str | os.PathLike) -> Dict[str, Any]:
    """Charge un fichier YAML et renvoie un dictionnaire."""
    full = resolve_path(path)
    with open(full, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data or {}


def load_text(path: str | os.PathLike) -> str:
    """Charge un fichier texte (prompt) en chaîne de caractères."""
    full = resolve_path(path)
    with open(full, "r", encoding="utf-8") as fh:
        return fh.read()


def save_json(path: str | os.PathLike, data: Any, *, indent: int = 2) -> None:
    """Écrit des données en JSON (UTF-8, lisible)."""
    full = resolve_path(path)
    full.parent.mkdir(parents=True, exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=indent)


def save_text(path: str | os.PathLike, text: str) -> None:
    """Écrit du texte (UTF-8)."""
    full = resolve_path(path)
    full.parent.mkdir(parents=True, exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(text)


def ensure_dir(path: str | os.PathLike) -> Path:
    """Crée un dossier (et ses parents) si nécessaire et renvoie son chemin."""
    full = resolve_path(path)
    full.mkdir(parents=True, exist_ok=True)
    return full


def slugify(value: str) -> str:
    """Transforme un texte en identifiant simple (minuscules, underscores)."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def format_id(index: int, width: int = 4) -> str:
    """Renvoie un identifiant numérique zéro-paddé, ex: 1 -> '0001'."""
    return str(index).zfill(width)


def stable_hash(*parts: Any) -> str:
    """Hash déterministe (sha256 court) d'une combinaison de valeurs.

    Sert à détecter les doublons de combinaisons de manière stable et
    reproductible entre deux exécutions.
    """
    joined = "|".join(str(p) for p in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def derive_seed(master_seed: int, *parts: Any) -> int:
    """Dérive une seed entière reproductible à partir de la seed maître.

    Chaque image obtient ainsi sa propre seed stable, dérivée de la seed
    globale et de l'identité de la combinaison.
    """
    digest = stable_hash(master_seed, *parts)
    # 8 premiers hex -> entier 32 bits, toujours identique pour les mêmes entrées
    return int(digest[:8], 16)
