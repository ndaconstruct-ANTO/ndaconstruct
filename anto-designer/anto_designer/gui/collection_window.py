"""Fenêtre d'une collection : import de calques, génération, sortie."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QListWidget, QMessageBox,
    QProgressDialog, QPushButton, QVBoxLayout, QWidget,
)

from .. import service, store
from ..branding import BRANDING
from .dialogs import GenerateDialog


def _open_folder(path: Path) -> None:
    path = Path(path)
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)])
        else:
            subprocess.run(["xdg-open", str(path)])
    except Exception:
        pass


class CollectionWindow(QWidget):
    def __init__(self, conn, collection, paths):
        super().__init__()
        self.conn = conn
        self.collection = collection
        self.paths = paths
        self.out_dir = Path(paths["collections"]) / collection.slug / "output"

        self.setWindowTitle(f"{BRANDING.app_name} — {collection.name}")
        self.resize(900, 640)
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        title = QLabel(self.collection.name); title.setObjectName("Title")
        sub = QLabel(f"Format {self.collection.width}×{self.collection.height} • "
                     f"100% local"); sub.setObjectName("Subtitle")
        root.addWidget(title)
        root.addWidget(sub)

        card = QFrame(); card.setObjectName("Card")
        cl = QVBoxLayout(card)
        cl.addWidget(QLabel("Catégories et calques :"))
        self.list = QListWidget()
        cl.addWidget(self.list)
        self.capacity_label = QLabel("")
        cl.addWidget(self.capacity_label)
        root.addWidget(card, 1)

        row = QHBoxLayout()
        b_import = QPushButton("📥 Importer des calques (dossier)")
        b_import.clicked.connect(self._import)
        b_gen = QPushButton("⚙️ Générer la collection")
        b_gen.clicked.connect(self._generate)
        b_out = QPushButton("📂 Ouvrir le dossier de sortie"); b_out.setObjectName("Ghost")
        b_out.clicked.connect(lambda: _open_folder(self.out_dir))
        row.addWidget(b_import)
        row.addWidget(b_gen)
        row.addWidget(b_out)
        root.addLayout(row)

        help_txt = QLabel(
            "Astuce : préparez un dossier avec un sous-dossier par catégorie, "
            "numéroté pour l'ordre. Ex. : 1_Fur, 2_Eyes, 3_Style, 4_Shoes, "
            "5_Objet (opt). Mettez vos PNG transparents dedans (même taille "
            f"que la collection : {self.collection.width}px).")
        help_txt.setObjectName("Subtitle")
        help_txt.setWordWrap(True)
        root.addWidget(help_txt)

    def refresh(self):
        self.list.clear()
        ov = service.collection_overview(self.conn, self.collection)
        for c in ov["categories"]:
            flag = "" if c["required"] else "  (optionnel)"
            self.list.addItem(
                f"#{c['z_index']}  {c['name']}{flag} — {c['layers']} calque(s)")
        if not ov["categories"]:
            self.list.addItem("(aucune catégorie — importez des calques)")
        self.capacity_label.setText(
            f"Combinaisons possibles : ~{ov['capacity']}")

    # -- actions --------------------------------------------------------------
    def _import(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Choisir le dossier de calques")
        if not folder:
            return
        try:
            rep = service.import_layers_from_folder(self.conn, self.collection, folder)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Import", f"Échec de l'import : {exc}")
            return
        msg = (f"Import terminé :\n• {rep['categories']} catégorie(s)\n"
               f"• {rep['layers']} calque(s)")
        if rep["skipped"]:
            msg += f"\n• {len(rep['skipped'])} ignoré(s) (mauvaise taille)"
        if rep["errors"]:
            msg += f"\n• {len(rep['errors'])} erreur(s)"
        QMessageBox.information(self, "Import", msg)
        self.refresh()

    def _generate(self):
        ov = service.collection_overview(self.conn, self.collection)
        if not ov["categories"]:
            QMessageBox.information(self, "Génération",
                                   "Importez d'abord des calques.")
            return
        dlg = GenerateDialog(self, capacity=ov["capacity"])
        if not dlg.exec():
            return
        count, seed = dlg.values()

        progress = QProgressDialog("Génération en cours…", "Annuler", 0, count, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)

        class _Stop:
            def is_set(_self):
                return progress.wasCanceled()

        def cb(i, total):
            progress.setValue(i)

        try:
            summary = service.generate(self.conn, self.collection, count,
                                       self.out_dir, seed=seed,
                                       progress_cb=cb, stop_event=_Stop())
        except Exception as exc:  # noqa: BLE001
            progress.close()
            QMessageBox.warning(self, "Génération", f"Échec : {exc}")
            return
        progress.setValue(count)

        msg = (f"Terminé !\n• Générés : {summary['generated']}\n"
               f"• Refusés : {summary['rejected']}\n"
               f"• Doublons évités : {summary['duplicate_images']}\n\n"
               f"Dossier : {self.out_dir}")
        box = QMessageBox(self)
        box.setWindowTitle("Génération")
        box.setText(msg)
        open_btn = box.addButton("Ouvrir le dossier", QMessageBox.AcceptRole)
        box.addButton("OK", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() == open_btn:
            _open_folder(self.out_dir)
