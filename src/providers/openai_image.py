"""OpenAI image-generation provider (gpt-image-1 / DALL-E).

Uses a dependency-free HTTP call (``urllib``) so it works without the ``openai``
package installed. Requires ``OPENAI_API_KEY``. The model can be overridden with
``OPENAI_IMAGE_MODEL`` (default: ``gpt-image-1``); if that model is unavailable
the provider automatically falls back to ``dall-e-3``.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request

from .base import ProviderError

_API_URL = "https://api.openai.com/v1/images/generations"


class OpenAIImageProvider:
    name = "openai"

    def __init__(self) -> None:
        self._api_key = os.environ.get("OPENAI_API_KEY")
        if not self._api_key:
            raise ProviderError(
                "OPENAI_API_KEY is not set. Export it before using --real."
            )
        self._model = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")

    def _post(self, body: dict) -> dict:
        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            _API_URL,
            data=payload,
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
            raise ProviderError(f"OpenAI image request failed (HTTP {exc.code}): {detail}")
        except urllib.error.URLError as exc:
            raise ProviderError(f"OpenAI image request failed: {exc.reason}")

    def generate_image(self, prompt: str, size: str = "1024x1024") -> bytes:
        """Return PNG bytes for ``prompt`` rendered at ``size``."""
        body = {"model": self._model, "prompt": prompt, "n": 1, "size": size}

        try:
            data = self._post(body)
        except ProviderError:
            # Fall back to dall-e-3 if the primary model is unavailable.
            if self._model != "dall-e-3":
                self._model = "dall-e-3"
                body["model"] = "dall-e-3"
                body["response_format"] = "b64_json"
                data = self._post(body)
            else:
                raise

        try:
            item = data["data"][0]
            b64 = item["b64_json"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"Unexpected image response shape: {data}") from exc

        return base64.b64decode(b64)
