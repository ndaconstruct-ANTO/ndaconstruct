"""Génération des métadonnées NFT (JSON) et du nommage des fichiers."""

from __future__ import annotations

import re


def file_base(collection, combo, categories) -> str:
    """Nom de base du fichier selon le gabarit, sans extension."""
    template = collection.naming_template or "{slug}_{id:04d}"
    # Variables disponibles : slug, id, et chaque catégorie (slug -> code).
    fields = {"slug": collection.slug.upper(), "id": combo.token_id}
    for cat in categories:
        layer = combo.chosen.get(cat.slug)
        fields[cat.slug] = (layer.code if layer else "NONE")
    try:
        base = template.format(**fields)
    except (KeyError, IndexError):
        base = f"{collection.slug.upper()}_{combo.token_id:04d}"
    return re.sub(r"[^A-Za-z0-9_\-]", "_", base)


def build_metadata(collection, combo, categories, image_filename: str) -> dict:
    cfg = collection.metadata_config or {}
    name_prefix = cfg.get("name_prefix", collection.name)
    description = cfg.get(
        "description",
        f"Collection officielle créée avec ANTO DESIGNER — NFT Collection Studio",
    )
    attributes = []
    for cat in categories:
        layer = combo.chosen.get(cat.slug)
        if layer is None:
            continue
        attributes.append({"trait_type": cat.name, "value": layer.trait_value})

    meta = {
        "name": f"{name_prefix} #{combo.token_id:0{cfg.get('id_digits', 4)}d}",
        "description": description,
        "image": cfg.get("image_uri_prefix", "") + image_filename,
        "attributes": attributes,
    }
    for k, v in (cfg.get("extra_properties") or {}).items():
        meta.setdefault(k, v)
    return meta
