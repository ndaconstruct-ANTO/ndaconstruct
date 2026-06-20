"""Fenêtre principale (écran d'accueil) d'Anto Designer."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from .. import __version__
from ..branding import BRANDING
from .. import config
from ..logging_setup import diagnostic_report, setup_logging


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.paths = config.ensure_dirs()
        self.logger = setup_logging(self.paths["logs"])
        self.setWindowTitle(BRANDING.full_name)
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

        # Cartes d'actions.
        grid = QGridLayout(); grid.setSpacing(16)
        actions = [
            ("➕ Nouvelle collection", self._todo),
            ("📂 Ouvrir une collection", self._todo),
            ("🧪 Lancer la démo", self._run_demo),
            ("🖼️ Bibliothèque de calques", self._todo),
            ("⚙️ Générer une collection", self._todo),
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
    def _todo(self) -> None:
        QMessageBox.information(
            self, BRANDING.app_name,
            "Écran en cours de construction dans cette première version.\n"
            "Le moteur (calques, génération, rareté, métadonnées) est déjà "
            "fonctionnel et testé — voir la démo.")

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
