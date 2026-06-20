"""Éditeur de calques : importer une image, rendre le fond transparent,
gommer, ajuster à la taille de la collection, enregistrer en PNG transparent.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSlider, QVBoxLayout, QWidget,
)

from .. import imageops, pnglib, service

_PREVIEW_MAX = 440


class _Canvas(QLabel):
    clicked = Signal(int, int)  # coordonnées dans l'image source

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.scale = 1.0
        self._active = False

    def set_eraser(self, on: bool):
        self._active = on

    def mousePressEvent(self, e):
        self._emit(e)

    def mouseMoveEvent(self, e):
        if e.buttons():
            self._emit(e)

    def _emit(self, e):
        if not self._active or self.scale <= 0:
            return
        x = int(e.position().x() / self.scale)
        y = int(e.position().y() / self.scale)
        self.clicked.emit(x, y)


class LayerEditor(QWidget):
    def __init__(self, conn, collection, paths):
        super().__init__()
        self.conn = conn
        self.collection = collection
        self.paths = paths
        self.buf = None
        self.w = self.h = 0
        self._qbytes = None

        self.setWindowTitle(f"Éditeur de calques — {collection.name}")
        self.resize(620, 720)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.addWidget(QLabel(
            "1) Importez une image  2) Rendez le fond transparent  "
            "3) Ajustez à la taille  4) Enregistrez comme calque."))

        b_open = QPushButton("📂 Importer une image…")
        b_open.clicked.connect(self._open)
        root.addWidget(b_open)

        self.canvas = _Canvas()
        self.canvas.clicked.connect(self._erase_at)
        self.canvas.setMinimumHeight(_PREVIEW_MAX)
        root.addWidget(self.canvas)

        # Détourage
        tol = QHBoxLayout()
        tol.addWidget(QLabel("Tolérance fond :"))
        self.tol = QSlider(Qt.Horizontal); self.tol.setRange(5, 120); self.tol.setValue(32)
        tol.addWidget(self.tol)
        b_bg = QPushButton("✨ Fond transparent (auto)")
        b_bg.clicked.connect(self._remove_bg)
        tol.addWidget(b_bg)
        root.addLayout(tol)

        # Gomme
        er = QHBoxLayout()
        self.eraser = QCheckBox("Gomme (cliquez/glissez sur l'image)")
        self.eraser.toggled.connect(self.canvas.set_eraser)
        er.addWidget(self.eraser)
        er.addWidget(QLabel("Taille :"))
        self.brush = QSlider(Qt.Horizontal); self.brush.setRange(2, 80); self.brush.setValue(16)
        er.addWidget(self.brush)
        root.addLayout(er)

        b_fit = QPushButton(
            f"📐 Ajuster à la taille de la collection ({self.collection.width}px)")
        b_fit.clicked.connect(self._fit)
        root.addWidget(b_fit)

        # Enregistrement
        save_row = QHBoxLayout()
        save_row.addWidget(QLabel("Catégorie :"))
        self.cat = QLineEdit("Style")
        save_row.addWidget(self.cat)
        save_row.addWidget(QLabel("Nom :"))
        self.layer_name = QLineEdit("nouveau")
        save_row.addWidget(self.layer_name)
        root.addLayout(save_row)
        b_save = QPushButton("💾 Enregistrer comme calque")
        b_save.clicked.connect(self._save)
        root.addWidget(b_save)

        self.status = QLabel(""); self.status.setWordWrap(True)
        root.addWidget(self.status)

    # -- image ----------------------------------------------------------------
    def _open(self):
        filt = "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        path, _ = QFileDialog.getOpenFileName(self, "Importer une image", "", filt)
        if not path:
            return
        try:
            self.w, self.h, self.buf = self._load(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Import", f"Impossible d'ouvrir : {exc}")
            return
        self.layer_name.setText(Path(path).stem)
        self._refresh()

    def _load(self, path):
        p = Path(path)
        if p.suffix.lower() == ".png":
            return pnglib.read_rgba(p)
        # autres formats : nécessitent Pillow
        try:
            from PIL import Image
        except ImportError:
            raise RuntimeError("Pour les JPG/autres, installez Pillow. PNG OK sans.")
        img = Image.open(p).convert("RGBA")
        return img.width, img.height, bytearray(img.tobytes())

    def _refresh(self):
        if self.buf is None:
            return
        self._qbytes = bytes(self.buf)
        img = QImage(self._qbytes, self.w, self.h, self.w * 4, QImage.Format_RGBA8888)
        scale = min(_PREVIEW_MAX / self.w, _PREVIEW_MAX / self.h, 1.0)
        self.canvas.scale = scale
        pix = QPixmap.fromImage(img).scaled(
            int(self.w * scale), int(self.h * scale),
            Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.canvas.setPixmap(pix)
        self.canvas.setFixedSize(pix.size())

    # -- outils ---------------------------------------------------------------
    def _remove_bg(self):
        if self.buf is None:
            return
        cleared = imageops.remove_background(self.buf, self.w, self.h,
                                             tolerance=self.tol.value())
        self.status.setText(f"Fond rendu transparent ({cleared} pixels).")
        self._refresh()

    def _erase_at(self, x, y):
        if self.buf is None:
            return
        imageops.erase_circle(self.buf, self.w, self.h, x, y, self.brush.value())
        self._refresh()

    def _fit(self):
        if self.buf is None:
            return
        cw, ch = self.collection.width, self.collection.height
        self.buf = imageops.fit_to_canvas(self.buf, self.w, self.h, cw, ch)
        self.w, self.h = cw, ch
        self.status.setText(f"Ajusté à {cw}×{ch}.")
        self._refresh()

    def _save(self):
        if self.buf is None:
            QMessageBox.information(self, "Enregistrer", "Importez d'abord une image.")
            return
        cw, ch = self.collection.width, self.collection.height
        if (self.w, self.h) != (cw, ch):
            self._fit()
        assets = Path(self.paths["collections"]) / self.collection.slug / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        name = self.layer_name.text().strip() or "calque"
        out = assets / f"{self.cat.text().strip() or 'Divers'}_{name}.png"
        pnglib.write_rgba(out, self.w, self.h, self.buf)
        try:
            res = service.add_layer_file(self.conn, self.collection,
                                         self.cat.text().strip() or "Divers", out,
                                         name=name)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Enregistrer", f"Échec : {exc}")
            return
        self.status.setText(f"✅ Calque ajouté : {res['category']} / {res['layer']}")
