"""Base de données locale SQLite (migrations versionnées).

SQLite est inclus dans la bibliothèque standard de Python : aucune installation,
robuste, fichier unique, idéal pour un logiciel local. Les migrations sont
versionnées et ne suppriment jamais de données existantes.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1


def connect(db_path: Path) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    migrate(conn)
    return conn


def _user_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def migrate(conn: sqlite3.Connection) -> None:
    """Applique les migrations jusqu'à SCHEMA_VERSION (sans perte de données)."""
    version = _user_version(conn)
    if version < 1:
        _migration_1(conn)
        conn.execute(f"PRAGMA user_version = 1")
    conn.commit()


def _migration_1(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            background_mode TEXT DEFAULT 'white',
            background_color TEXT DEFAULT '#FFFFFF',
            master_path TEXT DEFAULT '',
            naming_template TEXT DEFAULT '{slug}_{id:04d}',
            metadata_config TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            format_version INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            slug TEXT NOT NULL,
            z_index INTEGER NOT NULL DEFAULT 0,
            required INTEGER NOT NULL DEFAULT 1,
            max_one INTEGER NOT NULL DEFAULT 1,
            UNIQUE(collection_id, slug)
        );

        CREATE TABLE IF NOT EXISTS layers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
            category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            code TEXT NOT NULL,
            file_path TEXT NOT NULL,
            thumb_path TEXT DEFAULT '',
            rarity_tier TEXT DEFAULT 'Common',
            weight REAL DEFAULT 1.0,
            max_uses INTEGER DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            trait_value TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(collection_id, code)
        );

        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
            kind TEXT NOT NULL,                 -- incompatible | requires
            layer_a INTEGER NOT NULL REFERENCES layers(id) ON DELETE CASCADE,
            layer_b INTEGER NOT NULL REFERENCES layers(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS generated (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
            token_id INTEGER NOT NULL,
            signature TEXT NOT NULL,
            file_name TEXT NOT NULL,
            image_hash TEXT DEFAULT '',
            status TEXT DEFAULT 'VALIDÉ',
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(collection_id, signature)
        );

        CREATE TABLE IF NOT EXISTS generated_traits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_id INTEGER NOT NULL REFERENCES generated(id) ON DELETE CASCADE,
            category TEXT NOT NULL,
            layer_id INTEGER,
            value TEXT DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_layers_cat ON layers(category_id);
        CREATE INDEX IF NOT EXISTS idx_gen_coll ON generated(collection_id);
        """
    )
