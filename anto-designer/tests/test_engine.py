"""Tests du moteur Anto Designer (stdlib unittest, hors-ligne, sans Pillow)."""

import json
import tempfile
import unittest
from pathlib import Path

from anto_designer import (
    combination, database, dedup, imageops, layer_engine, metadata, pnglib,
    project, service, store, validation,
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


class ServiceTests(unittest.TestCase):
    def test_import_folder_and_generate(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        conn = database.connect(root / "s.db")
        self.addCleanup(conn.close)

        size = 48
        layers_root = root / "calques"
        spec = [("1_Fur", ["white", "black"]), ("2_Eyes", ["blue", "green"]),
                ("3_Objet (opt)", ["book"])]
        palette = {"white": (240, 240, 240, 255), "black": (20, 20, 20, 255),
                   "blue": (0, 0, 255, 255), "green": (0, 200, 0, 255),
                   "book": (150, 90, 20, 255)}

        def _slot_png(path, color, slot):
            # Chaque catégorie occupe une zone distincte -> composites différents.
            buf = pnglib.new_canvas(size, size, (0, 0, 0, 0))
            x0, y0 = slot * 12 + 2, slot * 12 + 2
            for y in range(y0, y0 + 10):
                for x in range(x0, x0 + 10):
                    o = (y * size + x) * 4
                    buf[o], buf[o + 1], buf[o + 2], buf[o + 3] = color
            pnglib.write_rgba(path, size, size, buf)

        for slot, (cat, names) in enumerate(spec):
            d = layers_root / cat
            d.mkdir(parents=True)
            for nm in names:
                _slot_png(d / f"{nm}.png", palette[nm], slot)

        col = service.new_collection(conn, "Imported", size, size)
        rep = service.import_layers_from_folder(conn, col, layers_root)
        self.assertEqual(rep["categories"], 3)
        self.assertEqual(rep["layers"], 5)

        ov = service.collection_overview(conn, col)
        self.assertEqual(len(ov["categories"]), 3)
        # 3e catégorie optionnelle.
        self.assertFalse(ov["categories"][2]["required"])

        out = root / "out"
        summary = service.generate(conn, col, 4, out, seed=1)
        self.assertGreaterEqual(summary["generated"], 4)

    def test_import_skips_wrong_size(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        conn = database.connect(root / "s2.db")
        self.addCleanup(conn.close)
        d = root / "lay" / "1_Fur"; d.mkdir(parents=True)
        _make_layer_png(d / "ok.png", 64, (1, 2, 3, 255))
        _make_layer_png(d / "bad.png", 32, (1, 2, 3, 255))
        col = service.new_collection(conn, "Sz", 64, 64)
        rep = service.import_layers_from_folder(conn, col, root / "lay")
        self.assertEqual(rep["layers"], 1)
        self.assertEqual(len(rep["skipped"]), 1)


class ImageOpsTests(unittest.TestCase):
    def test_remove_background_keeps_center(self):
        w = h = 16
        buf = pnglib.new_canvas(w, h, (255, 255, 255, 255))  # fond blanc opaque
        for y in range(6, 10):                                # carré rouge central
            for x in range(6, 10):
                o = (y * w + x) * 4
                buf[o], buf[o + 1], buf[o + 2], buf[o + 3] = (255, 0, 0, 255)
        cleared = imageops.remove_background(buf, w, h, tolerance=20)
        self.assertGreater(cleared, 0)
        self.assertEqual(buf[(0 * w + 0) * 4 + 3], 0)          # coin transparent
        self.assertEqual(buf[(8 * w + 8) * 4 + 3], 255)        # centre conservé

    def test_erase_circle(self):
        w = h = 16
        buf = pnglib.new_canvas(w, h, (0, 0, 0, 255))
        imageops.erase_circle(buf, w, h, 8, 8, 3)
        self.assertEqual(buf[(8 * w + 8) * 4 + 3], 0)

    def test_fit_to_canvas(self):
        src = pnglib.new_canvas(10, 20, (1, 2, 3, 255))
        dst = imageops.fit_to_canvas(src, 10, 20, 32, 32)
        self.assertEqual(len(dst), 32 * 32 * 4)


class RecolorTests(unittest.TestCase):
    def test_recolor_preserves_shading_changes_hue(self):
        w = h = 8
        buf = pnglib.new_canvas(w, h, (128, 128, 128, 255))  # gris moyen
        imageops.recolor(buf, w, h, (255, 0, 0), strength=1.0)  # -> rouge
        o = 0
        self.assertGreater(buf[o], buf[o + 1])   # r > g
        self.assertGreater(buf[o], buf[o + 2])   # r > b
        self.assertEqual(buf[o + 3], 255)        # alpha conservé

    def test_recolor_skips_transparent(self):
        w = h = 4
        buf = pnglib.new_canvas(w, h, (0, 0, 0, 0))
        imageops.recolor(buf, w, h, (255, 0, 0))
        self.assertEqual(sum(buf), 0)            # rien changé (tout transparent)

    def test_generate_color_variants(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        conn = database.connect(root / "t.db"); self.addCleanup(conn.close)
        col = service.new_collection(conn, "Var", 16, 16)
        base = root / "body.png"; _make_layer_png(base, 16, (150, 150, 150, 255))
        res = service.generate_color_variants(
            conn, col, base, "Fur", {"Rouge": "#FF0000", "Bleu": "#0000FF"})
        self.assertEqual(len(res["created"]), 2)
        cats = store.list_categories(conn, col.id)
        fur = next(c for c in cats if c.name == "Fur")
        self.assertEqual(len(store.list_layers(conn, fur.id)), 2)


class TemplateServiceTests(unittest.TestCase):
    def test_example_template_importable(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        conn = database.connect(root / "t.db"); self.addCleanup(conn.close)
        col = service.new_collection(conn, "Tpl", 64, 64)
        service.create_example_layers_template(root / "ex", col)
        rep = service.import_layers_from_folder(conn, col, root / "ex")
        self.assertEqual(rep["categories"], 5)
        self.assertGreater(rep["layers"], 0)

    def test_add_single_layer_file(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        conn = database.connect(root / "t.db"); self.addCleanup(conn.close)
        col = service.new_collection(conn, "One", 32, 32)
        p = root / "hat.png"; _make_layer_png(p, 32, (10, 20, 30, 255))
        out = service.add_layer_file(conn, col, "Headwear", p)
        self.assertEqual(out["category"], "Headwear")


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
