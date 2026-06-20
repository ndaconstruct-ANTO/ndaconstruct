"""Génération des métadonnées NFT, du CSV global et des registres."""

from __future__ import annotations

import csv
from pathlib import Path

from .combination_generator import Combination
from .utils import Config, ensure_dir, write_json


def file_base(combo: Combination, config: Config) -> str:
    """Nom de base du fichier (sans extension), selon le gabarit de nommage."""
    return config.naming_template.format(
        id=combo.id,
        fur_code=combo.fur.code,
        eye_code=combo.eye_left.code,
        style_code=combo.style.code,
    )


def build_metadata(combo: Combination, config: Config, image_filename: str) -> dict:
    """Métadonnées NFT : champs structurés (EN) + tableau d'attributs (FR)."""
    collection_name = config.collection.get("name", "LIONCEAUX NFT")
    return {
        "id": combo.uid,
        "name": f"Lion #{combo.id:04d}",
        "collection": collection_name,
        "description": config.collection.get("description", ""),
        "image": image_filename,
        "species": "Lion cub",
        "fur_color": combo.fur.name_en,
        "eye_color_left": combo.eye_left.name_en,
        "eye_color_right": combo.eye_right.name_en,
        "style": combo.style.name_en,
        "outfit": combo.style.outfit,
        "headwear": combo.style.headwear,
        "held_object": combo.held_object,
        "background": "Pure white",
        "camera": "Front view",
        "format": config.format.get("aspect_ratio", "1:1"),
        "rarity": combo.rarity_tier,
        "rarity_score": combo.rarity_score,
        "seed": combo.seed,
        "prompt_version": config.collection.get("prompt_version", "1.0"),
        # Tableau d'attributs compatible marketplaces (libellés FR).
        "attributes": [
            {"trait_type": "Pelage", "value": combo.fur.name_fr},
            {"trait_type": "Yeux gauche", "value": combo.eye_left.name_fr},
            {"trait_type": "Yeux droite", "value": combo.eye_right.name_fr},
            {"trait_type": "Style", "value": combo.style.name_fr},
            {"trait_type": "Objet", "value": combo.held_object},
            {"trait_type": "Hétérochromie", "value": "Oui" if combo.heterochromia else "Non"},
            {"trait_type": "Rareté", "value": combo.rarity_tier},
        ],
    }


def write_all(
    combos: list,
    config: Config,
    output_dir: Path,
    prompts: dict,
    reports: list,
    stats: dict,
) -> dict:
    """Écrit images-metadata, prompts, CSV, registres et statistiques.

    ``prompts`` : map uid -> {positive, negative}
    ``reports`` : liste de rapports de contrôle qualité
    Retourne un dictionnaire des chemins/compteurs produits.
    """
    output_dir = Path(output_dir)
    meta_dir = ensure_dir(output_dir / "metadata")
    prompt_dir = ensure_dir(output_dir / "prompts")
    report_dir = ensure_dir(output_dir / "reports")
    ensure_dir(output_dir / "images")

    csv_rows = []
    registry_ids = []
    registry_seeds = {}
    registry_combos = []

    for combo in combos:
        base = file_base(combo, config)
        image_filename = base + ".png"
        meta = build_metadata(combo, config, image_filename)

        # 1 fichier JSON par NFT (nom court selon la section 14).
        write_json(meta_dir / f"LION_{combo.id:04d}_METADATA.json", meta)

        # Prompts (positif + négatif) sauvegardés pour audit / réutilisation.
        p = prompts[combo.uid]
        (prompt_dir / f"{base}.txt").write_text(
            f"# {meta['name']} — {combo.uid}\n\n"
            f"## POSITIVE\n{p['positive']}\n\n## NEGATIVE\n{p['negative']}\n",
            encoding="utf-8",
        )

        csv_rows.append(
            {
                "id": combo.uid,
                "name": meta["name"],
                "image": image_filename,
                "fur": combo.fur.name_fr,
                "eye_left": combo.eye_left.name_fr,
                "eye_right": combo.eye_right.name_fr,
                "style": combo.style.name_fr,
                "object": combo.held_object,
                "heterochromia": combo.heterochromia,
                "rarity": combo.rarity_tier,
                "rarity_score": combo.rarity_score,
                "seed": combo.seed,
            }
        )
        registry_ids.append(combo.uid)
        registry_seeds[combo.uid] = combo.seed
        registry_combos.append(list(combo.key))

    # CSV global
    csv_path = output_dir / "collection.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)

    # Registres
    write_json(report_dir / "registry_ids.json", {"ids": registry_ids})
    write_json(report_dir / "registry_seeds.json", {"seeds": registry_seeds})
    write_json(report_dir / "registry_combinations.json", {"combinations": registry_combos})

    # Statistiques de rareté
    write_json(report_dir / "trait_stats.json", stats)

    # Rapports de contrôle qualité (détaillé + résumé)
    write_json(report_dir / "validation_reports.json", {"reports": reports})
    summary = {"VALIDÉ": 0, "À CORRIGER": 0, "REFUSÉ": 0}
    for r in reports:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    write_json(report_dir / "validation_summary.json", summary)

    return {
        "csv": str(csv_path),
        "metadata_dir": str(meta_dir),
        "prompts_dir": str(prompt_dir),
        "reports_dir": str(report_dir),
        "count": len(combos),
        "validation_summary": summary,
    }
