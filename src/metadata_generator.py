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

    # -- métadonnées par personnage ----------------------------------------
    def image_filename_for(self, character: Character) -> str:
        return self.image_filename.format(id=character.id)

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
        return {
            "name": f"{self.name} #{character.id}",
            "description": self.description,
            "image": image_ref,
            "attributes": attributes,
            # Champs hors-standard utiles à la reproductibilité (sous "properties").
            "properties": {
                "id": character.id,
                "seed": character.seed,
                "combo_key": character.combo_key,
                "rarity_score": character.rarity_score,
            },
        }

    def write_metadata(self, character: Character) -> str:
        meta = self.build_metadata(character)
        path = f"{self.output_cfg['metadata']}/{character.id}.json"
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
