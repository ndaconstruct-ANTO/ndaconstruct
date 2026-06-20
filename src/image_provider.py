"""Fournisseurs d'images — interface générique et implémentations.

Le reste du code ne connaît QUE l'interface `ImageProvider`. On peut donc
brancher plus tard OpenAI, Stable Diffusion, Flux, ComfyUI, une API externe ou
un modèle local sans rien changer ailleurs.

Le fournisseur par défaut est `SimulationProvider` : il ne contacte aucune API,
ne dépense rien, et se contente de décrire ce qui SERAIT envoyé. Aucune
génération payante ne peut donc avoir lieu tant que ce mode est actif.
"""
from __future__ import annotations

import base64
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from . import utils
from .prompt_builder import BuiltPrompt


def _save_png(image_bytes: bytes, out_path: Path, target_size: Optional[Tuple[int, int]]) -> None:
    """Écrit les octets d'image en PNG, en agrandissant à `target_size` si demandé.

    L'agrandissement nécessite Pillow. S'il est absent, on écrit l'image telle
    quelle (taille native du modèle) sans bloquer la génération.
    """
    if target_size is not None:
        try:
            import io

            from PIL import Image

            with Image.open(io.BytesIO(image_bytes)) as img:
                img = img.convert("RGBA") if img.mode in ("P", "LA") else img.convert("RGB")
                if img.size != target_size:
                    img = img.resize(target_size, Image.LANCZOS)
                img.save(out_path, format="PNG")
            return
        except ImportError:
            # Pillow absent : on retombe sur l'écriture brute ci-dessous.
            pass
    with open(out_path, "wb") as fh:
        fh.write(image_bytes)


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
    """Fournisseur OpenAI Images (modèle gpt-image-1).

    Particularités de gpt-image-1 prises en compte ici :
      - tailles supportées : 1024x1024, 1536x1024, 1024x1536, "auto".
        Il n'existe PAS de 2048 natif : on demande la taille carrée supportée la
        plus proche (1024x1024 par défaut), puis on agrandit éventuellement
        jusqu'à la résolution demandée si Pillow est installé (option upscale).
      - pas de paramètre "negative_prompt" : les interdits sont repliés dans le
        texte du prompt sous forme d'une consigne « Strictly avoid: ... ».
      - pas de paramètre "seed" : la reproductibilité côté image n'est pas
        garantie par l'API ; la seed reste enregistrée dans les métadonnées.
      - la réponse est toujours encodée en base64 (b64_json).
    """

    name = "openai"

    # Tailles carrées réellement supportées par gpt-image-1.
    _SUPPORTED_SQUARE = "1024x1024"
    _SUPPORTED_LANDSCAPE = "1536x1024"
    _SUPPORTED_PORTRAIT = "1024x1536"

    def _pick_size(self, prompt: BuiltPrompt) -> str:
        """Choisit une taille supportée selon le ratio demandé (carré par défaut)."""
        configured = self.config.get("size")
        if configured and configured != "auto":
            return configured
        if prompt.width == prompt.height:
            return self._SUPPORTED_SQUARE
        if prompt.width > prompt.height:
            return self._SUPPORTED_LANDSCAPE
        return self._SUPPORTED_PORTRAIT

    @staticmethod
    def _compose_prompt(prompt: BuiltPrompt) -> str:
        """Replie le prompt négatif dans le prompt positif (pas de champ dédié)."""
        text = prompt.positive
        if prompt.negative:
            text = (
                f"{prompt.positive}\n\n"
                f"Strictly avoid and never include the following: {prompt.negative}"
            )
        return text

    # Point de terminaison REST utilisé en l'absence du SDK officiel.
    _API_URL = "https://api.openai.com/v1/images/generations"

    @staticmethod
    def _call_openai(*, api_key: str, model: str, prompt: str, size: str, quality: str) -> str:
        """Appelle l'API Images d'OpenAI et renvoie l'image encodée en base64.

        Utilise le SDK officiel `openai` s'il est installé ; sinon, retombe sur
        un appel HTTP direct (urllib, sans dépendance externe) vers l'API REST.
        Les deux chemins renvoient la chaîne base64 (`b64_json`) de l'image.
        """
        try:
            from openai import OpenAI  # SDK officiel si disponible
        except ImportError:
            return OpenAIProvider._call_openai_http(
                api_key=api_key, model=model, prompt=prompt, size=size, quality=quality
            )
        client = OpenAI(api_key=api_key)
        response = client.images.generate(
            model=model, prompt=prompt, size=size, quality=quality, n=1
        )
        return response.data[0].b64_json

    @staticmethod
    def _call_openai_http(*, api_key: str, model: str, prompt: str, size: str, quality: str) -> str:
        """Appel HTTP direct à l'API Images (repli quand le SDK est absent)."""
        import json
        import urllib.error
        import urllib.request

        payload = json.dumps(
            {"model": model, "prompt": prompt, "size": size, "quality": quality, "n": 1}
        ).encode("utf-8")
        req = urllib.request.Request(
            OpenAIProvider._API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:  # message d'erreur lisible côté API
            detail = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"HTTP {exc.code} : {detail}") from exc
        return body["data"][0]["b64_json"]

    def generate(self, prompt: BuiltPrompt, *, filename: str) -> GenerationResult:
        api_key = self._require_env(self.config.get("api_key_env", "OPENAI_API_KEY"))
        request = self.build_request(prompt)
        size = self._pick_size(prompt)
        request["openai_size"] = size
        request["note"] = (
            "gpt-image-1 ne gère ni seed ni negative_prompt ; négatif replié dans le texte."
        )

        model = self.config.get("model", "gpt-image-1")
        quality = self.config.get("quality", "high")

        try:
            image_b64 = self._call_openai(
                api_key=api_key,
                model=model,
                prompt=self._compose_prompt(prompt),
                size=size,
                quality=quality,
            )
        except Exception as exc:  # pragma: no cover - dépend du réseau/API
            return GenerationResult(
                id=prompt.id,
                image_path=None,
                simulated=False,
                provider=self.name,
                request=request,
                width=prompt.width,
                height=prompt.height,
                error=f"Échec de l'appel OpenAI : {exc}",
            )

        image_bytes = base64.b64decode(image_b64)

        target_size = (prompt.width, prompt.height)
        out_path = Path(self.output_dir) / filename
        out_path.parent.mkdir(parents=True, exist_ok=True)
        upscale = bool(self.config.get("upscale_to_target", True))
        _save_png(image_bytes, out_path, target_size if upscale else None)

        return GenerationResult(
            id=prompt.id,
            image_path=str(out_path),
            simulated=False,
            provider=self.name,
            request=request,
            width=prompt.width,
            height=prompt.height,
        )


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
