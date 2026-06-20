"""Command line entry point for ndaconstruct.

Usage:
    python -m src.main generate --count 10 --provider openai --real
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .generator import FORMATS, generate_ndas
from .providers import PROVIDERS, ProviderError, get_provider


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ndaconstruct",
        description="Generate Non-Disclosure Agreements via an LLM provider.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    gen = subparsers.add_parser("generate", help="Generate one or more NDAs.")
    gen.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of NDAs to generate (default: 1).",
    )
    gen.add_argument(
        "--provider",
        choices=sorted(PROVIDERS),
        default="openai",
        help="LLM provider to use when --real is set (default: openai).",
    )
    gen.add_argument(
        "--real",
        action="store_true",
        help="Call the real provider API. Without this flag a free offline "
        "mock provider is used (no API key required).",
    )
    gen.add_argument(
        "--format",
        choices=FORMATS,
        default="txt",
        help="Output format: 'txt' (default) or 'png' image.",
    )
    gen.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory to write generated NDAs into (default: ./output).",
    )
    gen.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible NDA parameters.",
    )
    gen.set_defaults(func=_cmd_generate)

    return parser


def _cmd_generate(args: argparse.Namespace) -> int:
    try:
        provider = get_provider(args.provider, real=args.real)
    except ProviderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    mode = f"{provider.name} (real)" if args.real else f"{provider.name} (mock/offline)"
    print(f"Generating {args.count} NDA(s) using provider: {mode}")

    try:
        results = generate_ndas(
            provider,
            count=args.count,
            output_dir=args.output_dir,
            seed=args.seed,
            fmt=args.format,
        )
    except (ProviderError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for result in results:
        r = result.request
        kind = "mutual" if r.mutual else "one-way"
        print(
            f"  [{result.index:>3}] {result.path}  "
            f"({r.disclosing_party} <-> {r.receiving_party}, {kind}, {r.term_years}y)"
        )

    print(f"\nDone. Wrote {len(results)} file(s) to {args.output_dir}/")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
