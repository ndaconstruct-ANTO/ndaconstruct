"""Tests du fournisseur OpenAI — l'API est entièrement simulée (aucune dépense).

On injecte un faux module `openai` dans sys.modules pour vérifier que le
fournisseur construit la bonne requête, écrit un PNG à la bonne résolution et
produit un GenerationResult non simulé. Aucun appel réseau réel n'est effectué.
"""
import base64
import io
import sys
import types

import pytest

from src.combination_generator import CombinationGenerator, ConfigBundle
from src.image_provider import OpenAIProvider, get_provider
from src.prompt_builder import PromptBuilder
from src.quality_control import QualityControl, STATUS_REJECTED


def _tiny_png_b64() -> str:
    """Génère un petit PNG 8x8 valide encodé en base64 (via Pillow)."""
    from PIL import Image

    img = Image.new("RGB", (8, 8), (200, 180, 120))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


class _FakeImages:
    def __init__(self, recorder):
        self._recorder = recorder

    def generate(self, **kwargs):
        self._recorder.update(kwargs)
        payload = types.SimpleNamespace(b64_json=_tiny_png_b64())
        return types.SimpleNamespace(data=[payload])


class _FakeOpenAI:
    last_kwargs: dict = {}

    def __init__(self, api_key=None):
        self.api_key = api_key
        self.images = _FakeImages(_FakeOpenAI.last_kwargs)


@pytest.fixture
def fake_openai(monkeypatch):
    """Installe un faux module openai exposant la classe OpenAI."""
    _FakeOpenAI.last_kwargs = {}
    fake_module = types.ModuleType("openai")
    fake_module.OpenAI = _FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_module)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    return _FakeOpenAI


def test_get_provider_returns_openai(bundle: ConfigBundle):
    """Sans test_mode, le fournisseur openai est bien instancié."""
    provider = get_provider("openai", bundle.collection, "output/images", test_mode=False)
    assert isinstance(provider, OpenAIProvider)


def test_test_mode_blocks_real_provider(bundle: ConfigBundle):
    """En test_mode, openai est remplacé par la simulation (aucune dépense)."""
    provider = get_provider("openai", bundle.collection, "output/images", test_mode=True)
    assert provider.name == "simulation"


def test_pick_size_square(bundle: ConfigBundle):
    provider = OpenAIProvider({}, "output/images")
    gen = CombinationGenerator(bundle)
    p = PromptBuilder(bundle).build(gen.generate(1)[0])
    assert provider._pick_size(p) == "1024x1024"


def test_compose_prompt_folds_negative(bundle: ConfigBundle):
    provider = OpenAIProvider({}, "output/images")
    gen = CombinationGenerator(bundle)
    p = PromptBuilder(bundle).build(gen.generate(1)[0])
    composed = provider._compose_prompt(p)
    assert "Strictly avoid" in composed
    assert "human hands" in composed.lower()


def test_generate_writes_png(bundle: ConfigBundle, fake_openai, tmp_path):
    """Le fournisseur écrit un PNG à la résolution cible, sans appel réel."""
    pytest.importorskip("PIL")  # ce test nécessite Pillow
    gen = CombinationGenerator(bundle)
    char = gen.generate(1)[0]
    prompt = PromptBuilder(bundle).build(char)

    provider = OpenAIProvider(
        {"model": "gpt-image-1", "quality": "high", "upscale_to_target": True,
         "api_key_env": "OPENAI_API_KEY"},
        str(tmp_path),
    )
    result = provider.generate(prompt, filename="0001.png")

    assert result.simulated is False
    assert result.error is None
    assert result.provider == "openai"
    out = tmp_path / "0001.png"
    assert out.exists()

    # La requête envoyée à l'API utilise une taille supportée par gpt-image-1.
    assert fake_openai.last_kwargs["size"] in {"1024x1024", "1536x1024", "1024x1536", "auto"}
    assert fake_openai.last_kwargs["n"] == 1

    # Le PNG produit est carré et à la résolution configurée.
    from PIL import Image

    with Image.open(out) as img:
        assert img.size == (prompt.width, prompt.height)
        assert img.size[0] == img.size[1]

    # Le contrôle qualité accepte une image réelle conforme.
    qc = QualityControl(bundle).check(char, prompt, result)
    assert qc.status != STATUS_REJECTED, qc.errors


def test_generate_handles_api_error(bundle: ConfigBundle, monkeypatch, tmp_path):
    """Une erreur API est capturée proprement (pas de crash, error renseignée)."""
    class _BoomImages:
        def generate(self, **kwargs):
            raise RuntimeError("boom")

    class _BoomOpenAI:
        def __init__(self, api_key=None):
            self.images = _BoomImages()

    fake_module = types.ModuleType("openai")
    fake_module.OpenAI = _BoomOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_module)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")

    gen = CombinationGenerator(bundle)
    char = gen.generate(1)[0]
    prompt = PromptBuilder(bundle).build(char)
    provider = OpenAIProvider({"api_key_env": "OPENAI_API_KEY"}, str(tmp_path))
    result = provider.generate(prompt, filename="0001.png")
    assert result.image_path is None
    assert result.error is not None and "boom" in result.error


def test_missing_api_key_raises(bundle: ConfigBundle, monkeypatch, tmp_path):
    """Sans clé API, le fournisseur refuse clairement (aucune dépense possible)."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    gen = CombinationGenerator(bundle)
    char = gen.generate(1)[0]
    prompt = PromptBuilder(bundle).build(char)
    provider = OpenAIProvider({"api_key_env": "OPENAI_API_KEY"}, str(tmp_path))
    with pytest.raises(RuntimeError):
        provider.generate(prompt, filename="0001.png")
