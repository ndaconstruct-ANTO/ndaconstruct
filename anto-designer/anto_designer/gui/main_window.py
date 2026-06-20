"""Fenêtre principale (écran d'accueil) d'Anto Designer."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from .. import __version__
from ..branding import BRANDING
from .. import config, database, service, store
from ..logging_setup import diagnostic_report, setup_logging
from ..resources import icon_path
from .collection_window import CollectionWindow
from .dialogs import NewCollectionDialog
from .editor import LayerEditor
from .wizard import GuidedWizard


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.paths = config.ensure_dirs()
        self.logger = setup_logging(self.paths["logs"])
        self.conn = database.connect(self.paths["db"])
        self._open_windows = []  # garde les références (évite la fermeture auto)
        self.setWindowTitle(BRANDING.full_name)
        ico = icon_path()
        if ico:
            self.setWindowIcon(QIcon(ico))
        self.resize(1100, 720)
        self._build_home()

    def _build_home(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(24)

        # En-tête (identité visuelle).
        header = QVBoxLayout()
        title = QLabel(BRANDING.app_name); title.setObjectName("Title")
        sub = QLabel(BRANDING.subtitle); sub.setObjectName("Subtitle")
        tagline = QLabel(BRANDING.tagline); tagline.setObjectName("Subtitle")
        header.addWidget(title)
        header.addWidget(sub)
        header.addWidget(tagline)
        root.addLayout(header)

        # Bouton principal : assistant guidé (recommandé).
        assistant = QPushButton("🚀 Assistant guidé (recommandé) — créer une collection pas à pas")
        assistant.clicked.connect(self._open_wizard)
        root.addWidget(assistant)

        # Cartes d'actions.
        grid = QGridLayout(); grid.setSpacing(16)
        actions = [
            ("➕ Nouvelle collection", self._new_collection),
            ("📂 Ouvrir une collection", self._open_collection),
            ("🖼️ Éditeur de calques", self._open_editor),
            ("🗂️ Bibliothèque / Générer", self._open_collection),
            ("🧪 Lancer la démo", self._run_demo),
            ("ℹ️ À propos", self._about),
        ]
        for i, (label, handler) in enumerate(actions):
            btn = QPushButton(label)
            btn.clicked.connect(handler)
            grid.addWidget(btn, i // 3, i % 3)
        card = QFrame(); card.setObjectName("Card")
        card_lay = QVBoxLayout(card); card_lay.addLayout(grid)
        root.addWidget(card)

        # Pied de page.
        footer = QHBoxLayout()
        diag = QPushButton("Copier le rapport de diagnostic"); diag.setObjectName("Ghost")
        diag.clicked.connect(self._copy_diagnostic)
        footer.addWidget(diag)
        footer.addStretch(1)
        footer.addWidget(QLabel(f"v{__version__} — 100% local"))
        root.addStretch(1)
        root.addLayout(footer)

        self.setCentralWidget(central)

    # -- handlers -------------------------------------------------------------
    def _open_window(self, collection) -> None:
        win = CollectionWindow(self.conn, collection, self.paths)
        self._open_windows.append(win)
        win.show()

    def _open_wizard(self) -> None:
        wiz = GuidedWizard(self.conn, self.paths, self)
        self._open_windows.append(wiz)
        wiz.show()

    def _pick_collection(self):
        cols = store.list_collections(self.conn)
        if not cols:
            return None
        if len(cols) == 1:
            return cols[0]
        from PySide6.QtWidgets import QInputDialog
        names = [f"{c.name}  ({c.width}×{c.height})" for c in cols]
        choice, ok = QInputDialog.getItem(
            self, "Choisir une collection", "Collection :", names, 0, False)
        return cols[names.index(choice)] if ok else None

    def _open_editor(self) -> None:
        col = self._pick_collection()
        if col is None:
            QMessageBox.information(
                self, "Éditeur de calques",
                "Créez d'abord une collection (« Nouvelle collection » ou "
                "l'assistant guidé).")
            return
        ed = LayerEditor(self.conn, col, self.paths)
        self._open_windows.append(ed)
        ed.show()

    def _new_collection(self) -> None:
        dlg = NewCollectionDialog(self)
        if not dlg.exec():
            return
        name, size = dlg.values()
        try:
            collection = service.new_collection(self.conn, name, size, size)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Nouvelle collection", f"Échec : {exc}")
            return
        self._open_window(collection)

    def _open_collection(self) -> None:
        cols = store.list_collections(self.conn)
        if not cols:
            QMessageBox.information(
                self, "Ouvrir une collection",
                "Aucune collection pour l'instant.\nCliquez « Nouvelle collection ».")
            return
        from PySide6.QtWidgets import QInputDialog
        names = [f"{c.name}  ({c.width}×{c.height})" for c in cols]
        choice, ok = QInputDialog.getItem(
            self, "Ouvrir une collection", "Collection :", names, 0, False)
        if not ok:
            return
        self._open_window(cols[names.index(choice)])

    def _run_demo(self) -> None:
        try:
            from demo.build_demo import build_demo
            summary = build_demo(count=8)
            QMessageBox.information(
                self, "Démo", f"Démo générée :\n{summary}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Démo", f"Échec de la démo : {exc}")

    def _about(self) -> None:
        QMessageBox.about(
            self, "À propos",
            f"<b>{BRANDING.full_name}</b><br>v{__version__}<br><br>"
            "Studio local de création de collections NFT par calques.<br>"
            "100% local · hors-ligne · sans API payante (cœur calques).")

    def _copy_diagnostic(self) -> None:
        from PySide6.QtWidgets import QApplication
        report = diagnostic_report(self.paths["logs"])
        QApplication.clipboard().setText(report)
        QMessageBox.information(self, "Diagnostic", "Rapport copié dans le presse-papiers.")
