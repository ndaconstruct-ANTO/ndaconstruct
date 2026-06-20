"""Détection des doublons et tenue de l'historique des combinaisons.

Garantit qu'aucune image n'a exactement la même combinaison qu'une autre, et
permet de reprendre une collection sans réutiliser des combinaisons déjà créées.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set

from . import utils
from .combination_generator import Character


class DuplicateChecker:
    def __init__(self, history_path: str = "output/registries/combinations.json"):
        self.history_path = history_path
        self._seen: Set[str] = set()
        self._records: List[Dict[str, str]] = []

    # -- historique persistant ---------------------------------------------
    def load_history(self) -> Set[str]:
        """Charge les combinaisons déjà enregistrées (si le fichier existe)."""
        path = utils.resolve_path(self.history_path)
        if not Path(path).exists():
            return set()
        data = utils.load_yaml(path) if str(path).endswith((".yaml", ".yml")) else None
        if data is None:
            import json

            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        records = data.get("combinations", []) if isinstance(data, dict) else []
        self._records = records
        self._seen = {r["combo_key"] for r in records}
        return set(self._seen)

    # -- vérification en mémoire -------------------------------------------
    def is_duplicate(self, character: Character) -> bool:
        return character.combo_key in self._seen

    def register(self, character: Character) -> None:
        """Ajoute une combinaison à l'historique en mémoire."""
        if character.combo_key in self._seen:
            raise ValueError(
                f"Doublon détecté pour {character.id} : {character.combo_key}"
            )
        self._seen.add(character.combo_key)
        self._records.append(
            {
                "id": character.id,
                "combo_key": character.combo_key,
                "fur": character.fur["key"],
                "eyes": character.eyes["key"],
                "style": character.style["key"],
                "object": character.obj["key"],
                "seed": character.seed,
            }
        )

    def register_all(self, characters: List[Character]) -> None:
        for c in characters:
            self.register(c)

    @staticmethod
    def find_duplicates(characters: List[Character]) -> List[str]:
        """Renvoie la liste des combo_key apparaissant plusieurs fois."""
        seen: Set[str] = set()
        dups: List[str] = []
        for c in characters:
            if c.combo_key in seen and c.combo_key not in dups:
                dups.append(c.combo_key)
            seen.add(c.combo_key)
        return dups

    # -- persistance --------------------------------------------------------
    def save_history(self) -> None:
        utils.save_json(self.history_path, {"combinations": self._records})
