"""Couche de service : opérations de haut niveau utilisées par l'interface
graphique ET par la ligne de commande (donc testables sans GUI).

Garde l'interface fine : toute la logique vit ici, au-dessus du moteur déjà
testé (store, generator).
"""

from __future__ import annotations

import re
from pathlib import Path

from . import generator, imageops, pnglib, store

# Palettes par défaut (recoloration gratuite).
DEFAULT_FUR_COLORS = {
    "Blanc": "#F2F2F2", "Bleu Ice": "#BFE6F2", "Noir": "#2A2A2A",
    "Vert": "#3FA66A", "Mauve": "#7A4FB0", "Gris": "#9AA0A6",
    "Or": "#E6B422", "Rouge": "#C0392B", "Brun Clair": "#C9A36A",
}
DEFAULT_EYE_COLORS = {
    "Bleu": "#2563EB", "Bleu Ice": "#A8D8EA", "Turquoise": "#1ABC9C",
    "Vert": "#2ECC71", "Vert Émeraude": "#1E8449", "Jaune": "#F1C40F",
    "Ambre": "#FFBF00", "Orange": "#E67E22", "Rouge": "#E74C3C",
    "Rose": "#FF6FAE", "Violet": "#8E44AD", "Doré": "#D4AF37",
    "Argent": "#C0C0C0", "Noir": "#2C3E50", "Cosmique": "#6C5CE7",
    "Givre": "#D6F5FF", "Flamme": "#FF7043", "Citron": "#9ACD32",
    "Nuit": "#1E2A78", "Électrique": "#39FF14",
}


def _hex_rgb(h: str):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


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


_EXAMPLE_STRUCTURE = [
    ("1_Fur", ["blanc", "noir", "or"]),
    ("2_Eyes", ["bleu", "vert", "ambre"]),
    ("3_Style", ["docteur", "samourai"]),
    ("4_Shoes", ["bottes", "baskets"]),
    ("5_Objet (opt)", ["livre", "katana"]),
]


def create_example_layers_template(folder, collection) -> str:
    """Crée un dossier-exemple (structure + PNG placeholders à la bonne taille).

    L'utilisateur n'a plus qu'à remplacer les images par les siennes.
    Les placeholders sont quasi transparents (légère marque) pour rester légers.
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    w, h = collection.width, collection.height
    palette = [(240, 240, 240, 90), (40, 40, 40, 90), (230, 180, 34, 90),
               (0, 0, 255, 90), (0, 160, 0, 90)]
    for ci, (cat, names) in enumerate(_EXAMPLE_STRUCTURE):
        d = folder / cat
        d.mkdir(parents=True, exist_ok=True)
        for ni, nm in enumerate(names):
            buf = pnglib.new_canvas(w, h, (0, 0, 0, 0))
            color = palette[ci % len(palette)]
            # petit repère pour visualiser la zone (sinon image vide)
            x0, y0 = w // 4, h // 4 + ci * (h // 12)
            for y in range(y0, min(h, y0 + h // 12)):
                row = y * w
                for x in range(x0, min(w, x0 + w // 2)):
                    o = (row + x) * 4
                    buf[o], buf[o + 1], buf[o + 2], buf[o + 3] = color
            pnglib.write_rgba(d / f"{nm}.png", w, h, buf)
    return str(folder)


def add_layer_file(conn, collection, category_name: str, image_path, *,
                   name=None, weight=1.0, rarity_tier="Common") -> dict:
    """Ajoute un seul calque (depuis un PNG) à une catégorie (créée si besoin)."""
    image_path = Path(image_path)
    w, h = pnglib.read_size(image_path)
    if (w, h) != (collection.width, collection.height):
        raise ValueError(
            f"Taille {w}x{h} != collection {collection.width}x{collection.height}")

    cats = store.list_categories(conn, collection.id)
    match = next((c for c in cats if c.name.lower() == category_name.lower()), None)
    if match is None:
        z = (max((c.z_index for c in cats), default=0) + 1)
        match = store.add_category(conn, collection.id, category_name, z)

    stem = name or image_path.stem
    code = f"{_slug(category_name)}_{_slug(stem)}"
    layer = store.add_layer(conn, collection.id, match.id, stem.title(), code,
                            str(image_path), weight=weight, rarity_tier=rarity_tier,
                            trait_value=stem.title())
    return {"category": match.name, "layer": layer.name}


def generate_color_variants(conn, collection, base_image_path, category_name,
                            colors: dict, *, strength=0.85) -> dict:
    """Crée GRATUITEMENT des calques recolorés depuis une image de base.

    Pour chaque (nom -> couleur hex), recolore l'image de base en conservant les
    ombres, enregistre le PNG et ajoute le calque à la catégorie.
    Idéal pour les 9 pelages et les couleurs d'yeux (aucun coût).
    """
    base = Path(base_image_path)
    w, h, buf = pnglib.read_rgba(base)
    if (w, h) != (collection.width, collection.height):
        raise ValueError(
            f"Image de base {w}x{h} != collection "
            f"{collection.width}x{collection.height}")

    assets = Path("")  # déterminé par add_layer_file via chemin fourni
    out_dir = base.parent / f"_variants_{_slug(category_name)}"
    out_dir.mkdir(parents=True, exist_ok=True)

    made = []
    for name, hexcol in colors.items():
        variant = bytearray(buf)  # copie
        imageops.recolor(variant, w, h, _hex_rgb(hexcol), strength=strength)
        out = out_dir / f"{_slug(category_name)}_{_slug(name)}.png"
        pnglib.write_rgba(out, w, h, variant)
        add_layer_file(conn, collection, category_name, out, name=name)
        made.append(name)
    return {"category": category_name, "created": made}


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
