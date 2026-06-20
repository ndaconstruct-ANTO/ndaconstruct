"""Système de FONDS réversible pour la collection de lionceaux.

Principes (réversibilité totale) :
  - les PNG transparents d'origine NE SONT JAMAIS modifiés ;
  - les 5 fonds sont des fichiers indépendants (modifiables) ;
  - l'assemblage lionceau+fond est REGÉNÉRABLE à tout moment ;
  - un fichier de correspondance (CSV + JSON) garde l'attribution ;
  - si le mapping existe déjà, il est respecté (overrides manuels persistants).

Pour changer un fond plus tard : remplacez le fichier fond.png concerné
(ou éditez le mapping) puis relancez ce script.

Arborescence créée sous  livraison/ :
  collection_transparente/         (réserve : copie des transparents)
  fonds_officiels/<couleur>/fond.png
  collection_avec_fonds/<couleur>/*.png
  rapports/mapping.csv, mapping.json
"""

from __future__ import annotations

import csv
import json
import math
import random
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "anto-designer"))
from anto_designer import pnglib  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent          # collection_generator/
TRANSP_SRC = ROOT / "output" / "transparent"
META_SRC = ROOT / "output" / "metadata"
OUT = ROOT / "livraison"

# Dossiers de fonds (clé interne -> nom de dossier).
BG_FOLDERS = {
    "vert": "vert", "bleu": "bleu", "rouge": "rouge",
    "gris_argent": "gris_argent", "or_legendary": "or_legendary",
}

# Dégradé radial : (couleur centre, couleur bord). Centre clair -> bord foncé.
BG_COLORS = {
    "vert":        ((120, 210, 150), (18, 70, 45)),
    "bleu":        ((120, 170, 235), (16, 44, 92)),
    "rouge":       ((225, 120, 120), (92, 18, 26)),
    "gris_argent": ((224, 226, 230), (92, 96, 106)),
    "or_legendary": ((247, 218, 128), (120, 88, 24)),
}


def _smoothstep(t):
    return t * t * (3 - 2 * t)


def make_background(path: Path, size: int, center, edge, glitter=False, seed=7):
    buf = bytearray(size * size * 4)
    cx = cy = size / 2.0
    maxd = math.hypot(cx, cy)
    for y in range(size):
        dy2 = (y - cy) ** 2
        row = y * size
        for x in range(size):
            t = _smoothstep(min(1.0, math.sqrt((x - cx) ** 2 + dy2) / maxd))
            o = (row + x) * 4
            buf[o] = int(center[0] + (edge[0] - center[0]) * t)
            buf[o + 1] = int(center[1] + (edge[1] - center[1]) * t)
            buf[o + 2] = int(center[2] + (edge[2] - center[2]) * t)
            buf[o + 3] = 255
    if glitter:
        rng = random.Random(seed)
        for _ in range(int(size * size * 0.0035)):
            x = rng.randrange(size); y = rng.randrange(size)
            b = rng.randint(225, 255)
            o = (y * size + x) * 4
            buf[o] = b; buf[o + 1] = b; buf[o + 2] = min(255, b - 20); buf[o + 3] = 255
    path.parent.mkdir(parents=True, exist_ok=True)
    pnglib.write_rgba(path, size, size, buf)


def assign_background(fur_en: str, rarity: str) -> str:
    """Attribue un fond selon la rareté puis la couleur de pelage."""
    if rarity == "Legendary" or fur_en == "Gold":
        return "or_legendary"
    mapping = {
        "Green": "vert",
        "Ice Blue": "bleu", "Purple": "bleu",
        "Red": "rouge",
        "Pure White": "gris_argent", "Deep Black": "gris_argent",
        "Silver Grey": "gris_argent", "Light Tan": "gris_argent",
    }
    return mapping.get(fur_en, "gris_argent")


def _token_id(filename: str) -> str:
    # LION_0007_FUR-... -> 0007
    parts = filename.split("_")
    return parts[1] if len(parts) > 1 else filename


def build():
    transp = sorted(TRANSP_SRC.glob("*.png"))
    if not transp:
        raise SystemExit("Aucun transparent trouvé dans output/transparent.")
    size = pnglib.read_size(transp[0])[0]

    # 1) Réserve : copie des transparents (originaux intacts).
    reserve = OUT / "collection_transparente"
    reserve.mkdir(parents=True, exist_ok=True)
    for p in transp:
        shutil.copy2(p, reserve / p.name)  # réserve toujours synchronisée

    # 2) Les 5 fonds officiels (régénérés à chaque build, fichiers indépendants).
    for key in BG_FOLDERS:
        center, edge = BG_COLORS[key]
        make_background(OUT / "fonds_officiels" / key / "fond.png", size,
                        center, edge, glitter=(key == "or_legendary"))

    # 3) Mapping existant (réversibilité : on respecte les overrides manuels).
    rapports = OUT / "rapports"
    rapports.mkdir(parents=True, exist_ok=True)
    map_json = rapports / "mapping.json"
    existing = {}
    if map_json.exists():
        existing = {e["id"]: e for e in json.loads(map_json.read_text("utf-8"))["mapping"]}

    # 4) Assemblage lionceau + fond.
    bg_cache = {k: pnglib.read_rgba(OUT / "fonds_officiels" / k / "fond.png")
                for k in BG_FOLDERS}
    rows = []
    for p in transp:
        tid = _token_id(p.name)
        meta_file = META_SRC / f"LION_{tid}_METADATA.json"
        fur = rarity = style = ""
        if meta_file.exists():
            m = json.loads(meta_file.read_text("utf-8"))
            fur = m.get("fur_color", ""); rarity = m.get("rarity", "")
            style = m.get("style", "")
        # Respecte un override existant, sinon calcule.
        bg = existing.get(tid, {}).get("background") or assign_background(fur, rarity)

        fw, fh, fbuf = bg_cache[bg]
        canvas = bytearray(fbuf)            # copie du fond
        lw, lh, lbuf = pnglib.read_rgba(p)
        pnglib.alpha_over(canvas, lbuf)     # lionceau par-dessus, cadrage inchangé
        dest_dir = OUT / "collection_avec_fonds" / bg
        dest_dir.mkdir(parents=True, exist_ok=True)
        pnglib.write_rgba(dest_dir / p.name, fw, fh, canvas)

        rows.append({"id": tid, "file": p.name, "background": bg,
                     "fur": fur, "style": style, "rarity": rarity})

    # 5) Fichiers de correspondance.
    map_json.write_text(json.dumps({"mapping": rows}, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    with open(rapports / "mapping.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "file", "background", "fur",
                                          "style", "rarity"])
        w.writeheader(); w.writerows(rows)

    # Petit résumé.
    from collections import Counter
    dist = Counter(r["background"] for r in rows)
    print("Assemblage terminé.")
    print("Répartition des fonds :", dict(dist))
    print("Sorties dans :", OUT)
    return rows


if __name__ == "__main__":
    build()
