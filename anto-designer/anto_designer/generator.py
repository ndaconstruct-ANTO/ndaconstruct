"""Générateur automatique : combinaisons -> images -> métadonnées -> base.

Compose les calques, contrôle la qualité, évite les doublons (signature +
hash d'image), n'écrase jamais un fichier, et peut être interrompu proprement.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import combination, layer_engine, metadata, rarity, store, validation
from .dedup import DuplicateTracker


def _hex_to_rgba(h: str, transparent: bool) -> tuple:
    if transparent:
        return (0, 0, 0, 0)
    h = (h or "#FFFFFF").lstrip("#")
    if len(h) == 6:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)
    return (255, 255, 255, 255)


def _unique_path(directory: Path, base: str, ext: str) -> Path:
    """Retourne un chemin qui n'écrase jamais un fichier existant."""
    candidate = directory / f"{base}{ext}"
    n = 2
    while candidate.exists():
        candidate = directory / f"{base}_v{n}{ext}"
        n += 1
    return candidate


def generate_collection(conn, collection, count: int, out_dir: Path, *,
                        seed: int | None = None, progress_cb=None, stop_event=None,
                        require_square=True) -> dict:
    """Génère ``count`` NFT. Retourne un résumé (généré/refusé/doublons/rapports)."""
    out_dir = Path(out_dir)
    images_dir = out_dir / "images"
    meta_dir = out_dir / "metadata"
    reports_dir = out_dir / "reports"
    for d in (images_dir, meta_dir, reports_dir):
        d.mkdir(parents=True, exist_ok=True)

    categories = store.list_categories(conn, collection.id)
    tracker = DuplicateTracker(store.existing_signatures(conn, collection.id))
    combos = combination.generate(conn, collection, count, seed=seed, tracker=tracker)

    background = _hex_to_rgba(collection.background_color,
                             collection.background_mode == "transparent")

    summary = {"generated": 0, "rejected": 0, "duplicate_images": 0,
               "reports": [], "stopped": False}

    total = len(combos)
    for i, combo in enumerate(combos, start=1):
        if stop_event is not None and stop_event.is_set():
            summary["stopped"] = True
            break

        paths = [l.file_path for l in combo.ordered_layers]
        png = layer_engine.composite(paths, collection.width, collection.height,
                                     background=background)

        img_hash = layer_engine.image_hash(png)
        if not tracker.add_image(img_hash):
            summary["duplicate_images"] += 1
            continue

        report = validation.build_report(combo, categories, png,
                                        collection.width, collection.height,
                                        require_square=require_square)
        base = metadata.file_base(collection, combo, categories)

        if report["status"] == validation.REJECT:
            summary["rejected"] += 1
            summary["reports"].append(report)
            continue

        img_path = _unique_path(images_dir, base, ".png")
        img_path.write_bytes(png)
        meta = metadata.build_metadata(collection, combo, categories, img_path.name)
        (meta_dir / f"{base}.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        traits = [(c.name, (combo.chosen[c.slug].id if combo.chosen[c.slug] else None),
                   (combo.chosen[c.slug].trait_value if combo.chosen[c.slug] else "Aucun"))
                  for c in categories]
        store.record_generated(conn, collection.id, combo.token_id, combo.signature,
                              img_path.name, img_hash, report["status"], traits)

        summary["generated"] += 1
        summary["reports"].append(report)
        if progress_cb:
            progress_cb(i, total)

    # Rapports collectifs.
    dist = rarity.distribution(combos)
    (reports_dir / "rarity.json").write_text(
        json.dumps(dist, ensure_ascii=False, indent=2), encoding="utf-8")
    status_counts = {"VALIDÉ": 0, "À CORRIGER": 0, "REFUSÉ": 0}
    for r in summary["reports"]:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1
    (reports_dir / "validation_summary.json").write_text(
        json.dumps(status_counts, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["validation_summary"] = status_counts
    summary["rarity"] = dist
    return summary
