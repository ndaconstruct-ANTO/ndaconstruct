"""Re-découpe les transparents (poches enfermées + marge constante) puis
réassemble la collection avec fonds. N'altère JAMAIS les originaux fond blanc
(output/images), qui restent la source de vérité.
"""

from __future__ import annotations

import glob
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent / "anto-designer"))
sys.path.insert(0, str(ROOT))

from anto_designer import imageops, pnglib  # noqa: E402

WHITE_SRC = ROOT / "output" / "images"
TRANSP = ROOT / "output" / "transparent"
MARGIN = 0.08
TOL = 48


def recut():
    TRANSP.mkdir(parents=True, exist_ok=True)
    files = sorted(glob.glob(str(WHITE_SRC / "*.png")))
    t0 = time.time()
    for i, p in enumerate(files, 1):
        w, h, buf = pnglib.read_rgba(p)
        imageops.remove_background(buf, w, h, tolerance=TOL,
                                   remove_enclosed=True, max_hole_ratio=0.06)
        imageops.keep_largest_component(buf, w, h)  # enlève volutes/morceaux détachés
        buf = imageops.normalize_margins(buf, w, h, margin_ratio=MARGIN)
        pnglib.write_rgba(TRANSP / os.path.basename(p), w, h, buf)
        if i % 10 == 0:
            print(f"  re-découpe {i}/{len(files)} ({time.time()-t0:.0f}s)")
    print(f"Re-découpe terminée : {len(files)} images en {time.time()-t0:.0f}s")


if __name__ == "__main__":
    recut()
    # Réassemble avec les fonds (réserve + collection_avec_fonds + mapping).
    from tools.build_backgrounds import build
    build()
    print("RECUT_REBUILD_DONE")
