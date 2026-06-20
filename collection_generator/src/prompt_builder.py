"""Construction des prompts à partir du prompt maître verrouillé.

Sépare strictement :
  - les éléments FIXES (prompt de base, non modifiable par combinaison) ;
  - les éléments VARIABLES (injectés via les emplacements [VARIABLE]) ;
  - le prompt NÉGATIF officiel.

Règles intégrées (pas seulement écrites) : objet dans la patte DROITE,
chaussures OBLIGATOIRES et adaptées, pattes félines (jamais de mains humaines).
"""

from __future__ import annotations

from pathlib import Path

from .combination_generator import Combination
from .utils import PROMPTS_DIR, Config, Style, read_text


def shoe_description(style: Style) -> str:
    """Chaussures adaptées au style (champ dédié, sinon généré, sans marque)."""
    if style.footwear:
        return style.footwear
    return (
        f"sturdy shoes clearly suited to a {style.name_en.lower()}, original and "
        f"generic design, no brand and no logo"
    )


def object_phrase(held_object: str) -> str:
    """Transforme 'Single katana' -> 'a single katana' pour une phrase fluide."""
    obj = (held_object or "").strip()
    if not obj or obj.lower() == "none":
        return "nothing"
    if obj.lower().startswith("single "):
        obj = obj[len("single "):]
    return obj


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
    def _eye_text(self, combo: Combination) -> str:
        left, right = combo.eye_left, combo.eye_right
        if combo.heterochromia:
            l = left.name_en + (f" ({left.effect} glow)" if left.effect else "")
            r = right.name_en + (f" ({right.effect} glow)" if right.effect else "")
            return f"heterochromia eyes ({l} left eye and {r} right eye)"
        glow = f" with a subtle {left.effect} energetic glow" if left.effect else ""
        return f"{left.name_en} eyes{glow}"

    def _fur_text(self, fur) -> str:
        base = f"{fur.name_en} realistic fur"
        return f"{base} ({fur.prompt})" if fur.prompt else base

    def _headwear_text(self, style: Style) -> str:
        hw = (style.headwear or "").strip()
        if not hw or hw.lower() == "none":
            return "no headwear"
        return f"a {hw}"

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
        eye_name = combo.eye_left.name_en
        if combo.heterochromia:
            eye_name = f"{combo.eye_left.name_en} or {combo.eye_right.name_en}"
        replacements = {
            "[FUR_COLOR]": self._fur_text(combo.fur),
            "[EYE_COLOR]": self._eye_text(combo),
            "[LEFT_EYE_COLOR]": combo.eye_left.name_en,
            "[RIGHT_EYE_COLOR]": combo.eye_right.name_en,
            "[FUR_NAME]": combo.fur.name_en,
            "[EYE_NAME]": eye_name,
            "[STYLE]": combo.style.name_en,
            "[TOP]": f"a detailed {combo.style.name_en.lower()} upper garment",
            "[BOTTOM]": f"matching trousers/pants fully covering the legs, suited to the "
                        f"{combo.style.name_en.lower()} style",
            "[OUTFIT]": combo.style.outfit,
            "[HEADWEAR]": self._headwear_text(combo.style),
            "[SHOES]": shoe_description(combo.style),
            "[OBJECT]": object_phrase(combo.held_object),
            "[RESOLUTION]": resolution,
        }
        prompt = self._template_for(combo)
        for placeholder, value in replacements.items():
            prompt = prompt.replace(placeholder, value)

        # Texte autorisé sur un accessoire (marque "FLIPPERZ", slogan…).
        if combo.style.text:
            prompt += (
                f"\n\nOn the {combo.style.text_on}, clearly display the exact text "
                f"\"{combo.style.text}\" in clean bold legible lettering, correctly "
                f"spelled, well integrated on the fabric/surface. No other text or "
                f"writing anywhere else on the image."
            )

        return {"positive": prompt, "negative": self.negative_prompt}
