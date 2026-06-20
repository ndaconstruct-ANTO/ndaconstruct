"""Tests du moteur Anto Designer (stdlib unittest, hors-ligne, sans Pillow)."""

import json
import tempfile
import unittest
from pathlib import Path

from anto_designer import (
    combination, database, dedup, layer_engine, metadata, pnglib, project,
    store, validation,
)
from demo.build_demo import build_demo


def _make_layer_png(path, size, color):
    buf = pnglib.new_canvas(size, size, (0, 0, 0, 0))
    for y in range(size // 4, size * 3 // 4):
        for x in range(size // 4, size * 3 // 4):
            o = (y * size + x) * 4
            buf[o], buf[o + 1], buf[o + 2], buf[o + 3] = color
    pnglib.write_rgba(path, size, size, buf)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.conn = database.connect(self.dir / "t.db")

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def _collection_with_layers(self, size=64):
        col = store.create_collection(self.conn, "Test", size, size)
        fur = store.add_category(self.conn, col.id, "Fur", 1, required=True)
        eyes = store.add_category(self.conn, col.id, "Eyes", 2, required=True)
        obj = store.add_category(self.conn, col.id, "Object", 3, required=False)
        for code, color in (("A", (200, 100, 100, 255)), ("B", (100, 200, 100, 255))):
            p = self.dir / f"fur_{code}.png"; _make_layer_png(p, size, color)
            store.add_layer(self.conn, col.id, fur.id, code, f"FUR_{code}", str(p))
        for code, color in (("X", (0, 0, 255, 255)), ("Y", (255, 255, 0, 255))):
            p = self.dir / f"eye_{code}.png"; _make_layer_png(p, size, color)
            store.add_layer(self.conn, col.id, eyes.id, code, f"EYE_{code}", str(p))
        p = self.dir / "obj.png"; _make_layer_png(p, size, (10, 10, 10, 255))
        store.add_layer(self.conn, col.id, obj.id, "Book", "OBJ_BOOK", str(p))
        return col

    def test_collection_crud(self):
        col = self._collection_with_layers()
        cats = store.list_categories(self.conn, col.id)
        self.assertEqual([c.slug for c in cats], ["fur", "eyes", "object"])
        self.assertEqual(len(store.list_layers(self.conn, cats[0].id)), 2)

    def test_composite_dimensions(self):
        size = 64
        p1 = self.dir / "l1.png"; _make_layer_png(p1, size, (255, 0, 0, 128))
        p2 = self.dir / "l2.png"; _make_layer_png(p2, size, (0, 0, 255, 255))
        png = layer_engine.composite([str(p1), str(p2)], size, size,
                                     background=(255, 255, 255, 255))
        w, h, _ = pnglib.read_rgba_bytes(png)
        self.assertEqual((w, h), (size, size))

    def test_combination_unique_and_reproducible(self):
        col = self._collection_with_layers()
        a = combination.generate(self.conn, col, 5, seed=123)
        b = combination.generate(self.conn, col, 5, seed=123)
        self.assertEqual([c.signature for c in a], [c.signature for c in b])
        self.assertEqual(len({c.signature for c in a}), 5)

    def test_capacity_guard(self):
        col = store.create_collection(self.conn, "Tiny", 64, 64)
        cat = store.add_category(self.conn, col.id, "Fur", 1, required=True)
        p = self.dir / "only.png"; _make_layer_png(p, 64, (1, 2, 3, 255))
        store.add_layer(self.conn, col.id, cat.id, "Only", "FUR_ONLY", str(p))
        with self.assertRaises(ValueError):
            combination.generate(self.conn, col, 5, seed=1)

    def test_incompatibility_respected(self):
        col = self._collection_with_layers()
        furs = store.list_layers(self.conn, store.list_categories(self.conn, col.id)[0].id)
        eyes = store.list_layers(self.conn, store.list_categories(self.conn, col.id)[1].id)
        store.add_rule(self.conn, col.id, "incompatible", furs[0].id, eyes[0].id)
        combos = combination.generate(self.conn, col, 6, seed=7)
        for c in combos:
            ids = {l.id for l in c.ordered_layers}
            self.assertFalse(furs[0].id in ids and eyes[0].id in ids)

    def test_dedup_signature(self):
        t = dedup.DuplicateTracker()
        self.assertTrue(t.add_signature("a=1"))
        self.assertFalse(t.add_signature("a=1"))

    def test_metadata_and_naming(self):
        col = self._collection_with_layers()
        combos = combination.generate(self.conn, col, 1, seed=5)
        cats = store.list_categories(self.conn, col.id)
        base = metadata.file_base(col, combos[0], cats)
        self.assertTrue(base)
        meta = metadata.build_metadata(col, combos[0], cats, base + ".png")
        for key in ("name", "description", "image", "attributes"):
            self.assertIn(key, meta)
        self.assertTrue(meta["image"].endswith(".png"))

    def test_validation_rejects_transparent(self):
        empty = pnglib.new_canvas(64, 64, (0, 0, 0, 0))
        import io
        # encode empty canvas
        from anto_designer.pnglib import write_rgba
        tmp = self.dir / "empty.png"; write_rgba(tmp, 64, 64, empty)
        issues = validation.validate_image(tmp.read_bytes(), 64, 64)
        self.assertEqual(validation.status_of(issues), validation.REJECT)

    def test_project_export_import(self):
        col = self._collection_with_layers()
        dest = self.dir / "export"
        project.export_collection(self.conn, col, dest)
        self.assertTrue((dest / "manifest.json").exists())
        imported = project.import_collection(self.conn, dest)
        self.assertNotEqual(imported.id, col.id)
        cats = store.list_categories(self.conn, imported.id)
        self.assertEqual(len(cats), 3)


class DemoPipelineTests(unittest.TestCase):
    def test_full_demo_pipeline(self):
        summary = build_demo(count=6)
        self.assertGreaterEqual(summary["generated"], 6)
        self.assertEqual(summary["validation"].get("REFUSÉ", 0), 0)
        # Les images et métadonnées existent.
        out = Path(summary["output"])
        self.assertTrue(any((out / "images").glob("*.png")))
        self.assertTrue(any((out / "metadata").glob("*.json")))


if __name__ == "__main__":
    unittest.main()
