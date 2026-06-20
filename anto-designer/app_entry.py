"""Point d'entrée pour PyInstaller (application fenêtrée AntoDesigner.exe)."""

import sys

from anto_designer.gui.app import run

if __name__ == "__main__":
    sys.exit(run())
