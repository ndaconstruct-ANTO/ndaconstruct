"""Calcul de la rareté à partir de la fréquence réelle des traits."""

from __future__ import annotations

from collections import Counter

from .combination_generator import Combination
from .utils import Config

_TIER_ORDER = ["Common", "Uncommon", "Rare", "Epic", "Legendary"]


def compute_frequencies(combos: list) -> dict:
    """Compte les occurrences de chaque valeur de trait."""
    freq = {
        "fur": Counter(),
        "eyes": Counter(),
        "style": Counter(),
    }
    for c in combos:
        freq["fur"][c.fur.name_fr] += 1
        freq["eyes"][c.eye_left.name_fr] += 1
        if c.heterochromia:
            freq["eyes"][c.eye_right.name_fr] += 1
        freq["style"][c.style.name_fr] += 1
    return freq


def _raw_score(combo: Combination, freq: dict, total: int, weights: dict) -> float:
    """Score brut : plus un trait est rare (peu fréquent), plus le score monte."""
    w_fur = float(weights.get("fur", 1.0))
    w_eyes = float(weights.get("eyes", 1.0))
    w_style = float(weights.get("style", 1.0))
    hetero_bonus = float(weights.get("heterochromia_bonus", 0.0))

    fur_r = 1.0 - freq["fur"][combo.fur.name_fr] / total
    style_r = 1.0 - freq["style"][combo.style.name_fr] / total
    eye_l = 1.0 - freq["eyes"][combo.eye_left.name_fr] / total
    if combo.heterochromia:
        eye_r = 1.0 - freq["eyes"][combo.eye_right.name_fr] / total
        eye_r_avg = (eye_l + eye_r) / 2.0
    else:
        eye_r_avg = eye_l

    score = w_fur * fur_r + w_eyes * eye_r_avg + w_style * style_r
    if combo.heterochromia:
        score += hetero_bonus / 100.0
    return score


def _tier_for(score_0_100: float, config: Config) -> tuple:
    tier = config.tiers[0]
    for t in config.tiers:
        if score_0_100 >= t.threshold:
            tier = t
    return tier.name, tier.color


def _bump_min_tier(current: str, minimum: str) -> str:
    if _TIER_ORDER.index(minimum) > _TIER_ORDER.index(current):
        return minimum
    return current


def assign_rarity(config: Config, combos: list) -> None:
    """Calcule et affecte le palier de rareté à chaque combinaison (in place)."""
    if not combos:
        return
    total = len(combos)
    freq = compute_frequencies(combos)
    weights = config.rarity_weights

    raw = [_raw_score(c, freq, total, weights) for c in combos]
    lo, hi = min(raw), max(raw)
    span = (hi - lo) or 1.0

    tier_color = {t.name: t.color for t in config.tiers}

    for combo, r in zip(combos, raw):
        score = (r - lo) / span * 100.0
        tier_name, color = _tier_for(score, config)

        # Combinaisons volontairement rares : palier minimum forcé.
        for rule in config.rare_combinations:
            fur_ok = ("fur" not in rule) or (combo.fur.code in rule["fur"])
            eye_ok = ("eye" not in rule) or (
                combo.eye_left.code in rule["eye"] or combo.eye_right.code in rule["eye"]
            )
            style_ok = ("style" not in rule) or (combo.style.code in rule["style"])
            if fur_ok and eye_ok and style_ok and any(
                k in rule for k in ("fur", "eye", "style")
            ):
                min_tier = rule.get("min_tier")
                if min_tier in _TIER_ORDER:
                    tier_name = _bump_min_tier(tier_name, min_tier)
                    color = tier_color.get(tier_name, color)

        combo.rarity_score = round(score, 2)
        combo.rarity_tier = tier_name
        combo.rarity_color = color


def trait_statistics(combos: list) -> dict:
    """Résumé statistique : comptes et pourcentages par valeur de trait + paliers."""
    total = len(combos) or 1
    freq = compute_frequencies(combos)
    stats = {"total": len(combos), "traits": {}, "rarity_tiers": {}}

    for trait_type, counter in freq.items():
        base = sum(counter.values()) or 1
        stats["traits"][trait_type] = {
            value: {"count": cnt, "percent": round(cnt / base * 100, 2)}
            for value, cnt in counter.most_common()
        }

    tier_counter = Counter(c.rarity_tier for c in combos)
    for tier, cnt in tier_counter.most_common():
        stats["rarity_tiers"][tier] = {
            "count": cnt,
            "percent": round(cnt / total * 100, 2),
        }
    return stats
