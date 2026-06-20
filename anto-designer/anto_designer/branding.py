"""Identité visuelle d'Anto Designer (entièrement configurable).

Modifier ce fichier (ou le JSON de thème) suffit à changer nom, sous-titre,
couleurs, icône — sans toucher au reste du code.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Branding:
    app_name: str = "ANTO DESIGNER"
    subtitle: str = "NFT Collection Studio"
    full_name: str = "ANTO DESIGNER — NFT Collection Studio"
    tagline: str = "Crée tes collections NFT, en local, gratuitement."
    logo_path: str = ""  # défini plus tard, après validation des propositions
    icon_path: str = ""

    # Thème moderne, premium, clair et lisible (couleurs par défaut).
    theme: dict = field(
        default_factory=lambda: {
            "name": "Premium Light",
            "bg": "#F5F6F8",
            "surface": "#FFFFFF",
            "primary": "#6C4DF6",      # violet premium
            "primary_dark": "#4B33B5",
            "accent": "#F2B705",       # or
            "text": "#1B1D23",
            "text_muted": "#6B7280",
            "success": "#2E9E5B",
            "warning": "#E0A800",
            "danger": "#D64545",
            "radius": 12,
        }
    )


BRANDING = Branding()
