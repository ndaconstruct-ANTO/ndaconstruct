"""Tests automatisés du générateur de collection (stdlib unittest)."""

import unittest

from src.combination_generator import (
    generate_combinations,
    is_forbidden,
    max_unique_combinations,
)
from src.prompt_builder import PromptBuilder
from src.metadata_generator import build_metadata, file_base
from src.quality_control import REJECT, check_logical
from src.rarity_engine import assign_rarity, trait_statistics
from src.utils import load_config

_MULTI_HINTS = (" and ", " plus ", "+", "two ", "double")


class CollectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = load_config()

    # 1 — neuf couleurs de pelage
    def test_nine_fur_colors(self):
        self.assertEqual(len(self.cfg.fur_colors), 9)
        codes = {f.code for f in self.cfg.fur_colors}
        self.assertEqual(len(codes), 9, "codes de pelage non uniques")

    # 2 — unicité des identifiants
    def test_unique_ids(self):
        combos = generate_combinations(self.cfg, 50, seed=1)
        uids = [c.uid for c in combos]
        self.assertEqual(len(uids), len(set(uids)))

    # 3 — absence de doublons de combinaison
    def test_no_duplicate_combinations(self):
        combos = generate_combinations(self.cfg, 80, seed=2)
        keys = [c.key for c in combos]
        self.assertEqual(len(keys), len(set(keys)))

    # 4 — un seul objet maximum par personnage
    def test_single_object_per_character(self):
        for s in self.cfg.styles:
            obj = s.held_object.lower()
            self.assertFalse(
                any(h in obj for h in _MULTI_HINTS),
                f"Le style {s.code} semble tenir plusieurs objets : {s.held_object}",
            )

    # 5 — correspondance style / objet
    def test_style_object_match(self):
        combos = generate_combinations(self.cfg, 30, seed=3)
        for c in combos:
            self.assertEqual(c.held_object, c.style.held_object)
            issues = check_logical(c, self.cfg)
            self.assertNotIn(REJECT, {lvl for lvl, _ in issues})

    # 6 — stabilité du prompt de base
    def test_prompt_stability(self):
        builder = PromptBuilder(self.cfg)
        combos = generate_combinations(self.cfg, 5, seed=4)
        c = combos[0]
        p1 = builder.build(c)["positive"]
        p2 = builder.build(c)["positive"]
        self.assertEqual(p1, p2, "le prompt doit être déterministe")
        # Les éléments fixes essentiels doivent être présents.
        for token in ("anthropomorphic baby lion cub", "no visible tail",
                      "no human hands", "white #FFFFFF studio background"):
            self.assertIn(token, p1)
        # Aucun emplacement non résolu ne doit subsister.
        self.assertNotIn("[", p1)

    # 7 — génération correcte des métadonnées JSON
    def test_metadata_json(self):
        combos = generate_combinations(self.cfg, 3, seed=5)
        assign_rarity(self.cfg, combos)
        c = combos[0]
        meta = build_metadata(c, self.cfg, file_base(c, self.cfg) + ".png")
        for key in ("id", "name", "image", "fur_color", "eye_color_left",
                    "eye_color_right", "style", "held_object", "rarity", "attributes"):
            self.assertIn(key, meta)
        self.assertTrue(meta["image"].endswith(".png"))
        self.assertEqual(meta["held_object"], c.style.held_object)

    # 8 — reproductibilité avec une seed
    def test_reproducibility(self):
        a = generate_combinations(self.cfg, 40, seed=123)
        b = generate_combinations(self.cfg, 40, seed=123)
        self.assertEqual([c.key for c in a], [c.key for c in b])
        self.assertEqual([c.seed for c in a], [c.seed for c in b])

    # 9 — respect des combinaisons interdites
    def test_forbidden_respected(self):
        # La règle BLACK + BLACKSHINE doit être détectée.
        fur = self.cfg.fur_by_code["BLACK"]
        eye = self.cfg.eye_by_code["BLACKSHINE"]
        style = self.cfg.styles[0]
        self.assertTrue(is_forbidden(fur, eye, eye, style, self.cfg.forbidden))
        # Aucune combinaison générée ne doit être interdite.
        combos = generate_combinations(self.cfg, 100, seed=6)
        for c in combos:
            self.assertFalse(
                is_forbidden(c.fur, c.eye_left, c.eye_right, c.style, self.cfg.forbidden)
            )

    # 10 — calcul des raretés
    def test_rarity_calculation(self):
        combos = generate_combinations(self.cfg, 60, seed=7)
        assign_rarity(self.cfg, combos)
        valid_tiers = {t.name for t in self.cfg.tiers}
        for c in combos:
            self.assertIn(c.rarity_tier, valid_tiers)
            self.assertGreaterEqual(c.rarity_score, 0.0)
            self.assertLessEqual(c.rarity_score, 100.0)
        stats = trait_statistics(combos)
        # Les pourcentages par type de trait somment ~100%.
        for trait_type, values in stats["traits"].items():
            total_pct = sum(v["percent"] for v in values.values())
            self.assertAlmostEqual(total_pct, 100.0, delta=1.0)

    # bonus — borne de capacité respectée
    def test_capacity_guard(self):
        cap = max_unique_combinations(1, 1, 1)
        self.assertEqual(cap, 1)
        with self.assertRaises(ValueError):
            generate_combinations(
                self.cfg, 5, allowed_fur=["WHITE"], allowed_eyes=["YELLOW"],
                allowed_styles=["DOCTOR"], seed=8,
            )


if __name__ == "__main__":
    unittest.main()
