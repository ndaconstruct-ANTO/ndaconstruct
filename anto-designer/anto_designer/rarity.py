"""Calcul et rapport de rareté à partir de la fréquence réelle des traits."""

from __future__ import annotations

from collections import Counter

TIERS = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic", "Unique"]


def distribution(combinations: list) -> dict:
    """Compte et pourcentage de chaque calque par catégorie + paliers."""
    total = len(combinations) or 1
    per_cat: dict = {}
    tier_counter: Counter = Counter()
    for combo in combinations:
        for slug, layer in combo.chosen.items():
            value = layer.trait_value if layer else "Aucun"
            per_cat.setdefault(slug, Counter())[value] += 1
            if layer:
                tier_counter[layer.rarity_tier] += 1

    report = {"total": len(combinations), "traits": {}, "tiers": {}}
    for slug, counter in per_cat.items():
        base = sum(counter.values()) or 1
        report["traits"][slug] = {
            v: {"count": c, "percent": round(c / base * 100, 2)}
            for v, c in counter.most_common()
        }
    for tier, c in tier_counter.most_common():
        report["tiers"][tier] = {"count": c, "percent": round(c / total * 100, 2)}
    return report


def check_consistency(report: dict) -> list:
    """Vérifie que chaque catégorie totalise ~100% (cohérence)."""
    problems = []
    for slug, values in report["traits"].items():
        total = sum(v["percent"] for v in values.values())
        if abs(total - 100.0) > 1.0:
            problems.append(f"Catégorie '{slug}' : total {total:.1f}% (attendu ~100%)")
    return problems
