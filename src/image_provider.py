"""Fournisseurs d'images — interface générique et implémentations.

Le reste du code ne connaît QUE l'interface `ImageProvider`. On peut donc
brancher plus tard OpenAI, Stable Diffusion, Flux, ComfyUI, une API externe ou
un modèle local sans rien changer ailleurs.

Le fournisseur par défaut est `SimulationProvider` : il ne contacte aucune API,
ne dépense rien, et se contente de décrire ce qui SERAIT envoyé. Aucune
génération payante ne peut donc avoir lieu tant que ce mode est actif.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

from . import utils
from .prompt_builder import BuiltPrompt


@dataclass
class GenerationResult:
    """Résultat d'une demande de génération d'image."""

    id: str
    image_path: Optional[str]      # chemin du PNG si une image a été produite
    simulated: bool                # True si aucune image réelle n'a été créée
    provider: str
    request: Dict[str, Any]        # ce qui (aurait été) envoyé au fournisseur
    width: int
    height: int
    error: Optional[str] = None


class ImageProvider(ABC):
    """Interface commune à tous les fournisseurs d'images."""

    name = "abstract"

    def __init__(self, config: Dict[str, Any], output_dir: str):
        self.config = config
        self.output_dir = output_dir

    @abstractmethod
    def generate(self, prompt: BuiltPrompt, *, filename: str) -> GenerationResult:
        """Produit (ou simule) une image carrée pour le prompt donné."""

    # Outil commun : construit la charge utile envoyée au fournisseur.
    def build_request(self, prompt: BuiltPrompt) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "id": prompt.id,
            "prompt": prompt.positive,
            "negative_prompt": prompt.negative,
            "width": prompt.width,
            "height": prompt.height,
            "seed": prompt.seed,
        }


class SimulationProvider(ImageProvider):
    """Mode simulation : aucune image générée, aucune dépense, aucune API."""

    name = "simulation"

    def generate(self, prompt: BuiltPrompt, *, filename: str) -> GenerationResult:
        request = self.build_request(prompt)
        return GenerationResult(
            id=prompt.id,
            image_path=None,
            simulated=True,
            provider=self.name,
            request=request,
            width=prompt.width,
            height=prompt.height,
        )


class _RealProviderBase(ImageProvider):
    """Base commune aux fournisseurs réels : vérifie la clé API, refuse si absente.

    Les appels réseau ne sont volontairement PAS implémentés ici : ils seront
    ajoutés au moment où vous activerez explicitement un fournisseur payant.
    Tant que ce n'est pas fait, ces fournisseurs lèvent une erreur claire au
    lieu de dépenser quoi que ce soit par accident.
    """

    def _require_env(self, env_name: Optional[str]) -> str:
        if not env_name:
            return ""
        value = os.environ.get(env_name, "")
        if not value:
            raise RuntimeError(
                f"[{self.name}] Variable d'environnement '{env_name}' absente. "
                f"Renseignez-la (voir .env.example) avant d'activer ce fournisseur."
            )
        return value

    def generate(self, prompt: BuiltPrompt, *, filename: str) -> GenerationResult:
        raise NotImplementedError(
            f"[{self.name}] Le fournisseur réel n'est pas encore branché. "
            f"Restez en mode 'simulation' ou implémentez l'appel API ici. "
            f"Aucune génération payante n'est lancée automatiquement."
        )


class OpenAIProvider(_RealProviderBase):
    name = "openai"

    def generate(self, prompt: BuiltPrompt, *, filename: str) -> GenerationResult:
        self._require_env(self.config.get("api_key_env", "OPENAI_API_KEY"))
        # TODO (activation explicite) : appeler l'API Images d'OpenAI ici,
        # télécharger le PNG dans self.output_dir/filename, puis renvoyer un
        # GenerationResult(simulated=False, image_path=...).
        return super().generate(prompt, filename=filename)


class StableDiffusionProvider(_RealProviderBase):
    name = "stable_diffusion"

    def generate(self, prompt: BuiltPrompt, *, filename: str) -> GenerationResult:
        self._require_env(self.config.get("api_url_env", "SD_API_URL"))
        return super().generate(prompt, filename=filename)


class FluxProvider(_RealProviderBase):
    name = "flux"

    def generate(self, prompt: BuiltPrompt, *, filename: str) -> GenerationResult:
        self._require_env(self.config.get("api_key_env", "FLUX_API_KEY"))
        return super().generate(prompt, filename=filename)


class ComfyUIProvider(_RealProviderBase):
    name = "comfyui"

    def generate(self, prompt: BuiltPrompt, *, filename: str) -> GenerationResult:
        self._require_env(self.config.get("api_url_env", "COMFYUI_API_URL"))
        return super().generate(prompt, filename=filename)


_PROVIDER_CLASSES = {
    "simulation": SimulationProvider,
    "openai": OpenAIProvider,
    "stable_diffusion": StableDiffusionProvider,
    "flux": FluxProvider,
    "comfyui": ComfyUIProvider,
}


def get_provider(
    provider_key: str,
    collection_cfg: Dict[str, Any],
    output_dir: str,
    *,
    test_mode: bool = False,
) -> ImageProvider:
    """Fabrique le fournisseur demandé.

    En mode test, on force toujours la simulation pour éviter toute dépense.
    """
    if test_mode:
        provider_key = "simulation"

    providers_cfg = collection_cfg.get("providers", {})
    if provider_key not in _PROVIDER_CLASSES:
        raise ValueError(
            f"Fournisseur inconnu : '{provider_key}'. "
            f"Disponibles : {', '.join(sorted(_PROVIDER_CLASSES))}."
        )
    cls = _PROVIDER_CLASSES[provider_key]
    cfg = providers_cfg.get(provider_key, {})
    utils.ensure_dir(output_dir)
    return cls(cfg, output_dir)
