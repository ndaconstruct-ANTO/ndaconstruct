"""Tests des métadonnées NFT et du calcul de rareté."""
from src.combination_generator import CombinationGenerator, ConfigBundle
from src.metadata_generator import MetadataGenerator
from src.rarity_engine import RarityEngine


def _chars(bundle, n):
    gen = CombinationGenerator(bundle)
    chars = gen.generate(n)
    RarityEngine(bundle).assign_all(chars)
    return chars


def test_metadata_structure(bundle: ConfigBundle):
    """Le JSON généré doit respecter la structure NFT attendue."""
    chars = _chars(bundle, 5)
    meta_gen = MetadataGenerator(bundle)
    meta = meta_gen.build_metadata(chars[0])

    assert meta["name"].startswith("Lion #")
    assert "description" in meta
    assert meta["image"].endswith(".png")

    trait_types = {a["trait_type"] for a in meta["attributes"]}
    assert {"Pelage", "Yeux", "Style", "Objet", "Rareté"} <= trait_types
    # Reproductibilité : seed et combo_key conservés.
    assert meta["properties"]["seed"] == chars[0].seed
    assert meta["properties"]["combo_key"] == chars[0].combo_key


def test_metadata_has_spec_fields(bundle: ConfigBundle):
    """Le JSON doit exposer la structure normalisée du §13."""
    chars = _chars(bundle, 3)
    meta = MetadataGenerator(bundle).build_metadata(chars[0])
    for key in (
        "id", "collection", "species", "fur_color", "eye_color_left",
        "eye_color_right", "style", "outfit", "headwear", "held_object",
        "background", "camera", "format", "rarity", "prompt_version",
    ):
        assert key in meta, f"champ §13 manquant : {key}"
    assert meta["id"].startswith("LION-")
    assert meta["format"] == "1:1"
    assert meta["camera"] == "Front view"


def test_filename_follows_strict_naming(bundle: ConfigBundle):
    """Le nommage doit suivre le standard strict du §14."""
    chars = _chars(bundle, 2)
    gen = MetadataGenerator(bundle)
    img = gen.image_filename_for(chars[0])
    assert img.startswith("LION_")
    assert "_FUR-" in img and "_EYES-" in img and "_STYLE-" in img
    assert img.endswith(".png")
    assert gen.metadata_filename_for(chars[0]).endswith("_METADATA.json")


def test_heterochromia_distinct_eyes(bundle: ConfigBundle):
    """Avec une probabilité de 1, les deux yeux doivent pouvoir différer (§7)."""
    from src.combination_generator import CombinationGenerator
    bundle.collection["generation"]["heterochromia_chance"] = 1.0
    chars = CombinationGenerator(bundle).generate(5)
    assert any(c.heterochromia for c in chars)
    for c in chars:
        if c.heterochromia:
            assert c.left_eye["key"] != c.right_eye["key"]
            meta = MetadataGenerator(bundle).build_metadata(c)
            assert meta["eye_color_left"] != meta["eye_color_right"]
    bundle.collection["generation"]["heterochromia_chance"] = 0.0


def test_csv_has_all_rows(bundle: ConfigBundle):
    chars = _chars(bundle, 8)
    meta_gen = MetadataGenerator(bundle)
    csv_text = meta_gen.build_csv(chars)
    lines = [l for l in csv_text.splitlines() if l.strip()]
    assert len(lines) == 9  # 1 en-tête + 8 lignes


def test_rarity_assigned(bundle: ConfigBundle):
    """Chaque personnage doit recevoir un palier de rareté connu."""
    chars = _chars(bundle, 30)
    tier_names = {t["name"] for t in bundle.rarity["tiers"]}
    for c in chars:
        assert c.rarity is not None
        assert c.rarity["name"] in tier_names
        assert 0.0 <= c.rarity_score <= 1.0


def test_rarity_deterministic(bundle: ConfigBundle):
    """La rareté est déterministe pour une même seed."""
    a = _chars(bundle, 20)
    b = _chars(bundle, 20)
    assert [c.rarity["key"] for c in a] == [c.rarity["key"] for c in b]


def test_rare_combination_forces_min_tier(bundle: ConfigBundle):
    """Une règle rare_combinations doit forcer un palier minimum."""
    gen = CombinationGenerator(bundle)
    engine = RarityEngine(bundle)
    c = gen.generate(1)[0]
    # On force artificiellement la combinaison or + roi (règle légendaire).
    c.fur = next(f for f in bundle.fur_colors if f["key"] == "gold")
    c.style = next(s for s in bundle.styles if s["key"] == "king")
    engine.assign(c)
    assert c.rarity["key"] == "legendary"


def test_stats_percentages(bundle: ConfigBundle):
    """Le résumé statistique doit produire des pourcentages cohérents."""
    chars = _chars(bundle, 50)
    meta_gen = MetadataGenerator(bundle)
    stats = meta_gen.build_stats(chars)
    assert stats["total"] == 50
    fur_dist = stats["traits"]["Pelage"]
    total_percent = sum(v["percent"] for v in fur_dist.values())
    assert abs(total_percent - 100.0) < 1.0
