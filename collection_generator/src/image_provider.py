"""Fournisseurs d'images, isolés du reste du code.

Interface générique permettant de brancher plus tard différents moteurs :
OpenAI, Stable Diffusion, Flux, ComfyUI, une API externe ou un modèle local.

Le fournisseur par défaut est la SIMULATION : il ne génère aucune image et
n'engage aucune dépense.

Le fournisseur OpenAI sait fonctionner de DEUX façons :
  - sans image de référence : génération texte->image (/v1/images/generations) ;
  - AVEC une image maître de référence : édition basée référence
    (/v1/images/edits) pour conserver exactement le même lionceau.
"""

from __future__ import annotations

import abc
import base64
import json
import os
import urllib.error
import urllib.request
import uuid


class ImageProviderError(RuntimeError):
    """Erreur générique d'un fournisseur d'images."""


class ImageProvider(abc.ABC):
    name = "base"
    is_real = False

    @abc.abstractmethod
    def generate(self, positive: str, negative: str, *, size: str, seed: int,
                 reference: bytes | None = None) -> bytes | None:
        """Retourne les octets PNG de l'image, ou None en simulation."""
        raise NotImplementedError


class SimulationProvider(ImageProvider):
    """Mode test : ne contacte aucune API, ne crée aucune image réelle."""

    name = "simulation"
    is_real = False

    def generate(self, positive, negative, *, size, seed, reference=None):
        return None


class OpenAIImageProvider(ImageProvider):
    """Génération réelle via l'API d'images OpenAI (sans dépendance externe)."""

    name = "openai"
    is_real = True
    _GEN_URL = "https://api.openai.com/v1/images/generations"
    _EDIT_URL = "https://api.openai.com/v1/images/edits"

    def __init__(self) -> None:
        self._api_key = os.environ.get("OPENAI_API_KEY")
        if not self._api_key:
            raise ImageProviderError(
                "OPENAI_API_KEY absente. Renseignez-la dans .env pour la génération réelle."
            )
        self._model = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")

    # -- HTTP : JSON (generations) -------------------------------------------
    def _post_json(self, url: str, body: dict) -> dict:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        return self._send(req)

    # -- HTTP : multipart (edits, avec image de référence) -------------------
    def _post_multipart(self, url: str, fields: dict, files: dict) -> dict:
        boundary = "----lionceaux" + uuid.uuid4().hex
        body = bytearray()
        for name, value in fields.items():
            body += f"--{boundary}\r\n".encode()
            body += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
            body += f"{value}\r\n".encode()
        for name, (filename, content) in files.items():
            body += f"--{boundary}\r\n".encode()
            body += (
                f'Content-Disposition: form-data; name="{name}"; '
                f'filename="{filename}"\r\n'.encode()
            )
            body += b"Content-Type: image/png\r\n\r\n"
            body += content
            body += b"\r\n"
        body += f"--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            url,
            data=bytes(body),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        return self._send(req)

    def _send(self, req) -> dict:
        try:
            with urllib.request.urlopen(req, timeout=240) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise ImageProviderError(f"OpenAI (HTTP {exc.code}): {detail}")
        except urllib.error.URLError as exc:
            raise ImageProviderError(f"OpenAI: {exc.reason}")

    @staticmethod
    def _decode(data: dict) -> bytes:
        try:
            return base64.b64decode(data["data"][0]["b64_json"])
        except (KeyError, IndexError) as exc:
            raise ImageProviderError(f"Réponse OpenAI inattendue: {data}") from exc

    # -- API ------------------------------------------------------------------
    def generate(self, positive, negative, *, size, seed, reference=None):
        prompt = positive
        if negative:
            prompt += "\n\nStrictly avoid: " + negative

        if reference:
            # Édition basée référence : conserve le même lionceau maître.
            data = self._post_multipart(
                self._EDIT_URL,
                fields={"model": self._model, "prompt": prompt, "size": size, "n": "1"},
                files={"image": ("master_lion.png", reference)},
            )
            return self._decode(data)

        # Sinon : génération texte -> image, avec repli dall-e-3.
        body = {"model": self._model, "prompt": prompt, "n": 1, "size": size}
        try:
            data = self._post_json(self._GEN_URL, body)
        except ImageProviderError:
            if self._model != "dall-e-3":
                self._model = "dall-e-3"
                body["model"] = "dall-e-3"
                body["response_format"] = "b64_json"
                data = self._post_json(self._GEN_URL, body)
            else:
                raise
        return self._decode(data)


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
