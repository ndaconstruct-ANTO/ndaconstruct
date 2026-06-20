"""Core generation loop: turn a count + provider into NDA files on disk."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from .models import NDARequest
from .providers import Provider


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
) -> list[GenerationResult]:
    """Generate ``count`` NDAs using ``provider`` and write them to ``output_dir``.

    Returns a list of :class:`GenerationResult` describing what was written.
    """
    if count < 1:
        raise ValueError("count must be at least 1")

    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    results: list[GenerationResult] = []
    for i in range(1, count + 1):
        request = NDARequest.random(index=i, rng=rng)
        text = provider.generate(request)

        filename = f"nda_{i:03d}.txt"
        path = output_dir / filename
        path.write_text(text, encoding="utf-8")

        results.append(GenerationResult(index=i, request=request, path=path))

    return results
