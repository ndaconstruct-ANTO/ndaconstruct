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
from anto_designer import imageops, pnglib  # noqa: E402

MARGIN = 0.08  # bord constant autour du personnage

ROOT = Path(__file__).resolve().parent.parent          # collection_generator/
TRANSP_SRC = ROOT / "output" / "transparent"
META_SRC = ROOT / "output" / "metadata"
OUT = ROOT / "livraison"

# Dossiers de fonds (clé interne -> nom de dossier).
BG_FOLDERS = {
    "vert": "vert", "bleu": "bleu", "rouge": "rouge",
    "gris_argent": "gris_argent", "or_legendary": "or_legendary",
}

# Dégradé radial PRONONCÉ : centre clair -> bords nettement plus foncés.
BG_COLORS = {
    "vert":        ((150, 240, 180), (6, 38, 24)),
    "bleu":        ((140, 195, 248), (6, 24, 64)),
    "rouge":       ((238, 145, 145), (60, 8, 14)),
    "gris_argent": ((238, 240, 244), (62, 66, 76)),
    "or_legendary": ((253, 230, 150), (92, 64, 14)),
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
    """Attribue un fond CONTRASTANT (jamais ton sur ton).

    Le fond est choisi pour faire ressortir le lionceau (couleur opposée /
    complémentaire), jamais la même teinte que le pelage. Les légendaires vont
    sur le fond OR (sauf pelage or, qui serait ton sur ton -> fond contrastant).
    """
    if rarity == "Legendary":
        return "or_legendary" if fur_en != "Gold" else "bleu"

    contrast = {
        "Green": "rouge",          # vert -> rouge (complémentaire)
        "Red": "vert",             # rouge -> vert (complémentaire)
        "Ice Blue": "rouge",       # bleu clair -> rouge (fort contraste)
        "Purple": "vert",          # mauve -> vert
        "Pure White": "bleu",      # blanc -> bleu (pas de blanc/gris ton sur ton)
        "Deep Black": "gris_argent",  # noir -> argent clair (fort contraste)
        "Silver Grey": "bleu",     # gris -> bleu (évite gris sur gris)
        "Gold": "bleu",            # or -> bleu (évite or sur or)
        "Light Tan": "vert",       # brun clair -> vert
    }
    return contrast.get(fur_en, "bleu")


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
    # Réserve = transparents normalisés (marge constante), toujours synchronisée.
    reserve = OUT / "collection_transparente"
    reserve.mkdir(parents=True, exist_ok=True)
    for p in transp:
        w, h, buf = pnglib.read_rgba(p)
        buf = imageops.normalize_margins(buf, w, h, margin_ratio=MARGIN)
        pnglib.write_rgba(reserve / p.name, w, h, buf)

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
        lw, lh, lbuf = pnglib.read_rgba(reserve / p.name)  # transparent normalisé
        pnglib.alpha_over(canvas, lbuf)     # lionceau par-dessus, marge constante
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
