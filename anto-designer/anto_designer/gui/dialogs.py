"""Boîtes de dialogue : nouvelle collection, génération."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QSpinBox,
)


class NewCollectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nouvelle collection")
        form = QFormLayout(self)

        self.name = QLineEdit("Ma collection")
        self.size = QSpinBox()
        self.size.setRange(64, 8192)
        self.size.setSingleStep(256)
        self.size.setValue(2048)

        form.addRow("Nom de la collection :", self.name)
        form.addRow("Taille (carré, en pixels) :", self.size)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        return self.name.text().strip() or "Ma collection", int(self.size.value())


class GenerateDialog(QDialog):
    def __init__(self, parent=None, capacity: int = 0):
        super().__init__(parent)
        self.setWindowTitle("Générer une collection")
        form = QFormLayout(self)

        self.count = QSpinBox()
        self.count.setRange(1, 100000)
        self.count.setValue(min(10, capacity) or 10)

        self.use_seed = QCheckBox("Résultat reproductible (graine fixe)")
        self.use_seed.setChecked(True)
        self.seed = QSpinBox()
        self.seed.setRange(0, 2_000_000_000)
        self.seed.setValue(42)

        form.addRow("Nombre d'images :", self.count)
        if capacity:
            from PySide6.QtWidgets import QLabel
            form.addRow(QLabel(f"Combinaisons possibles : ~{capacity}"))
        form.addRow(self.use_seed)
        form.addRow("Graine :", self.seed)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        seed = int(self.seed.value()) if self.use_seed.isChecked() else None
        return int(self.count.value()), seed
