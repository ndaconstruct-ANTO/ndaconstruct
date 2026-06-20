"""Journalisation lisible et rapport de diagnostic (sans données privées)."""

from __future__ import annotations

import logging
import platform
import sys
from pathlib import Path

from . import __version__
from .layer_engine import backend_name

_LOGGER_NAME = "anto_designer"


def setup_logging(log_dir: Path) -> logging.Logger:
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(log_dir / "anto_designer.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)
    return logger


def diagnostic_report(log_dir: Path, tail: int = 60) -> str:
    """Rapport copiable : versions + dernières lignes de journal (anonymisé)."""
    lines = [
        "=== ANTO DESIGNER — Rapport de diagnostic ===",
        f"Version       : {__version__}",
        f"Python        : {sys.version.split()[0]}",
        f"OS            : {platform.system()} {platform.release()}",
        f"Backend image : {backend_name()}",
        "",
        "--- Dernières entrées du journal ---",
    ]
    log_file = Path(log_dir) / "anto_designer.log"
    if log_file.exists():
        content = log_file.read_text(encoding="utf-8").splitlines()
        lines.extend(content[-tail:])
    else:
        lines.append("(aucun journal)")
    return "\n".join(lines)
