"""Moteur de génération des combinaisons uniques de lionceaux.

Combine pelage, yeux (gauche/droite), style (et son unique objet), en évitant
les doublons et les combinaisons interdites, de façon reproductible (seed).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .duplicate_checker import DuplicateChecker
from .utils import Config, Style, TraitValue


@dataclass
class Combination:
    """Une combinaison complète et unique = un futur NFT."""

    id: int
    uid: str
    fur: TraitValue
    eye_left: TraitValue
    eye_right: TraitValue
    style: Style
    held_object: str
    seed: int
    rarity_tier: str = "Common"
    rarity_score: float = 0.0
    rarity_color: str = "#B0B0B0"

    @property
    def key(self) -> tuple:
        """Clé d'unicité (insensible à l'objet, qui découle du style)."""
        return (self.fur.code, self.eye_left.code, self.eye_right.code, self.style.code)

    @property
    def heterochromia(self) -> bool:
        return self.eye_left.code != self.eye_right.code


def _weighted_choice(rng: random.Random, items: list, weights: list):
    return rng.choices(items, weights=weights, k=1)[0]


def is_forbidden(fur: TraitValue, eye_l: TraitValue, eye_r: TraitValue,
                 style: Style, rules: list) -> bool:
    """Vrai si la combinaison correspond à TOUTES les contraintes d'une règle."""
    for rule in rules:
        fur_ok = ("fur" not in rule) or (fur.code in rule["fur"])
        eye_ok = ("eye" not in rule) or (
            eye_l.code in rule["eye"] or eye_r.code in rule["eye"]
        )
        style_ok = ("style" not in rule) or (style.code in rule["style"])
        # Une règle s'applique seulement si elle contraint au moins un trait.
        constrained = any(k in rule for k in ("fur", "eye", "style"))
        if constrained and fur_ok and eye_ok and style_ok:
            return True
    return False


def max_unique_combinations(n_fur: int, n_eyes: int, n_styles: int) -> int:
    """Borne haute du nombre de combinaisons uniques possibles."""
    # yeux : n identiques + n*(n-1) hétérochromes = n*n
    return n_fur * n_styles * (n_eyes * n_eyes)


def generate_combinations(
    config: Config,
    count: int,
    *,
    allowed_fur: list | None = None,
    allowed_eyes: list | None = None,
    allowed_styles: list | None = None,
    rarity: str | None = None,
    seed: int | None = None,
    checker: DuplicateChecker | None = None,
) -> list:
    """Génère ``count`` combinaisons uniques, reproductibles via ``seed``."""
    if count < 1:
        raise ValueError("count doit être >= 1")

    furs = _filter(config.fur_colors, allowed_fur)
    eyes = _filter(config.eye_colors, allowed_eyes)
    styles = _filter(config.styles, allowed_styles)
    if rarity:
        styles = [s for s in styles if s.rarity.lower() == rarity.lower()] or styles

    if not furs or not eyes or not styles:
        raise ValueError("Aucun trait disponible après filtrage (vérifiez les options).")

    capacity = max_unique_combinations(len(furs), len(eyes), len(styles))
    checker = checker or DuplicateChecker()
    remaining_capacity = capacity - len(checker)
    if count > remaining_capacity:
        raise ValueError(
            f"Impossible de produire {count} combinaisons uniques : capacité "
            f"maximale {capacity} (restantes {remaining_capacity}). "
            f"Ajoutez des styles, des couleurs d'yeux ou réduisez --count."
        )

    base_seed = config.generation.get("global_seed", 0) if seed is None else seed
    rng = random.Random(base_seed)
    allow_hetero = bool(config.generation.get("allow_heterochromia", True))
    hetero_p = float(config.generation.get("heterochromia_probability", 0.0))

    fur_w = [t.rarity_weight for t in furs]
    eye_w = [t.rarity_weight for t in eyes]
    style_w = [_style_weight(s) for s in styles]

    combos: list = []
    next_id = len(checker) + 1
    attempts = 0
    max_attempts = max(10000, count * 200)

    while len(combos) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(
                "Trop de tentatives pour éviter les doublons ; capacité quasi atteinte."
            )
        fur = _weighted_choice(rng, furs, fur_w)
        style = _weighted_choice(rng, styles, style_w)
        eye_left = _weighted_choice(rng, eyes, eye_w)
        if allow_hetero and len(eyes) > 1 and rng.random() < hetero_p:
            eye_right = _weighted_choice(rng, eyes, eye_w)
        else:
            eye_right = eye_left

        if is_forbidden(fur, eye_left, eye_right, style, config.forbidden):
            continue

        key = (fur.code, eye_left.code, eye_right.code, style.code)
        if not checker.add(key):
            continue

        cid = next_id
        next_id += 1
        uid = f"LION-{cid:04d}"
        # Seed reproductible et propre à chaque image.
        img_seed = (base_seed * 1_000_003 + cid) & 0x7FFFFFFF
        combos.append(
            Combination(
                id=cid,
                uid=uid,
                fur=fur,
                eye_left=eye_left,
                eye_right=eye_right,
                style=style,
                held_object=style.held_object,
                seed=img_seed,
            )
        )

    return combos


def _filter(values: list, allowed_codes: list | None) -> list:
    if not allowed_codes:
        return list(values)
    allowed = {c.upper() for c in allowed_codes}
    return [v for v in values if v.code.upper() in allowed]


_RARITY_BASE_WEIGHT = {
    "common": 50,
    "uncommon": 25,
    "rare": 15,
    "epic": 8,
    "legendary": 2,
}


def _style_weight(style: Style) -> float:
    return float(_RARITY_BASE_WEIGHT.get(style.rarity.lower(), 10))
