"""Accès aux données (CRUD) au-dessus de SQLite, renvoyant des dataclasses."""

from __future__ import annotations

import json
import re
import sqlite3

from .models import Category, Collection, Layer, Rule


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
    return s or "item"


# --- Collections -------------------------------------------------------------
def create_collection(conn: sqlite3.Connection, name: str, width: int, height: int,
                      *, background_mode="white", background_color="#FFFFFF",
                      master_path="", naming_template="{slug}_{id:04d}",
                      metadata_config=None) -> Collection:
    slug = _slugify(name)
    cur = conn.execute(
        "INSERT INTO collections(name, slug, width, height, background_mode, "
        "background_color, master_path, naming_template, metadata_config) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (name, slug, width, height, background_mode, background_color,
         master_path, naming_template, json.dumps(metadata_config or {})),
    )
    conn.commit()
    return get_collection(conn, cur.lastrowid)


def get_collection(conn: sqlite3.Connection, cid: int) -> Collection:
    r = conn.execute("SELECT * FROM collections WHERE id=?", (cid,)).fetchone()
    if not r:
        raise KeyError(f"Collection {cid} introuvable")
    return Collection(
        id=r["id"], name=r["name"], slug=r["slug"], width=r["width"],
        height=r["height"], background_mode=r["background_mode"],
        background_color=r["background_color"], master_path=r["master_path"],
        naming_template=r["naming_template"],
        metadata_config=json.loads(r["metadata_config"] or "{}"),
    )


def list_collections(conn: sqlite3.Connection) -> list:
    rows = conn.execute("SELECT id FROM collections ORDER BY id").fetchall()
    return [get_collection(conn, r["id"]) for r in rows]


# --- Catégories --------------------------------------------------------------
def add_category(conn: sqlite3.Connection, collection_id: int, name: str,
                 z_index: int, *, required=True, max_one=True) -> Category:
    slug = _slugify(name)
    cur = conn.execute(
        "INSERT INTO categories(collection_id, name, slug, z_index, required, max_one) "
        "VALUES(?,?,?,?,?,?)",
        (collection_id, name, slug, z_index, int(required), int(max_one)),
    )
    conn.commit()
    r = conn.execute("SELECT * FROM categories WHERE id=?", (cur.lastrowid,)).fetchone()
    return _row_category(r)


def list_categories(conn: sqlite3.Connection, collection_id: int) -> list:
    rows = conn.execute(
        "SELECT * FROM categories WHERE collection_id=? ORDER BY z_index, id",
        (collection_id,),
    ).fetchall()
    return [_row_category(r) for r in rows]


def _row_category(r) -> Category:
    return Category(id=r["id"], collection_id=r["collection_id"], name=r["name"],
                    slug=r["slug"], z_index=r["z_index"], required=bool(r["required"]),
                    max_one=bool(r["max_one"]))


# --- Calques -----------------------------------------------------------------
def add_layer(conn: sqlite3.Connection, collection_id: int, category_id: int,
              name: str, code: str, file_path: str, *, rarity_tier="Common",
              weight=1.0, max_uses=0, active=True, trait_value="",
              thumb_path="") -> Layer:
    cur = conn.execute(
        "INSERT INTO layers(collection_id, category_id, name, code, file_path, "
        "thumb_path, rarity_tier, weight, max_uses, active, trait_value) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (collection_id, category_id, name, code, file_path, thumb_path,
         rarity_tier, weight, max_uses, int(active), trait_value or name),
    )
    conn.commit()
    r = conn.execute("SELECT * FROM layers WHERE id=?", (cur.lastrowid,)).fetchone()
    return _row_layer(r)


def list_layers(conn: sqlite3.Connection, category_id: int, *, active_only=True) -> list:
    q = "SELECT * FROM layers WHERE category_id=?"
    if active_only:
        q += " AND active=1"
    q += " ORDER BY id"
    rows = conn.execute(q, (category_id,)).fetchall()
    return [_row_layer(r) for r in rows]


def _row_layer(r) -> Layer:
    return Layer(id=r["id"], collection_id=r["collection_id"],
                 category_id=r["category_id"], name=r["name"], code=r["code"],
                 file_path=r["file_path"], thumb_path=r["thumb_path"],
                 rarity_tier=r["rarity_tier"], weight=r["weight"],
                 max_uses=r["max_uses"], active=bool(r["active"]),
                 trait_value=r["trait_value"])


# --- Règles ------------------------------------------------------------------
def add_rule(conn: sqlite3.Connection, collection_id: int, kind: str,
             layer_a: int, layer_b: int) -> None:
    conn.execute(
        "INSERT INTO rules(collection_id, kind, layer_a, layer_b) VALUES(?,?,?,?)",
        (collection_id, kind, layer_a, layer_b),
    )
    conn.commit()


def list_rules(conn: sqlite3.Connection, collection_id: int) -> list:
    rows = conn.execute(
        "SELECT * FROM rules WHERE collection_id=?", (collection_id,)
    ).fetchall()
    return [Rule(id=r["id"], collection_id=r["collection_id"], kind=r["kind"],
                 layer_a=r["layer_a"], layer_b=r["layer_b"]) for r in rows]


# --- Généré ------------------------------------------------------------------
def record_generated(conn: sqlite3.Connection, collection_id: int, token_id: int,
                     signature: str, file_name: str, image_hash: str, status: str,
                     traits: list) -> int:
    cur = conn.execute(
        "INSERT INTO generated(collection_id, token_id, signature, file_name, "
        "image_hash, status) VALUES(?,?,?,?,?,?)",
        (collection_id, token_id, signature, file_name, image_hash, status),
    )
    gid = cur.lastrowid
    for (category, layer_id, value) in traits:
        conn.execute(
            "INSERT INTO generated_traits(generated_id, category, layer_id, value) "
            "VALUES(?,?,?,?)", (gid, category, layer_id, value),
        )
    conn.commit()
    return gid


def existing_signatures(conn: sqlite3.Connection, collection_id: int) -> set:
    rows = conn.execute(
        "SELECT signature FROM generated WHERE collection_id=?", (collection_id,)
    ).fetchall()
    return {r["signature"] for r in rows}
