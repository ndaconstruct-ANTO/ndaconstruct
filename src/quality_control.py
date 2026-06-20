"""Contrôle qualité automatique de chaque génération.

Deux niveaux de vérification :

1. Contrôles LOGIQUES (toujours possibles, même en simulation) :
   - format strictement carré, résolution correcte ;
   - un seul objet maximum ;
   - cohérence style ↔ objet ;
   - cohérence pelage ↔ configuration ;
   - présence des règles anti-queue / anti-mains humaines dans le prompt ;
   - absence de marque/texte demandés.

2. Contrôles IMAGE (uniquement si un fichier PNG existe réellement) :
   - dimensions du fichier (carré + résolution attendue) ;
   - (réservé) vérifications de centrage/fond si Pillow est disponible.

Chaque image reçoit un statut : VALIDÉE, À CONTRÔLER ou REFUSÉE.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .combination_generator import Character, ConfigBundle
from .image_provider import GenerationResult
from .prompt_builder import BuiltPrompt

STATUS_VALID = "VALIDÉE"
STATUS_REVIEW = "À CONTRÔLER"
STATUS_REJECTED = "REFUSÉE"


@dataclass
class QCResult:
    id: str
    status: str
    errors: List[str] = field(default_factory=list)     # -> REFUSÉE
    warnings: List[str] = field(default_factory=list)    # -> À CONTRÔLER
    checks: Dict[str, bool] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "errors": self.errors,
            "warnings": self.warnings,
            "checks": self.checks,
        }


class QualityControl:
    def __init__(self, bundle: ConfigBundle):
        self.bundle = bundle
        self.image_cfg = bundle.collection["image"]
        self.expected_w = int(self.image_cfg["width"])
        self.expected_h = int(self.image_cfg["height"])
        self._fur_keys = {f["key"] for f in bundle.fur_colors}
        self._styles_by_key = {s["key"]: s for s in bundle.styles}

    def check(
        self,
        character: Character,
        prompt: BuiltPrompt,
        result: Optional[GenerationResult] = None,
    ) -> QCResult:
        qc = QCResult(id=character.id, status=STATUS_VALID)

        self._check_format(qc)
        self._check_single_object(qc, character)
        self._check_style_object_match(qc, character)
        self._check_fur(qc, character)
        self._check_prompt_rules(qc, prompt)

        if result is not None:
            self._check_image_file(qc, result)

        # Statut final.
        if qc.errors:
            qc.status = STATUS_REJECTED
        elif qc.warnings:
            qc.status = STATUS_REVIEW
        else:
            qc.status = STATUS_VALID
        return qc

    # -- contrôles logiques -------------------------------------------------
    def _check_format(self, qc: QCResult) -> None:
        is_square = self.expected_w == self.expected_h
        qc.checks["format_carre"] = is_square
        if not is_square:
            qc.errors.append(
                f"Format non carré : {self.expected_w}x{self.expected_h}."
            )
        qc.checks["resolution_positive"] = self.expected_w > 0 and self.expected_h > 0
        if self.expected_w <= 0 or self.expected_h <= 0:
            qc.errors.append("Résolution invalide.")

    def _check_single_object(self, qc: QCResult, character: Character) -> None:
        # Par construction, character.obj est UN seul objet. On vérifie le contrat.
        ok = isinstance(character.obj, dict) and "key" in character.obj
        qc.checks["objet_unique"] = ok
        if not ok:
            qc.errors.append("Plus d'un objet ou objet mal formé.")

    def _check_style_object_match(self, qc: QCResult, character: Character) -> None:
        style = self._styles_by_key.get(character.style["key"])
        if not style:
            qc.checks["style_connu"] = False
            qc.errors.append(f"Style inconnu : {character.style['key']}.")
            return
        qc.checks["style_connu"] = True
        if character.obj["key"] == "none":
            qc.checks["objet_coherent"] = True
            return
        valid_objs = {o["key"] for o in (style.get("objects") or [])}
        ok = character.obj["key"] in valid_objs
        qc.checks["objet_coherent"] = ok
        if not ok:
            qc.errors.append(
                f"Objet '{character.obj['key']}' incohérent avec le style "
                f"'{character.style['key']}'."
            )

    def _check_fur(self, qc: QCResult, character: Character) -> None:
        ok = character.fur["key"] in self._fur_keys
        qc.checks["pelage_configure"] = ok
        if not ok:
            qc.errors.append(
                f"Couleur de pelage '{character.fur['key']}' absente de la configuration."
            )

    def _check_prompt_rules(self, qc: QCResult, prompt: BuiltPrompt) -> None:
        pos = prompt.positive.lower()
        neg = prompt.negative.lower()

        # Les interdits clés doivent être présents dans le prompt négatif.
        for needle, label in [
            ("human hands", "anti_mains_humaines"),
            ("tail", "anti_queue"),
            ("brand logo", "anti_marque"),
            ("text", "anti_texte"),
        ]:
            present = needle in neg
            qc.checks[label] = present
            if not present:
                qc.warnings.append(
                    f"Règle '{needle}' absente du prompt négatif."
                )

        # Le prompt positif doit verrouiller l'objet unique et le format carré.
        qc.checks["regle_objet_unique"] = "at most one" in pos or "single" in pos
        if not qc.checks["regle_objet_unique"]:
            qc.warnings.append("Règle de l'objet unique non détectée dans le prompt.")
        qc.checks["format_1_1_dans_prompt"] = "1:1" in prompt.positive
        if not qc.checks["format_1_1_dans_prompt"]:
            qc.warnings.append("Format 1:1 non mentionné dans le prompt.")

    # -- contrôle du fichier image (si présent) -----------------------------
    def _check_image_file(self, qc: QCResult, result: GenerationResult) -> None:
        if result.simulated or not result.image_path:
            # Rien à vérifier physiquement en simulation : on le note simplement.
            qc.checks["image_reelle"] = False
            qc.warnings.append(
                "Image simulée : contrôles visuels (centrage, fond, silhouette) "
                "à réaliser après génération réelle."
            )
            return

        path = Path(result.image_path)
        if not path.exists():
            qc.checks["image_presente"] = False
            qc.errors.append(f"Fichier image manquant : {result.image_path}.")
            return
        qc.checks["image_presente"] = True

        dims = _read_image_dimensions(path)
        if dims is None:
            qc.warnings.append(
                "Dimensions de l'image non vérifiables (Pillow non installé)."
            )
            return
        w, h = dims
        qc.checks["image_carree"] = w == h
        if w != h:
            qc.errors.append(f"Image non carrée : {w}x{h}.")
        qc.checks["image_resolution_ok"] = (w == self.expected_w and h == self.expected_h)
        if w != self.expected_w or h != self.expected_h:
            qc.warnings.append(
                f"Résolution {w}x{h} différente de la référence "
                f"{self.expected_w}x{self.expected_h}."
            )


def _read_image_dimensions(path: Path) -> Optional[tuple]:
    """Lit les dimensions d'une image si Pillow est disponible, sinon None."""
    try:
        from PIL import Image  # import paresseux : dépendance optionnelle
    except Exception:
        return None
    try:
        with Image.open(path) as img:
            return img.size
    except Exception:
        return None


def summarize(qc_results: List[QCResult]) -> Dict[str, int]:
    """Compte les statuts pour le rapport global."""
    summary = {STATUS_VALID: 0, STATUS_REVIEW: 0, STATUS_REJECTED: 0}
    for r in qc_results:
        summary[r.status] = summary.get(r.status, 0) + 1
    return summary
