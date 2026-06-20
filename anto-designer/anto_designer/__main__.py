"""Point d'entrée : lance l'interface graphique si possible, sinon la CLI.

    python -m anto_designer            -> interface graphique (Anto Designer)
    python -m anto_designer.cli info   -> informations système
"""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from .gui.app import run
    except Exception as exc:  # PySide6 absent ou environnement sans affichage
        print("Interface graphique indisponible :", exc)
        print("Installez les dépendances : pip install -r requirements.txt")
        print("En attendant, la CLI fonctionne : python -m anto_designer.cli info")
        return 1
    return run()


if __name__ == "__main__":
    sys.exit(main())
