"""Lancement de l'application graphique Anto Designer."""

from __future__ import annotations

import sys


def run() -> int:
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from .main_window import MainWindow
    from .theme import stylesheet
    from ..resources import icon_path

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("ANTO DESIGNER")
    ico = icon_path()
    if ico:
        app.setWindowIcon(QIcon(ico))
    app.setStyleSheet(stylesheet())
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
