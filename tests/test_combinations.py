"""Tests du moteur de combinaisons : unicité, identifiants, reproductibilité,
règles interdites, et règle de l'objet unique.
"""
from src.combination_generator import (
    CombinationGenerator,
    ConfigBundle,
    is_forbidden,
)


def test_nine_fur_colors(bundle: ConfigBundle):
    """La collection doit définir EXACTEMENT 9 couleurs de pelage."""
    assert len(bundle.fur_colors) == 9
    keys = {f["key"] for f in bundle.fur_colors}
    expected = {
        "white", "blue_ice", "black", "green", "mauve",
        "gray", "gold", "red", "light_brown",
    }
    assert keys == expected


def test_unique_ids(bundle: ConfigBundle):
    """Tous les identifiants générés doivent être uniques et séquentiels."""
    gen = CombinationGenerator(bundle)
    chars = gen.generate(50)
    ids = [c.id for c in chars]
    assert len(ids) == len(set(ids))
    assert ids == [f"{i:04d}" for i in range(1, 51)]


def test_no_duplicate_combinations(bundle: ConfigBundle):
    """Aucune combinaison ne doit apparaître deux fois."""
    gen = CombinationGenerator(bundle)
    chars = gen.generate(200)
    combos = [c.combo_key for c in chars]
    assert len(combos) == len(set(combos))


def test_single_object_maximum(bundle: ConfigBundle):
    """Chaque personnage tient au maximum UN seul objet."""
    gen = CombinationGenerator(bundle)
    for c in gen.generate(100):
        # obj est toujours un dictionnaire unique (un seul objet).
        assert isinstance(c.obj, dict)
        assert "key" in c.obj


def test_object_matches_style(bundle: ConfigBundle):
    """L'objet tenu doit appartenir à la liste d'objets du style."""
    gen = CombinationGenerator(bundle)
    styles_by_key = {s["key"]: s for s in bundle.styles}
    for c in gen.generate(150):
        style = styles_by_key[c.style["key"]]
        valid = {o["key"] for o in (style.get("objects") or [])}
        if c.obj["key"] == "none":
            assert not style.get("objects")
        else:
            assert c.obj["key"] in valid


def test_reproducible_with_seed(bundle: ConfigBundle):
    """La même seed produit exactement la même collection."""
    gen1 = CombinationGenerator(bundle)
    gen2 = CombinationGenerator(bundle)
    a = gen1.generate(30)
    b = gen2.generate(30)
    assert [c.combo_key for c in a] == [c.combo_key for c in b]
    assert [c.seed for c in a] == [c.seed for c in b]


def test_forbidden_combinations_respected(bundle: ConfigBundle):
    """Aucune combinaison interdite ne doit apparaître dans la sortie."""
    gen = CombinationGenerator(bundle)
    chars = gen.generate(300)
    for c in chars:
        assert not is_forbidden(c.trait_dict(), bundle.forbidden)


def test_forbidden_rule_detection(bundle: ConfigBundle):
    """La fonction is_forbidden détecte bien une règle ciblée."""
    rules = [{"match": {"fur": "black", "eyes": "glossy_black"}}]
    assert is_forbidden({"fur": "black", "eyes": "glossy_black", "style": "x", "object": "y"}, rules)
    assert not is_forbidden({"fur": "white", "eyes": "sky_blue", "style": "x", "object": "y"}, rules)


def test_max_unique_guard(bundle: ConfigBundle):
    """Demander plus que le maximum théorique doit lever une erreur claire."""
    gen = CombinationGenerator(bundle)
    too_many = gen.max_unique_combinations() + 1
    import pytest

    with pytest.raises(ValueError):
        gen.generate(too_many)
