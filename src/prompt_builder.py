"""Construction des prompts à partir du prompt de base verrouillé.

Sépare clairement :
  1. les éléments FIXES (prompt de base, jamais modifiés par un personnage) ;
  2. les éléments VARIABLES (injectés depuis les configs) ;
  3. les éléments INTERDITS (prompt négatif) ;
  4. les paramètres TECHNIQUES (résolution, format).

Aucun trait variable ne peut écraser la morphologie, le cadrage, le fond, la
caméra, le format ou l'éclairage : ces éléments vivent uniquement dans le prompt
de base et ne contiennent aucun champ injectable les concernant.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from . import utils
from .combination_generator import Character, ConfigBundle

# Champs autorisés à être injectés dans le prompt de base.
# Toute autre clé est ignorée -> impossible de modifier la morphologie/cadrage.
_ALLOWED_INJECTION_FIELDS = {
    "fur",
    "eyes",
    "style",
    "object",
    "headwear",
    "shoes",
    "background",
}


_COMMENT_PREFIX = "／／"


def _strip_comments(text: str) -> str:
    """Retire les lignes de commentaire (préfixe ／／) et les blancs superflus."""
    kept = [
        line
        for line in text.splitlines()
        if not line.lstrip().startswith(_COMMENT_PREFIX)
    ]
    return "\n".join(kept).strip()


@dataclass
class BuiltPrompt:
    """Résultat de la construction : ce qui serait envoyé au fournisseur."""

    id: str
    positive: str
    negative: str
    width: int
    height: int
    seed: int
    fields: Dict[str, str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "seed": self.seed,
            "width": self.width,
            "height": self.height,
            "positive_prompt": self.positive,
            "negative_prompt": self.negative,
            "injected_fields": self.fields,
        }


class PromptBuilder:
    def __init__(self, bundle: ConfigBundle):
        self.bundle = bundle
        prompt_files = bundle.collection["prompt_files"]
        # Les lignes de commentaire (préfixe ／／) servent de documentation dans
        # les fichiers et ne doivent PAS être envoyées au modèle d'image.
        self.base_prompt = _strip_comments(utils.load_text(prompt_files["base"]))
        self.negative_prompt = _strip_comments(utils.load_text(prompt_files["negative"]))
        self.image_cfg = bundle.collection["image"]
        self.default_shoes = bundle.default_shoes
        self.common_forbidden = bundle.common_forbidden

        # Fond actif (verrouillé pour toute la collection).
        bg_cfg = bundle.collection.get("background", {})
        active = bg_cfg.get("active", "white")
        presets = bg_cfg.get("presets", {})
        self.background_prompt = presets.get(active, {}).get(
            "prompt", "pure immaculate solid white studio background"
        )

    def _injection_fields(self, character: Character) -> Dict[str, str]:
        """Construit le dictionnaire des champs variables à injecter."""
        style = character.style
        headwear = style.get("headwear")
        shoes = style.get("shoes") or self.default_shoes
        # Yeux : description unique en homochromie, gauche/droite en hétérochromie (§7).
        if character.heterochromia:
            eyes_prompt = (
                f"heterochromia, left eye {character.left_eye['prompt']}, "
                f"right eye {character.right_eye['prompt']}"
            )
        else:
            eyes_prompt = character.eyes["prompt"]
        fields = {
            "fur": character.fur["prompt"],
            "eyes": eyes_prompt,
            "style": style["outfit_prompt"],
            "object": character.obj["prompt"],
            "headwear": headwear if headwear else "no headwear",
            "shoes": shoes,
            "background": self.background_prompt,
        }
        # Sécurité : on ne garde QUE les champs autorisés.
        return {k: v for k, v in fields.items() if k in _ALLOWED_INJECTION_FIELDS}

    def build(self, character: Character) -> BuiltPrompt:
        fields = self._injection_fields(character)

        # Injection sûre : on remplace les marqueurs {champ} un par un.
        positive = self.base_prompt
        for key, value in fields.items():
            positive = positive.replace("{" + key + "}", value)
        positive = positive.strip()

        # Prompt négatif = interdits globaux + interdits propres au style.
        negative_parts: List[str] = [self.negative_prompt]
        style_forbidden = character.style.get("forbidden") or []
        extra_forbidden = list(self.common_forbidden) + list(style_forbidden)
        if extra_forbidden:
            negative_parts.append(", ".join(extra_forbidden))
        negative = ", ".join(p for p in negative_parts if p).strip()

        return BuiltPrompt(
            id=character.id,
            positive=positive,
            negative=negative,
            width=int(self.image_cfg["width"]),
            height=int(self.image_cfg["height"]),
            seed=character.seed,
            fields=fields,
        )

    def base_prompt_signature(self) -> str:
        """Empreinte stable du prompt de base (pour les tests de stabilité)."""
        return utils.stable_hash(self.base_prompt, self.negative_prompt)
