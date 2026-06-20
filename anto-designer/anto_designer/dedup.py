"""Anti-doublons : signatures de combinaison + hash d'image finale."""

from __future__ import annotations

import hashlib


def signature(chosen: dict) -> str:
    """Signature unique d'une combinaison.

    ``chosen`` : {category_slug: layer_code | None}. L'ordre des catégories est
    normalisé pour rendre la signature stable.
    """
    parts = [f"{k}={chosen[k] or '-'}" for k in sorted(chosen)]
    return "|".join(parts)


def signature_hash(chosen: dict) -> str:
    return hashlib.sha1(signature(chosen).encode("utf-8")).hexdigest()


class DuplicateTracker:
    def __init__(self, existing: set | None = None) -> None:
        self._sigs = set(existing or set())
        self._hashes: set = set()

    def is_dup_signature(self, sig: str) -> bool:
        return sig in self._sigs

    def add_signature(self, sig: str) -> bool:
        if sig in self._sigs:
            return False
        self._sigs.add(sig)
        return True

    def is_dup_image(self, image_hash: str) -> bool:
        return image_hash in self._hashes

    def add_image(self, image_hash: str) -> bool:
        if image_hash in self._hashes:
            return False
        self._hashes.add(image_hash)
        return True
