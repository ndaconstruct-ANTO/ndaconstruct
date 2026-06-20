"""Tests des prompts : stabilité du prompt de base et verrouillage des règles."""
from src.combination_generator import CombinationGenerator, ConfigBundle
from src.prompt_builder import PromptBuilder


def test_base_prompt_stable(bundle: ConfigBundle):
    """L'empreinte du prompt de base doit être identique d'un build à l'autre."""
    b1 = PromptBuilder(bundle)
    b2 = PromptBuilder(bundle)
    assert b1.base_prompt_signature() == b2.base_prompt_signature()


def test_locked_rules_present_in_every_prompt(bundle: ConfigBundle):
    """Chaque prompt doit contenir les règles verrouillées (queue, mains, objet)."""
    gen = CombinationGenerator(bundle)
    builder = PromptBuilder(bundle)
    for c in gen.generate(40):
        p = builder.build(c)
        pos = p.positive.lower()
        neg = p.negative.lower()
        # Format carré verrouillé.
        assert "1:1" in p.positive
        # Règle de l'objet unique.
        assert "at most one" in pos
        # Interdits dans le négatif.
        assert "human hands" in neg
        assert "tail" in neg
        assert "brand logo" in neg


def test_variable_fields_injected(bundle: ConfigBundle):
    """Les traits variables doivent apparaître dans le prompt positif."""
    gen = CombinationGenerator(bundle)
    builder = PromptBuilder(bundle)
    c = gen.generate(1)[0]
    p = builder.build(c)
    assert c.fur["prompt"] in p.positive
    assert c.eyes["prompt"] in p.positive
    assert c.style["outfit_prompt"] in p.positive


def test_no_unresolved_placeholders(bundle: ConfigBundle):
    """Aucun marqueur {champ} ne doit subsister dans le prompt final."""
    gen = CombinationGenerator(bundle)
    builder = PromptBuilder(bundle)
    for c in gen.generate(20):
        p = builder.build(c)
        # Les marqueurs injectables ne doivent plus exister.
        for field in ("{fur}", "{eyes}", "{style}", "{object}", "{headwear}", "{shoes}", "{background}"):
            assert field not in p.positive


def test_background_locked_consistent(bundle: ConfigBundle):
    """Le fond doit être identique sur toutes les images (collection cohérente)."""
    gen = CombinationGenerator(bundle)
    builder = PromptBuilder(bundle)
    bg = builder.background_prompt
    for c in gen.generate(15):
        p = builder.build(c)
        assert bg in p.positive
