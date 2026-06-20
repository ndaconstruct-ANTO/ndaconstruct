"""Lancement de l'application graphique Anto Designer."""

from __future__ import annotations

import sys


def run() -> int:
    from PySide6.QtWidgets import QApplication

    from .main_window import MainWindow
    from .theme import stylesheet

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("ANTO DESIGNER")
    app.setStyleSheet(stylesheet())
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
