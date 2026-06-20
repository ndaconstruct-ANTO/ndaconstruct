"""Export / import portable d'une collection (manifeste versionné)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from . import store

PROJECT_FORMAT_VERSION = 1


def export_collection(conn, collection, dest_dir: Path) -> Path:
    """Exporte une collection (métadonnées + calques) dans un dossier portable."""
    dest_dir = Path(dest_dir)
    assets = dest_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    categories = store.list_categories(conn, collection.id)
    cats_payload = []
    for cat in categories:
        layers = store.list_layers(conn, cat.id, active_only=False)
        layer_items = []
        for l in layers:
            src = Path(l.file_path)
            copied = ""
            if src.exists():
                copied = f"assets/{src.name}"
                shutil.copy2(src, assets / src.name)
            layer_items.append({
                "name": l.name, "code": l.code, "file": copied,
                "rarity_tier": l.rarity_tier, "weight": l.weight,
                "max_uses": l.max_uses, "active": l.active,
                "trait_value": l.trait_value,
            })
        cats_payload.append({
            "name": cat.name, "slug": cat.slug, "z_index": cat.z_index,
            "required": cat.required, "max_one": cat.max_one, "layers": layer_items,
        })

    rules = store.list_rules(conn, collection.id)
    manifest = {
        "format_version": PROJECT_FORMAT_VERSION,
        "app": "ANTO DESIGNER",
        "collection": {
            "name": collection.name, "slug": collection.slug,
            "width": collection.width, "height": collection.height,
            "background_mode": collection.background_mode,
            "background_color": collection.background_color,
            "naming_template": collection.naming_template,
            "metadata_config": collection.metadata_config,
        },
        "categories": cats_payload,
        "rules": [{"kind": r.kind, "layer_a": r.layer_a, "layer_b": r.layer_b}
                  for r in rules],
    }
    (dest_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return dest_dir


def import_collection(conn, src_dir: Path) -> "object":
    """Importe une collection depuis un dossier exporté. Retourne la Collection."""
    src_dir = Path(src_dir)
    manifest = json.loads((src_dir / "manifest.json").read_text(encoding="utf-8"))
    c = manifest["collection"]

    # Nom unique si déjà présent.
    name = c["name"]
    existing = {col.slug for col in store.list_collections(conn)}
    base_slug = c["slug"]
    if base_slug in existing:
        name = f"{name} (import)"

    collection = store.create_collection(
        conn, name, c["width"], c["height"],
        background_mode=c.get("background_mode", "white"),
        background_color=c.get("background_color", "#FFFFFF"),
        naming_template=c.get("naming_template", "{slug}_{id:04d}"),
        metadata_config=c.get("metadata_config", {}),
    )

    code_to_id = {}
    for cat in manifest["categories"]:
        category = store.add_category(conn, collection.id, cat["name"], cat["z_index"],
                                      required=cat["required"], max_one=cat["max_one"])
        for l in cat["layers"]:
            file_path = ""
            if l.get("file"):
                file_path = str(src_dir / l["file"])
            layer = store.add_layer(conn, collection.id, category.id, l["name"],
                                    l["code"], file_path, rarity_tier=l["rarity_tier"],
                                    weight=l["weight"], max_uses=l["max_uses"],
                                    active=l["active"], trait_value=l["trait_value"])
            code_to_id[l["code"]] = layer.id

    return collection
