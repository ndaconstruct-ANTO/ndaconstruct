"""Système anti-doublons : garantit que chaque combinaison est unique."""

from __future__ import annotations

import json
from pathlib import Path


class DuplicateChecker:
    """Suit les combinaisons déjà utilisées (clé = pelage/yeux/style).

    Peut charger un registre existant pour éviter les doublons entre plusieurs
    générations successives.
    """

    def __init__(self) -> None:
        self._seen: set[tuple] = set()

    def __len__(self) -> int:
        return len(self._seen)

    def has(self, key: tuple) -> bool:
        return key in self._seen

    def add(self, key: tuple) -> bool:
        """Enregistre ``key``. Retourne False si elle était déjà présente."""
        if key in self._seen:
            return False
        self._seen.add(key)
        return True

    def load_registry(self, path: Path) -> None:
        """Charge un registre de combinaisons déjà générées (si présent)."""
        path = Path(path)
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data.get("combinations", []):
            self._seen.add(tuple(entry))

    def export(self) -> list:
        return [list(k) for k in sorted(self._seen)]
