"""Core generation loop: turn a count + provider into NDA files on disk."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from .models import NDARequest
from .providers import Provider
from .render import render_text_to_png

#: Output formats supported by the generator.
FORMATS = ("txt", "png")


@dataclass
class GenerationResult:
    """Outcome of a single NDA generation."""

    index: int
    request: NDARequest
    path: Path


def generate_ndas(
    provider: Provider,
    count: int,
    output_dir: Path,
    *,
    seed: int | None = None,
    fmt: str = "txt",
) -> list[GenerationResult]:
    """Generate ``count`` NDAs using ``provider`` and write them to ``output_dir``.

    ``fmt`` selects the on-disk format: ``"txt"`` for plain text or ``"png"`` for
    a rendered image. Returns a list of :class:`GenerationResult`.
    """
    if count < 1:
        raise ValueError("count must be at least 1")
    if fmt not in FORMATS:
        raise ValueError(f"unknown format '{fmt}'. Choose from: {', '.join(FORMATS)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    results: list[GenerationResult] = []
    for i in range(1, count + 1):
        request = NDARequest.random(index=i, rng=rng)
        text = provider.generate(request)

        if fmt == "png":
            path = output_dir / f"nda_{i:03d}.png"
            render_text_to_png(text, path)
        else:
            path = output_dir / f"nda_{i:03d}.txt"
            path.write_text(text, encoding="utf-8")

        results.append(GenerationResult(index=i, request=request, path=path))

    return results
