"""Fournisseurs d'images, isolés du reste du code.

Interface générique permettant de brancher plus tard différents moteurs :
OpenAI, Stable Diffusion, Flux, ComfyUI, une API externe ou un modèle local.

Le fournisseur par défaut est la SIMULATION : il ne génère aucune image et
n'engage aucune dépense ; il sert à valider toute la chaîne (combinaisons,
prompts, métadonnées, doublons, rareté, rapports).
"""

from __future__ import annotations

import abc
import base64
import json
import os
import urllib.error
import urllib.request


class ImageProviderError(RuntimeError):
    """Erreur générique d'un fournisseur d'images."""


class ImageProvider(abc.ABC):
    name = "base"
    is_real = False

    @abc.abstractmethod
    def generate(self, positive: str, negative: str, *, size: str, seed: int) -> bytes | None:
        """Retourne les octets PNG de l'image, ou None en simulation."""
        raise NotImplementedError


class SimulationProvider(ImageProvider):
    """Mode test : ne contacte aucune API, ne crée aucune image réelle."""

    name = "simulation"
    is_real = False

    def generate(self, positive, negative, *, size, seed):
        return None


class OpenAIImageProvider(ImageProvider):
    """Génération réelle via l'API d'images OpenAI (sans dépendance externe)."""

    name = "openai"
    is_real = True
    _API_URL = "https://api.openai.com/v1/images/generations"

    def __init__(self) -> None:
        self._api_key = os.environ.get("OPENAI_API_KEY")
        if not self._api_key:
            raise ImageProviderError(
                "OPENAI_API_KEY absente. Renseignez-la dans .env pour la génération réelle."
            )
        self._model = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")

    def _post(self, body: dict) -> dict:
        req = urllib.request.Request(
            self._API_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise ImageProviderError(f"OpenAI (HTTP {exc.code}): {detail}")
        except urllib.error.URLError as exc:
            raise ImageProviderError(f"OpenAI: {exc.reason}")

    def generate(self, positive, negative, *, size, seed):
        # L'API image d'OpenAI ne prend pas de prompt négatif séparé : on l'intègre.
        prompt = positive
        if negative:
            prompt += "\n\nStrictly avoid: " + negative
        body = {"model": self._model, "prompt": prompt, "n": 1, "size": size}
        try:
            data = self._post(body)
        except ImageProviderError:
            if self._model != "dall-e-3":
                self._model = "dall-e-3"
                body["model"] = "dall-e-3"
                body["response_format"] = "b64_json"
                data = self._post(body)
            else:
                raise
        try:
            return base64.b64decode(data["data"][0]["b64_json"])
        except (KeyError, IndexError) as exc:
            raise ImageProviderError(f"Réponse OpenAI inattendue: {data}") from exc


_PROVIDERS = {
    "simulation": SimulationProvider,
    "openai": OpenAIImageProvider,
}


def get_provider(name: str, *, real: bool) -> ImageProvider:
    """Retourne un fournisseur. En l'absence de ``real``, toujours la simulation."""
    if not real:
        return SimulationProvider()
    if name not in _PROVIDERS:
        raise ImageProviderError(
            f"Fournisseur inconnu '{name}'. Disponibles : {', '.join(_PROVIDERS)}"
        )
    return _PROVIDERS[name]()
