"""Calcul de la rareté de chaque personnage.

La rareté est dérivée d'un "score de rareté" agrégé à partir des poids de
tirage du pelage, des yeux et du style : plus un trait est rare (poids faible),
plus il pousse le score vers le haut. Le score est ensuite mappé vers un palier
défini dans config/rarity.yaml. Des règles "rare_combinations" peuvent forcer un
palier minimum.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .combination_generator import Character, ConfigBundle, _rule_matches


class RarityEngine:
    def __init__(self, bundle: ConfigBundle):
        self.rarity_cfg = bundle.rarity
        self.tiers: List[Dict[str, Any]] = sorted(
            self.rarity_cfg["tiers"], key=lambda t: t["max_score"]
        )
        self.weights: Dict[str, float] = self.rarity_cfg.get("score_weights", {})
        self.rare_rules: List[Dict[str, Any]] = self.rarity_cfg.get("rare_combinations", [])
        self._tier_by_key = {t["key"]: t for t in self.tiers}

        # Pré-calcule l'échelle de "rareté individuelle" de chaque trait :
        # plus le poids est faible parmi ses pairs, plus le trait est rare.
        self._fur_scale = self._build_scale(bundle.fur_colors)
        self._eye_scale = self._build_scale(bundle.eye_colors)
        self._style_scale = self._build_scale(bundle.styles)

    @staticmethod
    def _build_scale(items: List[Dict[str, Any]]) -> Dict[str, float]:
        """Associe à chaque trait une rareté normalisée dans [0, 1].

        0 = le trait le plus fréquent du groupe, 1 = le plus rare.
        """
        weights = {it["key"]: max(0.0001, float(it.get("rarity_weight", 1))) for it in items}
        if not weights:
            return {}
        wmin = min(weights.values())
        wmax = max(weights.values())
        span = (wmax - wmin) or 1.0
        # Inversion : poids faible -> rareté élevée.
        return {k: (wmax - w) / span for k, w in weights.items()}

    def score(self, character: Character) -> float:
        """Score de rareté agrégé dans [0, 1]."""
        f = self._fur_scale.get(character.fur["key"], 0.0)
        e = self._eye_scale.get(character.eyes["key"], 0.0)
        s = self._style_scale.get(character.style["key"], 0.0)
        wf = self.weights.get("fur", 0.33)
        we = self.weights.get("eyes", 0.34)
        ws = self.weights.get("style", 0.33)
        total_w = (wf + we + ws) or 1.0
        return (f * wf + e * we + s * ws) / total_w

    def _tier_for_score(self, score: float) -> Dict[str, Any]:
        for tier in self.tiers:
            if score <= tier["max_score"]:
                return tier
        return self.tiers[-1]

    def _apply_rare_rules(self, character: Character, tier: Dict[str, Any]) -> Dict[str, Any]:
        """Force éventuellement un palier minimum selon les rare_combinations."""
        traits = character.trait_dict()
        best = tier
        for rule in self.rare_rules:
            match = rule.get("match", {})
            min_tier_key = rule.get("min_tier")
            if match and min_tier_key and _rule_matches(match, traits):
                forced = self._tier_by_key.get(min_tier_key)
                if forced and forced["order"] > best["order"]:
                    best = forced
        return best

    def assign(self, character: Character) -> Character:
        """Calcule et fixe la rareté (palier + score) sur le personnage."""
        score = self.score(character)
        tier = self._tier_for_score(score)
        tier = self._apply_rare_rules(character, tier)
        character.rarity = tier
        character.rarity_score = round(score, 4)
        return character

    def assign_all(self, characters: List[Character]) -> List[Character]:
        for c in characters:
            self.assign(c)
        return characters

    # -- statistiques -------------------------------------------------------
    @staticmethod
    def distribution(characters: List[Character], trait: str) -> Dict[str, Dict[str, Any]]:
        """Répartition (compte + pourcentage) d'un trait dans la collection.

        `trait` ∈ {"fur", "eyes", "style", "object", "rarity"}.
        """
        getter = {
            "fur": lambda c: c.fur["name"],
            "eyes": lambda c: c.eyes["name"],
            "style": lambda c: c.style["name"],
            "object": lambda c: c.obj["name"],
            "rarity": lambda c: (c.rarity or {}).get("name", "N/A"),
        }[trait]
        total = len(characters) or 1
        counts: Dict[str, int] = {}
        for c in characters:
            name = getter(c)
            counts[name] = counts.get(name, 0) + 1
        return {
            name: {"count": n, "percent": round(100.0 * n / total, 2)}
            for name, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        }
