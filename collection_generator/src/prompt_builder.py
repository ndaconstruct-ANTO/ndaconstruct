"""Construction des prompts à partir du prompt maître verrouillé.

Sépare strictement :
  - les éléments FIXES (prompt de base, non modifiable par combinaison) ;
  - les éléments VARIABLES (injectés via les emplacements [VARIABLE]) ;
  - le prompt NÉGATIF officiel.
"""

from __future__ import annotations

from pathlib import Path

from .combination_generator import Combination
from .utils import PROMPTS_DIR, Config, read_text


class PromptBuilder:
    def __init__(self, config: Config, prompts_dir: Path = PROMPTS_DIR) -> None:
        self.config = config
        self.prompts_dir = Path(prompts_dir)
        self.base_prompt = read_text(self.prompts_dir / "base_prompt.txt").strip()
        self.negative_prompt = read_text(
            self.prompts_dir / "negative_prompt.txt"
        ).strip()
        self._template_cache: dict = {}

    # -- éléments variables ---------------------------------------------------
    def _eye_text(self, eye) -> str:
        txt = eye.name_en
        if eye.effect:
            txt += f" with a subtle {eye.effect} energetic glow"
        return txt

    def _fur_text(self, fur) -> str:
        return f"{fur.name_en} ({fur.prompt})" if fur.prompt else fur.name_en

    # -- template (base ou spécifique au style) -------------------------------
    def _template_for(self, combo: Combination) -> str:
        code = combo.style.code
        if code not in self._template_cache:
            specific = self.prompts_dir / "templates" / f"STYLE_{code}.txt"
            if specific.exists():
                self._template_cache[code] = read_text(specific).strip()
            else:
                self._template_cache[code] = self.base_prompt
        return self._template_cache[code]

    # -- API ------------------------------------------------------------------
    def build(self, combo: Combination) -> dict:
        """Retourne {positive, negative} pour une combinaison donnée."""
        resolution = f"{self.config.resolution} x {self.config.resolution} pixels"
        replacements = {
            "[FUR_COLOR]": self._fur_text(combo.fur),
            "[LEFT_EYE_COLOR]": self._eye_text(combo.eye_left),
            "[RIGHT_EYE_COLOR]": self._eye_text(combo.eye_right),
            "[STYLE]": combo.style.name_en,
            "[OUTFIT]": combo.style.outfit,
            "[HEADWEAR]": combo.style.headwear,
            "[HELD_OBJECT]": combo.held_object,
            "[RESOLUTION]": resolution,
        }
        prompt = self._template_for(combo)
        for placeholder, value in replacements.items():
            prompt = prompt.replace(placeholder, value)

        return {"positive": prompt, "negative": self.negative_prompt}
