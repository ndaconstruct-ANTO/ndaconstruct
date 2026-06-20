"""Tests du contrôle qualité et du pipeline complet en mode simulation."""
from src.combination_generator import CombinationGenerator, ConfigBundle
from src.prompt_builder import PromptBuilder
from src.quality_control import QualityControl, STATUS_REJECTED
from src.rarity_engine import RarityEngine
from src.main import PipelineOptions, run_pipeline


def test_quality_control_passes_logical_checks(bundle: ConfigBundle):
    """En simulation, aucun personnage ne doit être REFUSÉ (erreurs logiques)."""
    gen = CombinationGenerator(bundle)
    builder = PromptBuilder(bundle)
    qc = QualityControl(bundle)
    chars = gen.generate(40)
    RarityEngine(bundle).assign_all(chars)
    for c in chars:
        p = builder.build(c)
        result = qc.check(c, p, None)
        assert result.status != STATUS_REJECTED, result.errors


def test_quality_control_rejects_bad_object(bundle: ConfigBundle):
    """Un objet incohérent avec le style doit être REFUSÉ."""
    gen = CombinationGenerator(bundle)
    builder = PromptBuilder(bundle)
    qc = QualityControl(bundle)
    c = gen.generate(1)[0]
    # On injecte un objet qui n'appartient pas au style.
    c.obj = {"key": "fake_object", "name": "Faux", "prompt": "holding a fake object"}
    p = builder.build(c)
    result = qc.check(c, p, None)
    assert result.status == STATUS_REJECTED


def test_pipeline_simulation_no_images(bundle: ConfigBundle):
    """Le pipeline simulation ne produit aucune image réelle."""
    options = PipelineOptions(count=10, write_outputs=False)
    result = run_pipeline(options)
    assert result.provider_name == "simulation"
    assert len(result.characters) == 10
    assert len(result.prompts) == 10
    assert all(r.simulated for r in result.results)
    assert all(r.image_path is None for r in result.results)


def test_pipeline_test_mode_forces_simulation(bundle: ConfigBundle):
    """Même en demandant un fournisseur réel, le mode test force la simulation."""
    options = PipelineOptions(count=3, provider="openai", test_mode=True, write_outputs=False)
    result = run_pipeline(options)
    assert result.provider_name == "simulation"
