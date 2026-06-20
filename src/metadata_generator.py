"""Génération des métadonnées NFT et des registres.

Produit :
  - un fichier JSON par image (format compatible collection NFT) ;
  - un CSV global ;
  - un registre des identifiants ;
  - un registre des seeds ;
  - un registre des combinaisons ;
  - un résumé statistique des traits avec pourcentages de rareté.
"""
from __future__ import annotations

import csv
import io
from typing import Any, Dict, List

from . import utils
from .combination_generator import Character, ConfigBundle
from .rarity_engine import RarityEngine


class MetadataGenerator:
    def __init__(self, bundle: ConfigBundle):
        self.bundle = bundle
        self.collection_cfg = bundle.collection["collection"]
        self.output_cfg = bundle.collection["output"]
        self.image_filename = self.collection_cfg.get("image_filename", "{id}.png")
        self.base_uri = self.collection_cfg.get("base_image_uri", "")
        self.name = self.collection_cfg.get("name", "Lion")
        self.description = self.collection_cfg.get("description", "")
        # Champs de métadonnées normalisés (§13) et nommage strict (§14).
        self.id_prefix = self.collection_cfg.get("id_prefix", "LION")
        self.nft_collection_name = self.collection_cfg.get(
            "nft_collection_name", "LIONCEAUX NFT"
        )
        self.species = self.collection_cfg.get("species", "Lion cub")
        self.prompt_version = self.collection_cfg.get("prompt_version", "1.0")
        self.camera = self.collection_cfg.get("camera", "Front view")
        self.image_cfg = bundle.collection["image"]
        # Libellé lisible du fond actif (verrouillé pour toute la collection).
        bg = bundle.collection.get("background", {})
        active = bg.get("active", "white")
        self.background_label = bg.get("presets", {}).get(active, {}).get(
            "name", "Pure white"
        )

    # -- identifiants et noms de fichiers ----------------------------------
    def nft_id(self, character: Character) -> str:
        """Identifiant normalisé, ex: 'LION-0001' (§13)."""
        return f"{self.id_prefix}-{character.id}"

    def _eyes_token(self, character: Character) -> str:
        """Jeton 'yeux' pour le nom de fichier (gère l'hétérochromie)."""
        left = character.left_eye["key"].upper()
        if character.heterochromia:
            return f"{left}-{character.right_eye['key'].upper()}"
        return left

    def image_filename_for(self, character: Character) -> str:
        """Nommage strict §14 : LION_0001_FUR-BLACK_EYES-GREEN_STYLE-GANGSTER.png."""
        fmt = self.image_cfg.get("format", "png")
        return (
            f"{self.id_prefix}_{character.id}"
            f"_FUR-{character.fur['key'].upper()}"
            f"_EYES-{self._eyes_token(character)}"
            f"_STYLE-{character.style['key'].upper()}.{fmt}"
        )

    def metadata_filename_for(self, character: Character) -> str:
        """Nommage strict §14 : LION_0001_METADATA.json."""
        return f"{self.id_prefix}_{character.id}_METADATA.json"

    # -- métadonnées par personnage ----------------------------------------
    def build_metadata(self, character: Character) -> Dict[str, Any]:
        image_ref = self.base_uri + self.image_filename_for(character)
        attributes = [
            {"trait_type": "Pelage", "value": character.fur["name"]},
            {"trait_type": "Yeux", "value": character.eyes["name"]},
            {"trait_type": "Style", "value": character.style["name"]},
            {"trait_type": "Objet", "value": character.obj["name"]},
        ]
        if character.rarity:
            attributes.append(
                {"trait_type": "Rareté", "value": character.rarity["name"]}
            )
        headwear = character.style.get("headwear") or "None"
        return {
            "name": f"{self.name} #{character.id}",
            "description": self.description,
            "image": image_ref,
            # --- Structure normalisée demandée au §13 ---
            "id": self.nft_id(character),
            "collection": self.nft_collection_name,
            "species": self.species,
            "fur_color": character.fur["name"],
            "eye_color_left": character.left_eye["name"],
            "eye_color_right": character.right_eye["name"],
            "style": character.style["name"],
            "outfit": character.style.get("outfit_prompt", ""),
            "headwear": headwear,
            "held_object": character.obj["name"],
            "background": self.background_label,
            "camera": self.camera,
            "format": self.image_cfg.get("aspect_ratio", "1:1"),
            "rarity": (character.rarity or {}).get("name", "To be calculated"),
            "prompt_version": self.prompt_version,
            # --- Standard marketplace (OpenSea) ---
            "attributes": attributes,
            # --- Champs utiles à la reproductibilité ---
            "properties": {
                "id": character.id,
                "seed": character.seed,
                "combo_key": character.combo_key,
                "rarity_score": character.rarity_score,
                "heterochromia": character.heterochromia,
            },
        }

    def write_metadata(self, character: Character) -> str:
        meta = self.build_metadata(character)
        path = f"{self.output_cfg['metadata']}/{self.metadata_filename_for(character)}"
        utils.save_json(path, meta)
        return path

    def write_all_metadata(self, characters: List[Character]) -> List[str]:
        return [self.write_metadata(c) for c in characters]

    # -- CSV global ---------------------------------------------------------
    def build_csv(self, characters: List[Character]) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            ["id", "name", "fur", "eyes", "style", "object", "rarity", "rarity_score", "seed", "image"]
        )
        for c in characters:
            writer.writerow(
                [
                    c.id,
                    f"{self.name} #{c.id}",
                    c.fur["name"],
                    c.eyes["name"],
                    c.style["name"],
                    c.obj["name"],
                    (c.rarity or {}).get("name", ""),
                    c.rarity_score if c.rarity_score is not None else "",
                    c.seed,
                    self.image_filename_for(c),
                ]
            )
        return buffer.getvalue()

    def write_csv(self, characters: List[Character]) -> str:
        content = self.build_csv(characters)
        path = self.output_cfg["csv"]
        utils.save_text(path, content)
        return path

    # -- registres ----------------------------------------------------------
    def write_registries(self, characters: List[Character]) -> Dict[str, str]:
        reg_dir = self.output_cfg.get("registries", "output/registries")

        ids = {c.id: c.combo_key for c in characters}
        seeds = {c.id: c.seed for c in characters}
        combos = [
            {
                "id": c.id,
                "combo_key": c.combo_key,
                "fur": c.fur["key"],
                "eyes": c.eyes["key"],
                "style": c.style["key"],
                "object": c.obj["key"],
            }
            for c in characters
        ]

        paths = {
            "ids": f"{reg_dir}/ids.json",
            "seeds": f"{reg_dir}/seeds.json",
            "combinations": f"{reg_dir}/combinations.json",
        }
        utils.save_json(paths["ids"], {"ids": ids})
        utils.save_json(paths["seeds"], {"seeds": seeds})
        utils.save_json(paths["combinations"], {"combinations": combos})
        return paths

    # -- statistiques de rareté --------------------------------------------
    def build_stats(self, characters: List[Character]) -> Dict[str, Any]:
        engine = RarityEngine(self.bundle)
        return {
            "total": len(characters),
            "traits": {
                "Pelage": engine.distribution(characters, "fur"),
                "Yeux": engine.distribution(characters, "eyes"),
                "Style": engine.distribution(characters, "style"),
                "Objet": engine.distribution(characters, "object"),
                "Rareté": engine.distribution(characters, "rarity"),
            },
        }

    def write_stats(self, characters: List[Character]) -> str:
        stats = self.build_stats(characters)
        path = f"{self.output_cfg['reports']}/stats.json"
        utils.save_json(path, stats)
        return path
