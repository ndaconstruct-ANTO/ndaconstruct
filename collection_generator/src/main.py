"""Interface en ligne de commande du générateur de collection NFT.

Exemples :
    # Mode simulation (par défaut, AUCUNE dépense) :
    python -m src.main generate --count 100

    # Lister les traits disponibles :
    python -m src.main list-traits

    # Génération RÉELLE d'images (autorisation explicite via --real) :
    python -m src.main generate --count 10 --provider openai --real
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .combination_generator import generate_combinations
from .duplicate_checker import DuplicateChecker
from .image_provider import ImageProviderError, get_provider
from .metadata_generator import file_base, write_all
from .prompt_builder import PromptBuilder
from .quality_control import REJECT, build_report
from .rarity_engine import assign_rarity, trait_statistics
from .utils import OUTPUT_DIR, ensure_dir, load_config

# Tailles supportées par l'API image d'OpenAI (le carré est imposé).
_OPENAI_SQUARE_SIZE = "1024x1024"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lionceaux",
        description="Génère une collection cohérente de lionceaux NFT.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="Générer des combinaisons (+ images si --real).")
    g.add_argument("--count", type=int, default=10, help="Nombre d'images (défaut: 10).")
    g.add_argument("--fur", nargs="*", default=None, help="Codes de pelage autorisés.")
    g.add_argument("--eyes", nargs="*", default=None, help="Codes d'yeux autorisés.")
    g.add_argument("--styles", nargs="*", default=None, help="Codes de style autorisés.")
    g.add_argument("--rarity", default=None, help="Filtrer les styles par palier de base.")
    g.add_argument("--resolution", type=int, default=None, help="Résolution carrée (px).")
    g.add_argument("--provider", default="openai", help="Fournisseur d'images réel.")
    g.add_argument(
        "--real",
        action="store_true",
        help="Génère RÉELLEMENT les images (peut être payant). Sans ce drapeau : simulation.",
    )
    g.add_argument("--seed", type=int, default=None, help="Seed globale (reproductible).")
    g.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Dossier de sortie.")
    g.add_argument("--fresh", action="store_true", help="Ignorer le registre existant.")
    g.add_argument("--preview", type=int, default=10, help="Nombre d'exemples affichés.")
    g.add_argument(
        "--max-retries",
        type=int,
        default=1,
        help="Régénérations max si une image réelle est REFUSÉE (défaut: 1).",
    )
    g.set_defaults(func=_cmd_generate)

    lt = sub.add_parser("list-traits", help="Lister pelages, yeux et styles disponibles.")
    lt.set_defaults(func=_cmd_list_traits)

    return parser


def _cmd_list_traits(args: argparse.Namespace) -> int:
    cfg = load_config()
    print(f"Pelages ({len(cfg.fur_colors)}) :")
    for t in cfg.fur_colors:
        print(f"  {t.code:<6} {t.name_fr} / {t.name_en}")
    print(f"\nYeux ({len(cfg.eye_colors)}) :")
    for t in cfg.eye_colors:
        print(f"  {t.code:<12} {t.name_fr} / {t.name_en}")
    print(f"\nStyles ({len(cfg.styles)}) :")
    for s in cfg.styles:
        print(f"  {s.code:<14} {s.name_fr:<22} objet: {s.held_object}")
    return 0


def _cmd_generate(args: argparse.Namespace) -> int:
    cfg = load_config()
    if args.resolution:
        cfg.format["resolution"] = args.resolution

    output_dir = ensure_dir(args.output_dir)

    checker = DuplicateChecker()
    if not args.fresh:
        checker.load_registry(output_dir / "reports" / "registry_combinations.json")

    try:
        combos = generate_combinations(
            cfg,
            args.count,
            allowed_fur=args.fur,
            allowed_eyes=args.eyes,
            allowed_styles=args.styles,
            rarity=args.rarity,
            seed=args.seed,
            checker=checker,
        )
    except (ValueError, RuntimeError) as exc:
        print(f"erreur : {exc}", file=sys.stderr)
        return 1

    assign_rarity(cfg, combos)

    builder = PromptBuilder(cfg)
    prompts = {c.uid: builder.build(c) for c in combos}

    # Fournisseur d'images : simulation par défaut.
    real = bool(args.real)
    try:
        provider = get_provider(args.provider, real=real)
    except ImageProviderError as exc:
        print(f"erreur : {exc}", file=sys.stderr)
        return 1

    mode = f"RÉEL ({provider.name})" if provider.is_real else "SIMULATION (aucune dépense)"
    print(f"Mode : {mode}")

    # Image maître de référence (verrouillage du même lionceau).
    reference = _load_reference(cfg) if provider.is_real else None
    if provider.is_real:
        print("Référence maître : " + ("ACTIVE ✅" if reference else "absente (texte→image)"))
    print(f"Génération de {len(combos)} lionceau(x)…")

    images_dir = ensure_dir(output_dir / "images")
    reports = []
    for combo in combos:
        base = file_base(combo, cfg)
        image_path = None
        if provider.is_real:
            target = images_dir / f"{base}.png"
            if target.exists():
                print(f"  ! existe déjà, conservé : {target.name}")
                image_path = target
            else:
                image_path = _generate_with_retries(
                    provider, prompts[combo.uid], combo, cfg, target,
                    reference, args.max_retries,
                )
                if image_path is None:
                    # Erreur ponctuelle : on saute cette image et on continue.
                    print(f"  ⚠️ {combo.uid} ignoré (erreur), on continue.")
                    continue
        reports.append(build_report(combo, cfg, image_path))

    stats = trait_statistics(combos)
    result = write_all(combos, cfg, output_dir, prompts, reports, stats)

    _print_summary(combos, prompts, result, args.preview)
    if not real:
        print(
            "\nℹ️  Mode simulation : aucune image n'a été générée et aucune dépense "
            "engagée. Tout le reste (combinaisons, prompts, métadonnées, rareté, "
            "rapports) est prêt dans le dossier de sortie."
        )
    return 0


def _load_reference(cfg) -> bytes | None:
    """Charge l'image maître de référence si activée et présente."""
    mm = cfg.master_model
    if not mm.get("use_reference_image"):
        return None
    rel = mm.get("reference_image")
    if not rel:
        return None
    from .utils import PROJECT_ROOT

    path = (PROJECT_ROOT / rel)
    if path.exists():
        return path.read_bytes()
    print(f"  ! image de référence introuvable : {path} (passage en texte→image)")
    return None


def _generate_with_retries(provider, prompt, combo, cfg, target, reference, max_retries):
    """Génère une image et régénère tant qu'elle est REFUSÉE (jusqu'à max_retries)."""
    attempts = max(1, max_retries + 1)
    last_path = None
    for attempt in range(1, attempts + 1):
        try:
            data = provider.generate(
                prompt["positive"], prompt["negative"],
                size=_OPENAI_SQUARE_SIZE, seed=combo.seed, reference=reference,
            )
        except ImageProviderError as exc:
            print(f"erreur image {combo.uid} : {exc}", file=sys.stderr)
            return None
        if not data:
            return None
        target.write_bytes(data)
        last_path = target
        report = build_report(combo, cfg, target)
        if report["status"] != REJECT:
            return target
        if attempt < attempts:
            print(f"  ↻ {combo.uid} REFUSÉ, régénération ({attempt}/{max_retries})…")
    return last_path


def _print_summary(combos, prompts, result, preview: int) -> None:
    print(f"\n✅ Terminé : {result['count']} combinaison(s).")
    print(f"   CSV         : {result['csv']}")
    print(f"   Métadonnées : {result['metadata_dir']}")
    print(f"   Prompts     : {result['prompts_dir']}")
    print(f"   Rapports    : {result['reports_dir']}")
    print(f"   Validation  : {result['validation_summary']}")

    n = min(preview, len(combos))
    if n:
        print(f"\nAperçu de {n} combinaison(s) :")
        for c in combos[:n]:
            hetero = " (hétérochromie)" if c.heterochromia else ""
            print(
                f"  {c.uid}  pelage={c.fur.name_fr:<10} "
                f"yeux={c.eye_left.name_fr}{('/' + c.eye_right.name_fr) if c.heterochromia else ''}"
                f"{hetero}  style={c.style.name_fr:<20} objet={c.held_object:<24} "
                f"rareté={c.rarity_tier}"
            )


def main(argv: list | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
