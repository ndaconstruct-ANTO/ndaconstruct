"""Couche de service : opérations de haut niveau utilisées par l'interface
graphique ET par la ligne de commande (donc testables sans GUI).

Garde l'interface fine : toute la logique vit ici, au-dessus du moteur déjà
testé (store, generator).
"""

from __future__ import annotations

import re
from pathlib import Path

from . import generator, pnglib, store


def new_collection(conn, name: str, width: int, height: int, **kwargs):
    """Crée une collection (avec valeurs par défaut raisonnables)."""
    return store.create_collection(conn, name, width, height, **kwargs)


def _parse_category_folder(folder_name: str, fallback_index: int):
    """Déduit (z_index, nom, optionnel) depuis un nom de dossier.

    Exemples :
      "1_Fur"            -> (1, "Fur", obligatoire)
      "3 - Couvre-chef (opt)" -> (3, "Couvre-chef", optionnel)
    """
    m = re.match(r"^\s*(\d+)\s*[_\-\.\s]*(.*)$", folder_name)
    if m:
        z = int(m.group(1))
        name = m.group(2).strip() or folder_name
    else:
        z = fallback_index
        name = folder_name
    optional = any(tok in folder_name.lower()
                   for tok in ("(opt", "optionnel", "_opt", " opt"))
    name = re.sub(r"\(opt[^)]*\)", "", name, flags=re.I).strip() or folder_name
    return z, name, optional


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text.strip().upper()).strip("_") or "X"


def import_layers_from_folder(conn, collection, folder) -> dict:
    """Importe des calques depuis un dossier organisé en sous-dossiers.

    Structure attendue (chaque sous-dossier = une catégorie) ::

        mes_calques/
          1_Fur/      blanc.png  noir.png ...
          2_Eyes/     bleu.png   vert.png ...
          3_Style/    docteur.png ...
          4_Shoes/    bottes.png ...
          5_Objet (opt)/ livre.png ...

    Le numéro en tête donne l'ordre d'affichage. "(opt)" rend la catégorie
    facultative. Les PNG dont les dimensions diffèrent de la collection sont
    ignorés (et listés dans le rapport).
    """
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError(f"Dossier introuvable : {folder}")

    subdirs = sorted([d for d in folder.iterdir() if d.is_dir()],
                     key=lambda d: d.name.lower())
    if not subdirs:
        raise ValueError("Aucun sous-dossier (catégorie) trouvé dans ce dossier.")

    result = {"categories": 0, "layers": 0, "skipped": [], "errors": []}
    for idx, sub in enumerate(subdirs, start=1):
        z, cat_name, optional = _parse_category_folder(sub.name, idx)
        category = store.add_category(conn, collection.id, cat_name, z,
                                      required=not optional)
        result["categories"] += 1

        pngs = sorted(sub.glob("*.png"))
        for p in pngs:
            try:
                w, h = pnglib.read_size(p)
            except Exception as exc:  # noqa: BLE001
                result["errors"].append(f"{p.name}: illisible ({exc})")
                continue
            if (w, h) != (collection.width, collection.height):
                result["skipped"].append(
                    f"{sub.name}/{p.name}: {w}x{h} != {collection.width}x{collection.height}")
                continue
            stem = p.stem
            code = f"{_slug(cat_name)}_{_slug(stem)}"
            store.add_layer(conn, collection.id, category.id, stem.title(),
                            code, str(p), trait_value=stem.title())
            result["layers"] += 1

    return result


def generate(conn, collection, count: int, out_dir, *, seed=None,
             progress_cb=None, stop_event=None) -> dict:
    return generator.generate_collection(conn, collection, count, out_dir,
                                         seed=seed, progress_cb=progress_cb,
                                         stop_event=stop_event)


def collection_overview(conn, collection) -> dict:
    """Résumé pour l'affichage : catégories et nombre de calques + capacité."""
    from .combination import count_capacity

    cats = store.list_categories(conn, collection.id)
    cats_layers = [(c, store.list_layers(conn, c.id, active_only=True)) for c in cats]
    return {
        "categories": [
            {"name": c.name, "z_index": c.z_index, "required": c.required,
             "layers": len(layers)}
            for c, layers in cats_layers
        ],
        "capacity": count_capacity(cats_layers) if cats_layers else 0,
    }
