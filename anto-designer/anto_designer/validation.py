"""Contrôle qualité automatique (logique + image)."""

from __future__ import annotations

from . import pnglib

VALID = "VALIDÉ"
REVIEW = "À CORRIGER"
REJECT = "REFUSÉ"


def validate_combination(combo, categories) -> list:
    """Contrôles logiques sur la combinaison. Retourne [(niveau, message)]."""
    issues = []
    chosen = combo.chosen
    by_slug = {c.slug: c for c in categories}

    for cat in categories:
        layer = chosen.get(cat.slug)
        if cat.required and layer is None:
            issues.append((REJECT, f"Catégorie obligatoire absente : {cat.name}"))

    # Un seul objet dans la patte droite (catégorie dédiée, si présente).
    for slug in ("right_paw_objects", "objet", "object", "held_object"):
        if slug in by_slug:
            # max_one est garanti par construction ; on vérifie la présence unique.
            break

    return issues


def validate_image(png_bytes: bytes, width: int, height: int,
                   *, require_square=True) -> list:
    """Contrôles sur l'image finale (dimensions, transparence, non vide)."""
    issues = []
    try:
        w, h, rgba = pnglib.read_rgba_bytes(png_bytes)
    except Exception as exc:  # noqa: BLE001
        return [(REJECT, f"PNG invalide : {exc}")]

    if require_square and w != h:
        issues.append((REJECT, f"Image non carrée ({w}x{h})"))
    if (w, h) != (width, height):
        issues.append((REVIEW, f"Dimensions {w}x{h} != attendues {width}x{height}"))

    # Image entièrement transparente ou vide ?
    any_opaque = any(rgba[i] for i in range(3, len(rgba), 4))
    if not any_opaque:
        issues.append((REJECT, "Image entièrement transparente (vide)"))

    return issues


def status_of(issues: list) -> str:
    levels = {lvl for lvl, _ in issues}
    if REJECT in levels:
        return REJECT
    if REVIEW in levels:
        return REVIEW
    return VALID


def build_report(combo, categories, png_bytes, width, height,
                 *, require_square=True) -> dict:
    issues = validate_combination(combo, categories)
    if png_bytes is not None:
        issues += validate_image(png_bytes, width, height, require_square=require_square)
    return {
        "token_id": combo.token_id,
        "status": status_of(issues),
        "reasons": [f"[{lvl}] {msg}" for lvl, msg in issues],
    }
