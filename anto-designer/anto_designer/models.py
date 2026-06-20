"""Modèles de données (dataclasses) du domaine Anto Designer."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Collection:
    id: int
    name: str
    slug: str
    width: int
    height: int
    background_mode: str = "white"
    background_color: str = "#FFFFFF"
    master_path: str = ""
    naming_template: str = "{slug}_{id:04d}"
    metadata_config: dict = field(default_factory=dict)


@dataclass
class Category:
    id: int
    collection_id: int
    name: str
    slug: str
    z_index: int          # ordre d'affichage (petit = derrière)
    required: bool = True  # un calque de cette catégorie est obligatoire
    max_one: bool = True   # un seul calque sélectionné


@dataclass
class Layer:
    id: int
    collection_id: int
    category_id: int
    name: str
    code: str
    file_path: str
    thumb_path: str = ""
    rarity_tier: str = "Common"
    weight: float = 1.0
    max_uses: int = 0      # 0 = illimité
    active: bool = True
    trait_value: str = ""  # valeur affichée dans les métadonnées


@dataclass
class Rule:
    """Règle entre calques : 'incompatible' (exclusion) ou 'requires' (dépendance)."""

    id: int
    collection_id: int
    kind: str        # "incompatible" | "requires"
    layer_a: int
    layer_b: int
