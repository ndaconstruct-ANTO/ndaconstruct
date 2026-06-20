"""Projet de démonstration : crée des calques synthétiques et génère une mini
collection — entièrement hors-ligne et sans Pillow (utilise ``pnglib``).

Sert à démontrer et tester toute la chaîne sans dépendre des images de
l'utilisateur. Ne modifie JAMAIS de fichiers originaux : tout est créé dans un
espace de travail dédié.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from anto_designer import database, generator, pnglib, store

DEMO_ROOT = Path(__file__).resolve().parent / "_workspace"
SIZE = 256


# --- petits outils de dessin (RGBA) -----------------------------------------
def _blank():
    return pnglib.new_canvas(SIZE, SIZE, (0, 0, 0, 0))


def _set(buf, x, y, rgba):
    if 0 <= x < SIZE and 0 <= y < SIZE:
        o = (y * SIZE + x) * 4
        buf[o], buf[o + 1], buf[o + 2], buf[o + 3] = rgba


def _rect(buf, x0, y0, x1, y1, rgba):
    for y in range(max(0, y0), min(SIZE, y1)):
        for x in range(max(0, x0), min(SIZE, x1)):
            _set(buf, x, y, rgba)


def _ellipse(buf, cx, cy, rx, ry, rgba):
    for y in range(cy - ry, cy + ry):
        for x in range(cx - rx, cx + rx):
            if rx and ry and ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                _set(buf, x, y, rgba)


def _save(path: Path, buf):
    pnglib.write_rgba(path, SIZE, SIZE, buf)


def _make_body(path, color):
    buf = _blank()
    _ellipse(buf, 128, 80, 46, 44, color)      # tête
    _ellipse(buf, 100, 60, 12, 14, color)      # oreille G
    _ellipse(buf, 156, 60, 12, 14, color)      # oreille D
    _rect(buf, 96, 110, 160, 200, color)       # corps
    _rect(buf, 70, 120, 96, 185, color)        # bras G
    _rect(buf, 160, 120, 186, 185, color)      # bras D
    _save(path, buf)


def _make_eyes(path, color):
    buf = _blank()
    _ellipse(buf, 112, 80, 7, 9, color)
    _ellipse(buf, 144, 80, 7, 9, color)
    _save(path, buf)


def _make_outfit(path, color):
    buf = _blank()
    _rect(buf, 96, 120, 160, 195, color)
    _save(path, buf)


def _make_shoes(path, color):
    buf = _blank()
    _rect(buf, 96, 196, 124, 212, color)
    _rect(buf, 132, 196, 160, 212, color)
    _save(path, buf)


def _make_object(path, color):
    buf = _blank()
    _rect(buf, 60, 130, 74, 180, color)        # objet dans la patte droite (gauche image)
    _save(path, buf)


def build_demo(count: int = 8) -> dict:
    if DEMO_ROOT.exists():
        shutil.rmtree(DEMO_ROOT)
    assets = DEMO_ROOT / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    conn = database.connect(DEMO_ROOT / "demo.db")
    col = store.create_collection(conn, "Demo Lionceaux", SIZE, SIZE,
                                  naming_template="LION_{id:04d}_FUR-{fur}_STYLE-{outfit}")

    # Catégories ordonnées (z_index croissant = arrière -> avant).
    fur_cat = store.add_category(conn, col.id, "Fur", 1, required=True)
    eyes_cat = store.add_category(conn, col.id, "Eyes", 2, required=True)
    outfit_cat = store.add_category(conn, col.id, "Style", 3, required=True)
    shoes_cat = store.add_category(conn, col.id, "Shoes", 4, required=True)
    obj_cat = store.add_category(conn, col.id, "Right Paw Object", 5, required=False)

    furs = {"TAN": (201, 163, 106, 255), "GREY": (154, 160, 166, 255),
            "BLACK": (40, 40, 40, 255), "GOLD": (230, 180, 34, 255)}
    eyes = {"BLUE": (37, 99, 235, 255), "GREEN": (46, 204, 113, 255),
            "AMBER": (255, 191, 0, 255)}
    outfits = {"DOCTOR": (240, 240, 240, 255), "SAMURAI": (123, 36, 28, 255),
               "MASON": (230, 126, 34, 255)}
    shoes = {"BOOTS": (90, 60, 40, 255), "SNEAKERS": (52, 73, 94, 255)}
    objects = {"BOOK": (125, 80, 20, 255), "KATANA": (180, 180, 190, 255)}

    for code, color in furs.items():
        p = assets / f"fur_{code}.png"; _make_body(p, color)
        store.add_layer(conn, col.id, fur_cat.id, code.title(), f"FUR_{code}",
                        str(p), trait_value=code.title(), weight=2.0)
    for code, color in eyes.items():
        p = assets / f"eyes_{code}.png"; _make_eyes(p, color)
        store.add_layer(conn, col.id, eyes_cat.id, code.title(), f"EYES_{code}",
                        str(p), trait_value=code.title())
    for code, color in outfits.items():
        p = assets / f"outfit_{code}.png"; _make_outfit(p, color)
        store.add_layer(conn, col.id, outfit_cat.id, code.title(), f"STYLE_{code}",
                        str(p), trait_value=code.title())
    for code, color in shoes.items():
        p = assets / f"shoes_{code}.png"; _make_shoes(p, color)
        store.add_layer(conn, col.id, shoes_cat.id, code.title(), f"SHOES_{code}",
                        str(p), trait_value=code.title())
    for code, color in objects.items():
        p = assets / f"object_{code}.png"; _make_object(p, color)
        store.add_layer(conn, col.id, obj_cat.id, code.title(), f"OBJ_{code}",
                        str(p), trait_value=code.title(), rarity_tier="Rare")

    out_dir = DEMO_ROOT / "output"
    summary = generator.generate_collection(conn, col, count, out_dir, seed=42)
    conn.close()
    return {
        "generated": summary["generated"],
        "rejected": summary["rejected"],
        "duplicate_images": summary["duplicate_images"],
        "validation": summary["validation_summary"],
        "output": str(out_dir),
    }


if __name__ == "__main__":
    print(build_demo())
