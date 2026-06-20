"""LLM providers for NDA generation."""

from .base import Provider, ProviderError
from .mock import MockProvider
from .openai_provider import OpenAIProvider

#: Registry mapping provider names to their implementations.
PROVIDERS = {
    "openai": OpenAIProvider,
    "mock": MockProvider,
}


def get_provider(name: str, *, real: bool):
    """Return a provider instance for ``name``.

    When ``real`` is False we always fall back to :class:`MockProvider`, so no
    API calls are made and no credentials are required. This makes it safe to
    run the tool without ``--real`` for testing.
    """
    if not real:
        return MockProvider()

    try:
        provider_cls = PROVIDERS[name]
    except KeyError:
        available = ", ".join(sorted(PROVIDERS))
        raise ProviderError(f"Unknown provider '{name}'. Available: {available}")

    return provider_cls()


__all__ = [
    "Provider",
    "ProviderError",
    "MockProvider",
    "OpenAIProvider",
    "PROVIDERS",
    "get_provider",
]
