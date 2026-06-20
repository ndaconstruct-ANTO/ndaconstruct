"""Generate AI images with OpenAI and write them to disk."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .providers.openai_image import OpenAIImageProvider

#: Default subject/style prompt: a cute 3D Pixar-style lion cub on white.
DEFAULT_PROMPT = (
    "A cute, friendly baby lion cub standing upright on two legs, soft fluffy "
    "golden fur, big round expressive eyes, gentle smile, adorable, full body, "
    "centered, 3D Pixar-style render, soft studio lighting, high detail, "
    "isolated on a plain white background"
)


@dataclass
class ImageResult:
    index: int
    path: Path
    prompt: str


def generate_images(
    count: int,
    output_dir: Path,
    *,
    prompt: str = DEFAULT_PROMPT,
    size: str = "1024x1024",
) -> list[ImageResult]:
    """Generate ``count`` images for ``prompt`` and write PNGs to ``output_dir``."""
    if count < 1:
        raise ValueError("count must be at least 1")

    output_dir.mkdir(parents=True, exist_ok=True)
    provider = OpenAIImageProvider()

    results: list[ImageResult] = []
    for i in range(1, count + 1):
        data = provider.generate_image(prompt, size=size)
        path = output_dir / f"image_{i:03d}.png"
        path.write_bytes(data)
        results.append(ImageResult(index=i, path=path, prompt=prompt))

    return results
