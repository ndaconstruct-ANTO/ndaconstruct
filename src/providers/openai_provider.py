"""OpenAI-backed NDA generation provider.

Prefers the official ``openai`` Python SDK (>= 1.0) when installed, and falls
back to a dependency-free HTTP call (``urllib``) when it is not. Either way it
requires the ``OPENAI_API_KEY`` environment variable. The model can be
overridden with the ``OPENAI_MODEL`` environment variable.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from ..models import NDARequest
from .base import Provider, ProviderError

_SYSTEM_PROMPT = (
    "You are a legal drafting assistant. You write clear, well-structured "
    "Non-Disclosure Agreements (NDAs). Return only the agreement text, with "
    "numbered sections and signature blocks. Do not add commentary."
)

_API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self) -> None:
        self._api_key = os.environ.get("OPENAI_API_KEY")
        if not self._api_key:
            raise ProviderError(
                "OPENAI_API_KEY is not set. Export it before using "
                "--provider openai --real, or omit --real to use the mock provider."
            )

        self._model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

        # Use the official SDK if it is available; otherwise fall back to HTTP.
        try:
            from openai import OpenAI

            self._client = OpenAI(api_key=self._api_key)
        except ImportError:
            self._client = None

    def _build_prompt(self, request: NDARequest) -> str:
        agreement_type = "mutual (two-way)" if request.mutual else "one-way (unilateral)"
        return (
            f"Draft a {agreement_type} Non-Disclosure Agreement with these terms:\n"
            f"- Disclosing party: {request.disclosing_party}\n"
            f"- Receiving party: {request.receiving_party}\n"
            f"- Effective date: {request.effective_date:%B %d, %Y}\n"
            f"- Term: {request.term_years} year(s)\n"
            f"- Governing law: {request.jurisdiction}\n"
            f"- Purpose: {request.purpose}\n\n"
            "Include sections for definition of Confidential Information, obligations, "
            "exclusions, term and survival, return of materials, governing law, and "
            "signature blocks."
        )

    def _messages(self, request: NDARequest) -> list[dict]:
        return [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": self._build_prompt(request)},
        ]

    def _generate_via_sdk(self, request: NDARequest) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=self._messages(request),
            temperature=0.7,
        )
        content = response.choices[0].message.content
        if not content:
            raise ProviderError("OpenAI returned an empty response.")
        return content.strip() + "\n"

    def _generate_via_http(self, request: NDARequest) -> str:
        payload = json.dumps(
            {
                "model": self._model,
                "messages": self._messages(request),
                "temperature": 0.7,
            }
        ).encode("utf-8")

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
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise ProviderError(
                f"OpenAI request failed (HTTP {exc.code}): {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"OpenAI request failed: {exc.reason}") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"Unexpected OpenAI response shape: {data}") from exc

        if not content:
            raise ProviderError("OpenAI returned an empty response.")
        return content.strip() + "\n"

    def generate(self, request: NDARequest) -> str:
        try:
            if self._client is not None:
                return self._generate_via_sdk(request)
            return self._generate_via_http(request)
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 - surface any SDK error cleanly
            raise ProviderError(f"OpenAI request failed: {exc}") from exc
