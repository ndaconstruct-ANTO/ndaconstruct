"""Chargement de configuration, modèles de données et utilitaires partagés."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml  # PyYAML
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "PyYAML est requis. Installez-le avec : pip install -r requirements.txt"
    ) from exc


# --- Chemins par défaut ------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
OUTPUT_DIR = PROJECT_ROOT / "output"


# --- Modèles de données ------------------------------------------------------
@dataclass(frozen=True)
class TraitValue:
    """Une valeur de trait (couleur de pelage ou d'yeux)."""

    code: str
    name_en: str
    name_fr: str
    hex: str = ""
    prompt: str = ""
    rarity_weight: float = 1.0
    effect: str = ""


@dataclass(frozen=True)
class Style:
    """Un style / métier / univers et son unique objet associé."""

    code: str
    name_en: str
    name_fr: str
    outfit: str
    headwear: str
    held_object: str
    palette: tuple = ()
    forbidden: tuple = ()
    rarity: str = "Common"
    footwear: str = ""  # description de chaussures adaptées (optionnel)
    text: str = ""      # texte affiché sur un accessoire (ex. "FLIPPERZ")
    text_on: str = "garment"  # support du texte (cap, hoodie, t-shirt, spray can…)


@dataclass(frozen=True)
class Tier:
    """Un palier de rareté."""

    name: str
    name_fr: str
    threshold: float
    color: str


@dataclass
class Config:
    """Configuration complète et chargée de la collection."""

    collection: dict
    format: dict
    background: dict
    composition: dict
    master_model: dict
    generation: dict
    fur_colors: list
    eye_colors: list
    styles: list
    tiers: list
    rarity_weights: dict
    rare_combinations: list
    forbidden: list = field(default_factory=list)

    # Index par code (remplis après chargement)
    fur_by_code: dict = field(default_factory=dict)
    eye_by_code: dict = field(default_factory=dict)
    style_by_code: dict = field(default_factory=dict)

    @property
    def resolution(self) -> int:
        return int(self.format.get("resolution", 2048))

    @property
    def naming_template(self) -> str:
        return self.generation.get(
            "naming_template",
            "LION_{id:04d}_FUR-{fur_code}_EYES-{eye_code}_STYLE-{style_code}",
        )


# --- Chargement --------------------------------------------------------------
def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _trait_list(raw: list) -> list:
    out = []
    for item in raw:
        out.append(
            TraitValue(
                code=item["code"],
                name_en=item["name_en"],
                name_fr=item["name_fr"],
                hex=item.get("hex", ""),
                prompt=item.get("prompt", ""),
                rarity_weight=float(item.get("rarity_weight", 1.0)),
                effect=item.get("effect", ""),
            )
        )
    return out


def _style_list(raw: list) -> list:
    out = []
    for item in raw:
        out.append(
            Style(
                code=item["code"],
                name_en=item["name_en"],
                name_fr=item["name_fr"],
                outfit=item["outfit"],
                headwear=item.get("headwear", "None"),
                held_object=item.get("held_object", "None"),
                palette=tuple(item.get("palette", []) or []),
                forbidden=tuple(item.get("forbidden", []) or []),
                rarity=item.get("rarity", "Common"),
                footwear=item.get("footwear", ""),
                text=item.get("text", ""),
                text_on=item.get("text_on", "garment"),
            )
        )
    return out


def load_config(config_dir: Path = CONFIG_DIR) -> Config:
    """Charge tous les fichiers YAML de configuration dans un objet ``Config``."""
    config_dir = Path(config_dir)
    collection_cfg = load_yaml(config_dir / "collection.yaml")
    fur = _trait_list(load_yaml(config_dir / "fur_colors.yaml")["fur_colors"])
    eyes = _trait_list(load_yaml(config_dir / "eye_colors.yaml")["eye_colors"])
    styles = _style_list(load_yaml(config_dir / "styles.yaml")["styles"])
    rarity_cfg = load_yaml(config_dir / "rarity.yaml")
    forbidden_cfg = load_yaml(config_dir / "forbidden_combinations.yaml") or {}

    tiers = [
        Tier(
            name=t["name"],
            name_fr=t.get("name_fr", t["name"]),
            threshold=float(t["threshold"]),
            color=t.get("color", "#999999"),
        )
        for t in rarity_cfg["tiers"]
    ]

    cfg = Config(
        collection=collection_cfg.get("collection", {}),
        format=collection_cfg.get("format", {}),
        background=collection_cfg.get("background", {}),
        composition=collection_cfg.get("composition", {}),
        master_model=collection_cfg.get("master_model", {}),
        generation=collection_cfg.get("generation", {}),
        fur_colors=fur,
        eye_colors=eyes,
        styles=styles,
        tiers=tiers,
        rarity_weights=rarity_cfg.get("weights", {}),
        rare_combinations=rarity_cfg.get("rare_combinations", []) or [],
        forbidden=forbidden_cfg.get("forbidden", []) or [],
    )
    cfg.fur_by_code = {t.code: t for t in fur}
    cfg.eye_by_code = {t.code: t for t in eyes}
    cfg.style_by_code = {s.code: s for s in styles}
    return cfg


# --- Helpers d'écriture ------------------------------------------------------
def ensure_dir(path: Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data) -> None:
    ensure_dir(Path(path).parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
