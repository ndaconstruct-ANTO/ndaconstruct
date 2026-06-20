"""Provider interface shared by all NDA generation backends."""

from __future__ import annotations

import abc

from ..models import NDARequest


class ProviderError(RuntimeError):
    """Raised when a provider cannot fulfil a generation request."""


class Provider(abc.ABC):
    """Abstract base class for an NDA-generating backend."""

    #: Human readable name, used in logs and output metadata.
    name: str = "base"

    @abc.abstractmethod
    def generate(self, request: NDARequest) -> str:
        """Return the full text of an NDA for ``request``."""
        raise NotImplementedError
