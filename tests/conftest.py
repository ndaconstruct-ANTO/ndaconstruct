"""Configuration commune des tests : rend le paquet `src` importable."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.combination_generator import ConfigBundle  # noqa: E402


@pytest.fixture(scope="session")
def bundle() -> ConfigBundle:
    """Configuration chargée une seule fois pour toute la session de test."""
    return ConfigBundle.load("config/collection.yaml")
