"""Assistant guidé pas-à-pas (avec explications à chaque étape).

Accompagne un utilisateur novice : créer une collection → préparer/importer des
calques → générer → voir le résultat. Chaque page explique quoi faire.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QLabel, QLineEdit, QMessageBox, QProgressDialog, QPushButton,
    QSpinBox, QVBoxLayout, QWizard, QWizardPage,
)

from .. import service, store


def _open_folder(path) -> None:
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


def _explain(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setTextFormat(Qt.RichText)
    return lbl


class IntroPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Bienvenue dans l'assistant ANTO DESIGNER 🦁")
        self.setSubTitle("Cet assistant vous guide, étape par étape.")
        lay = QVBoxLayout(self)
        lay.addWidget(_explain(
            "Nous allons créer une <b>collection NFT</b> ensemble.<br><br>"
            "Le principe : un <b>même personnage</b> de base, sur lequel on "
            "superpose des <b>calques</b> (pelage, yeux, tenue, chaussures, "
            "objet…). En les combinant, le logiciel crée des <b>centaines "
            "d'images uniques</b>, automatiquement, <b>sur votre ordinateur</b>.<br><br>"
            "👉 Cliquez sur <b>Suivant</b> pour commencer."))


class CollectionPage(QWizardPage):
    def __init__(self, wizard_ref):
        super().__init__()
        self._wiz = wizard_ref
        self.setTitle("Étape 1 — Créer la collection")
        self.setSubTitle("Donnez un nom et choisissez la taille des images.")
        lay = QVBoxLayout(self)
        lay.addWidget(_explain(
            "Le <b>nom</b> identifie votre collection. La <b>taille</b> est en "
            "pixels (carré). 2048 = haute qualité. Tous vos calques devront "
            "avoir <b>cette même taille</b>."))
        lay.addWidget(QLabel("Nom de la collection :"))
        self.name = QLineEdit("Mes Lionceaux")
        lay.addWidget(self.name)
        lay.addWidget(QLabel("Taille (carré, en pixels) :"))
        self.size = QSpinBox(); self.size.setRange(64, 8192)
        self.size.setSingleStep(256); self.size.setValue(2048)
        lay.addWidget(self.size)
        self.status = _explain("")
        lay.addWidget(self.status)

    def validatePage(self):
        try:
            self._wiz.collection = service.new_collection(
                self._wiz.conn, self.name.text().strip() or "Ma collection",
                int(self.size.value()), int(self.size.value()))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Création", f"Échec : {exc}")
            return False
        return True


class LayersPage(QWizardPage):
    def __init__(self, wizard_ref):
        super().__init__()
        self._wiz = wizard_ref
        self.setTitle("Étape 2 — Préparer les calques")
        self.setSubTitle("Organisez vos images, un sous-dossier par catégorie.")
        lay = QVBoxLayout(self)
        lay.addWidget(_explain(
            "Vos calques sont des <b>images PNG transparentes</b> de la même "
            "taille que la collection. Rangez-les ainsi (le numéro donne "
            "l'ordre d'empilement) :<br>"
            "<pre>1_Fur/    2_Eyes/    3_Style/    4_Shoes/    5_Objet (opt)/</pre>"
            "« (opt) » = catégorie facultative.<br><br>"
            "Pas encore de calques ? Créez un <b>dossier exemple</b> prêt à "
            "remplir, ou ouvrez plus tard l'<b>Éditeur de calques</b> pour "
            "détourer vos propres images."))
        b = QPushButton("📁 Créer un dossier exemple (structure prête)")
        b.clicked.connect(self._make_example)
        lay.addWidget(b)
        self.status = _explain("")
        lay.addWidget(self.status)

    def _make_example(self):
        folder = QFileDialog.getExistingDirectory(self, "Où créer le dossier exemple ?")
        if not folder:
            return
        target = Path(folder) / "calques_exemple"
        try:
            service.create_example_layers_template(target, self._wiz.collection)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Exemple", f"Échec : {exc}")
            return
        self.status.setText(f"✅ Dossier créé : {target}")
        _open_folder(target)


class ImportPage(QWizardPage):
    def __init__(self, wizard_ref):
        super().__init__()
        self._wiz = wizard_ref
        self._imported = False
        self.setTitle("Étape 3 — Importer les calques")
        self.setSubTitle("Indiquez le dossier qui contient vos catégories.")
        lay = QVBoxLayout(self)
        lay.addWidget(_explain(
            "Choisissez le dossier <b>parent</b> (celui qui contient "
            "1_Fur, 2_Eyes, …). Le logiciel crée les catégories et range vos "
            "calques. Les images de mauvaise taille sont ignorées et signalées."))
        b = QPushButton("📥 Choisir le dossier de calques…")
        b.clicked.connect(self._import)
        lay.addWidget(b)
        self.status = _explain("")
        lay.addWidget(self.status)

    def _import(self):
        folder = QFileDialog.getExistingDirectory(self, "Dossier de calques")
        if not folder:
            return
        try:
            rep = service.import_layers_from_folder(self._wiz.conn,
                                                    self._wiz.collection, folder)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Import", f"Échec : {exc}")
            return
        msg = (f"✅ {rep['categories']} catégorie(s), {rep['layers']} calque(s) importé(s).")
        if rep["skipped"]:
            msg += f" {len(rep['skipped'])} ignoré(s) (mauvaise taille)."
        self.status.setText(msg)
        self._imported = rep["layers"] > 0
        self.completeChanged.emit()

    def isComplete(self):
        return self._imported


class GeneratePage(QWizardPage):
    def __init__(self, wizard_ref):
        super().__init__()
        self._wiz = wizard_ref
        self._done = False
        self.setTitle("Étape 4 — Générer la collection")
        self.setSubTitle("Choisissez combien d'images créer.")
        lay = QVBoxLayout(self)
        lay.addWidget(_explain(
            "Le logiciel combine vos calques en <b>images uniques</b> (sans "
            "doublon) et crée pour chacune un fichier <b>image</b> + des "
            "<b>métadonnées NFT</b>. Choisissez le nombre puis cliquez "
            "<b>Générer</b>."))
        lay.addWidget(QLabel("Nombre d'images :"))
        self.count = QSpinBox(); self.count.setRange(1, 100000); self.count.setValue(10)
        lay.addWidget(self.count)
        b = QPushButton("⚙️ Générer maintenant")
        b.clicked.connect(self._generate)
        lay.addWidget(b)
        self.status = _explain("")
        lay.addWidget(self.status)

    def _generate(self):
        col = self._wiz.collection
        out_dir = Path(self._wiz.paths["collections"]) / col.slug / "output"
        count = int(self.count.value())
        progress = QProgressDialog("Génération…", "Annuler", 0, count, self)
        progress.setWindowModality(Qt.WindowModal)

        class _Stop:
            def is_set(_s):
                return progress.wasCanceled()

        try:
            summary = service.generate(self._wiz.conn, col, count, out_dir,
                                       seed=42, progress_cb=lambda i, t: progress.setValue(i),
                                       stop_event=_Stop())
        except Exception as exc:  # noqa: BLE001
            progress.close()
            QMessageBox.warning(self, "Génération", f"Échec : {exc}")
            return
        progress.setValue(count)
        self._wiz.last_output = out_dir
        self.status.setText(
            f"✅ {summary['generated']} image(s) créée(s) — {out_dir}")
        self._done = True
        self.completeChanged.emit()

    def isComplete(self):
        return self._done


class DonePage(QWizardPage):
    def __init__(self, wizard_ref):
        super().__init__()
        self._wiz = wizard_ref
        self.setTitle("Terminé ! 🎉")
        self.setSubTitle("Votre collection est prête.")
        lay = QVBoxLayout(self)
        lay.addWidget(_explain(
            "Vos images et leurs métadonnées sont enregistrées sur votre "
            "ordinateur. Vous pouvez relancer l'assistant quand vous voulez, "
            "ajouter des calques, ou régénérer davantage d'images."))
        b = QPushButton("📂 Ouvrir le dossier de mes images")
        b.clicked.connect(self._open)
        lay.addWidget(b)

    def _open(self):
        out = getattr(self._wiz, "last_output", None)
        if out:
            _open_folder(out)


class GuidedWizard(QWizard):
    def __init__(self, conn, paths, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.paths = paths
        self.collection = None
        self.last_output = None
        self.setWindowTitle("Assistant ANTO DESIGNER")
        self.setWizardStyle(QWizard.ModernStyle)
        self.resize(680, 520)
        self.addPage(IntroPage())
        self.addPage(CollectionPage(self))
        self.addPage(LayersPage(self))
        self.addPage(ImportPage(self))
        self.addPage(GeneratePage(self))
        self.addPage(DonePage(self))
