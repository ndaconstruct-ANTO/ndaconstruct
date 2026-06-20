"""Feuille de style (QSS) générée depuis le thème de branding."""

from __future__ import annotations

from ..branding import BRANDING


def stylesheet() -> str:
    t = BRANDING.theme
    r = t["radius"]
    return f"""
    QWidget {{
        background: {t['bg']};
        color: {t['text']};
        font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
        font-size: 14px;
    }}
    QFrame#Card, QWidget#Card {{
        background: {t['surface']};
        border-radius: {r}px;
    }}
    QLabel#Title {{ font-size: 26px; font-weight: 800; color: {t['text']}; }}
    QLabel#Subtitle {{ font-size: 14px; color: {t['text_muted']}; }}
    QPushButton {{
        background: {t['primary']};
        color: white;
        border: none;
        border-radius: {r}px;
        padding: 10px 16px;
        font-weight: 600;
    }}
    QPushButton:hover {{ background: {t['primary_dark']}; }}
    QPushButton#Ghost {{
        background: transparent;
        color: {t['primary']};
        border: 1px solid {t['primary']};
    }}
    """
