"""Génère la collection de lionceaux directement SUR FOND TRANSPARENT
(détourage 'scalpel' par l'IA, à partir de l'image maître), écrit les
métadonnées, puis réassemble sur les fonds contrastants.

Usage : python -m tools.generate_transparent_collection [N] [seed]
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.combination_generator import generate_combinations          # noqa: E402
from src.image_provider import ImageProviderError, OpenAIImageProvider  # noqa: E402
from src.metadata_generator import build_metadata, file_base         # noqa: E402
from src.prompt_builder import PromptBuilder                         # noqa: E402
from src.rarity_engine import assign_rarity                         # noqa: E402
from src.utils import PROJECT_ROOT, ensure_dir, load_config, write_json  # noqa: E402

SIZE = "1024x1024"


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 2026

    cfg = load_config()
    cfg.format["resolution"] = 1024  # sortie réelle de l'API (carré)
    combos = generate_combinations(cfg, n, seed=seed)
    assign_rarity(cfg, combos)

    # +1 LÉGENDAIRE spécial garanti (Roi, fourrure blanche, yeux dorés) -> fond OR.
    from src.combination_generator import Combination
    king = cfg.style_by_code["KING"]
    special = Combination(
        id=n + 1, uid=f"LION-{n + 1:04d}",
        fur=cfg.fur_by_code["WHITE"], eye_left=cfg.eye_by_code["GOLD"],
        eye_right=cfg.eye_by_code["GOLD"], style=king,
        held_object=king.held_object, seed=(seed * 7 + 101) & 0x7FFFFFFF,
    )
    special.rarity_tier = "Legendary"  # force le fond OR pailleté
    combos.append(special)
    builder = PromptBuilder(cfg)
    provider = OpenAIImageProvider()

    master = (PROJECT_ROOT / cfg.master_model["reference_image"]).read_bytes()
    out_t = ensure_dir(PROJECT_ROOT / "output" / "transparent")
    out_m = ensure_dir(PROJECT_ROOT / "output" / "metadata")

    done = skipped = 0
    t0 = time.time()
    for i, combo in enumerate(combos, 1):
        p = builder.build(combo)
        base = file_base(combo, cfg)
        try:
            data = provider.generate(p["positive"], p["negative"], size=SIZE,
                                     seed=combo.seed, reference=master, transparent=True)
        except ImageProviderError as exc:
            print(f"  ⚠️ {combo.uid} ignoré: {exc}")
            skipped += 1
            continue
        (out_t / f"{base}.png").write_bytes(data)
        write_json(out_m / f"LION_{combo.id:04d}_METADATA.json",
                   build_metadata(combo, cfg, f"{base}.png"))
        done += 1
        if i % 5 == 0:
            print(f"  {i}/{len(combos)} (ok={done}, skip={skipped}, {time.time()-t0:.0f}s)")

    print(f"Génération transparente terminée: {done} ok, {skipped} ignorés "
          f"en {time.time()-t0:.0f}s")

    # Réassemblage sur fonds contrastants (+ marge constante + mapping).
    from tools.build_backgrounds import build
    build()
    print("TRANSPARENT_COLLECTION_DONE")


if __name__ == "__main__":
    main()
