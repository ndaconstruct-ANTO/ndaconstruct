"""Génération de combinaisons valides et uniques à partir des calques.

Respecte : ordre des catégories (z_index), obligatoire/optionnel, poids de
rareté, incompatibilités et dépendances, anti-doublons, reproductibilité (seed).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import store
from .dedup import DuplicateTracker, signature


@dataclass
class Combination:
    token_id: int
    chosen: dict                 # {category_slug: Layer | None}
    ordered_layers: list         # [Layer, ...] dans l'ordre d'affichage
    signature: str

    @property
    def chosen_codes(self) -> dict:
        return {k: (v.code if v else None) for k, v in self.chosen.items()}


def _none_weight(total_weight: float) -> float:
    return max(1.0, total_weight * 0.25)


def count_capacity(categories_layers: list) -> int:
    """Borne haute du nombre de combinaisons (produit des options par catégorie)."""
    cap = 1
    for cat, layers in categories_layers:
        options = len(layers) + (0 if cat.required else 1)
        cap *= max(1, options)
    return cap


def _valid(chosen_layers: list, rules: list) -> bool:
    ids = {l.id for l in chosen_layers}
    for rule in rules:
        if rule.kind == "incompatible":
            if rule.layer_a in ids and rule.layer_b in ids:
                return False
        elif rule.kind == "requires":
            if rule.layer_a in ids and rule.layer_b not in ids:
                return False
    return True


def generate(conn, collection, count: int, *, seed: int | None = None,
             tracker: DuplicateTracker | None = None) -> list:
    """Retourne ``count`` combinaisons valides et uniques."""
    if count < 1:
        raise ValueError("count doit être >= 1")

    categories = store.list_categories(conn, collection.id)
    cats_layers = [(c, store.list_layers(conn, c.id, active_only=True)) for c in categories]
    rules = store.list_rules(conn, collection.id)

    # Vérifie qu'aucune catégorie obligatoire n'est vide.
    for cat, layers in cats_layers:
        if cat.required and not layers:
            raise ValueError(f"Catégorie obligatoire vide : {cat.name}")

    tracker = tracker or DuplicateTracker()
    capacity = count_capacity(cats_layers) - len(tracker._sigs)
    if count > max(0, capacity):
        raise ValueError(
            f"Impossible de produire {count} combinaisons uniques "
            f"(capacité restante ~{max(0, capacity)}). Ajoutez des calques."
        )

    rng = random.Random(seed if seed is not None else 0)
    out: list = []
    attempts = 0
    max_attempts = max(10000, count * 300)
    next_token = 1

    while len(out) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError("Trop de tentatives (capacité quasi atteinte).")

        chosen: dict = {}
        chosen_layers: list = []
        for cat, layers in cats_layers:
            if not layers:
                chosen[cat.slug] = None
                continue
            items = list(layers)
            weights = [max(0.0001, l.weight) for l in layers]
            if not cat.required:
                items = items + [None]
                weights = weights + [_none_weight(sum(weights))]
            pick = rng.choices(items, weights=weights, k=1)[0]
            chosen[cat.slug] = pick
            if pick is not None:
                chosen_layers.append(pick)

        if not _valid(chosen_layers, rules):
            continue

        sig = signature({k: (v.code if v else None) for k, v in chosen.items()})
        if not tracker.add_signature(sig):
            continue

        # Ordre d'affichage = ordre des catégories (z_index croissant).
        ordered = [chosen[c.slug] for c, _ in cats_layers if chosen[c.slug] is not None]
        out.append(Combination(token_id=next_token, chosen=chosen,
                               ordered_layers=ordered, signature=sig))
        next_token += 1

    return out
