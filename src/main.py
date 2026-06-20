"""Point d'entrée en ligne de commande.

Exemples :
    python -m src.main generate --count 100
    python -m src.main generate --count 10 --provider simulation
    python -m src.main info
    python -m src.main preview --count 5

Par défaut, tout fonctionne en mode SIMULATION : aucune image n'est générée et
aucune dépense n'est engagée. Pour une génération réelle, il faut explicitement
choisir un fournisseur ET désactiver le mode test (--real), ce qui n'est pas le
comportement par défaut.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import utils
from .combination_generator import CombinationGenerator, Character, ConfigBundle
from .duplicate_checker import DuplicateChecker
from .image_provider import GenerationResult, get_provider
from .metadata_generator import MetadataGenerator
from .prompt_builder import BuiltPrompt, PromptBuilder
from .quality_control import QualityControl, summarize
from .rarity_engine import RarityEngine


# ---------------------------------------------------------------------------
# Pipeline de génération (réutilisable par la CLI et l'interface web)
# ---------------------------------------------------------------------------
@dataclass
class PipelineOptions:
    count: int = 10
    provider: Optional[str] = None
    test_mode: Optional[bool] = None
    seed: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    config_path: str = "config/collection.yaml"
    write_outputs: bool = True
    resume: bool = False
    # Surcharge facultative des traits autorisés : {"fur_colors": [...],
    # "eye_colors": [...], "styles": [...]}. Listes vides = aucun filtre.
    allowed_traits: Optional[Dict[str, List[str]]] = None


@dataclass
class PipelineResult:
    characters: List[Character]
    prompts: List[BuiltPrompt]
    results: List[GenerationResult]
    qc: List[Any]
    stats: Dict[str, Any]
    provider_name: str
    files: Dict[str, Any] = field(default_factory=dict)


def run_pipeline(options: PipelineOptions) -> PipelineResult:
    bundle = ConfigBundle.load(options.config_path)

    # Surcharges éventuelles venues de la CLI.
    gen_cfg = bundle.collection.setdefault("generation", {})
    if options.seed is not None:
        gen_cfg["master_seed"] = options.seed
    if options.provider is not None:
        gen_cfg["provider"] = options.provider
    if options.test_mode is not None:
        gen_cfg["test_mode"] = options.test_mode
    if options.width is not None:
        bundle.collection["image"]["width"] = options.width
    if options.height is not None:
        bundle.collection["image"]["height"] = options.height
    if options.allowed_traits is not None:
        allow = bundle.collection.setdefault("allowed_traits", {})
        allow.update(options.allowed_traits)

    test_mode = bool(gen_cfg.get("test_mode", True))
    provider_key = gen_cfg.get("provider", "simulation")

    # 1) Combinaisons uniques.
    combiner = CombinationGenerator(bundle)
    dup = DuplicateChecker(
        history_path=f"{bundle.collection['output'].get('registries', 'output/registries')}/combinations.json"
    )
    existing = dup.load_history() if options.resume else set()
    characters = combiner.generate(options.count, existing_keys=existing)

    # 2) Rareté.
    rarity = RarityEngine(bundle)
    rarity.assign_all(characters)

    # 3) Prompts.
    builder = PromptBuilder(bundle)
    prompts = [builder.build(c) for c in characters]

    # 4) Fournisseur d'images (simulation par défaut).
    provider = get_provider(
        provider_key,
        bundle.collection,
        bundle.collection["output"]["images"],
        test_mode=test_mode,
    )
    meta_gen = MetadataGenerator(bundle)
    results: List[GenerationResult] = []
    for c, p in zip(characters, prompts):
        filename = meta_gen.image_filename_for(c)
        results.append(provider.generate(p, filename=filename))

    # 5) Contrôle qualité.
    qc_engine = QualityControl(bundle)
    qc_results = [qc_engine.check(c, p, r) for c, p, r in zip(characters, prompts, results)]

    # 6) Statistiques.
    stats = meta_gen.build_stats(characters)

    files: Dict[str, Any] = {}
    if options.write_outputs:
        files = _write_outputs(
            bundle, meta_gen, characters, prompts, results, qc_results, dup
        )

    return PipelineResult(
        characters=characters,
        prompts=prompts,
        results=results,
        qc=qc_results,
        stats=stats,
        provider_name=provider.name,
        files=files,
    )


def _write_outputs(
    bundle: ConfigBundle,
    meta_gen: MetadataGenerator,
    characters: List[Character],
    prompts: List[BuiltPrompt],
    results: List[GenerationResult],
    qc_results: List[Any],
    dup: DuplicateChecker,
) -> Dict[str, Any]:
    out = bundle.collection["output"]
    files: Dict[str, Any] = {}

    files["metadata"] = meta_gen.write_all_metadata(characters)
    files["csv"] = meta_gen.write_csv(characters)
    files["registries"] = meta_gen.write_registries(characters)
    files["stats"] = meta_gen.write_stats(characters)

    # Prompts : un fichier texte lisible + un JSON exploitable par image.
    prompt_dir = out["prompts"]
    for p in prompts:
        utils.save_text(
            f"{prompt_dir}/{p.id}.txt",
            f"=== PROMPT POSITIF ===\n{p.positive}\n\n"
            f"=== PROMPT NÉGATIF ===\n{p.negative}\n\n"
            f"=== TECHNIQUE ===\nseed={p.seed} size={p.width}x{p.height}\n",
        )
    utils.save_json(f"{prompt_dir}/all_prompts.json", [p.as_dict() for p in prompts])
    files["prompts"] = prompt_dir

    # Rapport de contrôle qualité.
    qc_payload = {
        "summary": summarize(qc_results),
        "results": [r.as_dict() for r in qc_results],
    }
    utils.save_json(f"{out['reports']}/quality_report.json", qc_payload)
    files["quality_report"] = f"{out['reports']}/quality_report.json"

    # Historique des combinaisons (anti-doublon persistant).
    dup.register_all(characters)
    dup.save_history()
    files["history"] = dup.history_path

    return files


# ---------------------------------------------------------------------------
# Affichage console
# ---------------------------------------------------------------------------
def _print_preview(result: PipelineResult, limit: int = 10) -> None:
    print(f"\nFournisseur : {result.provider_name}")
    print(f"Personnages générés : {len(result.characters)}")

    # Bilan des images réelles : ne jamais masquer un échec d'appel API.
    errors = [r for r in result.results if r.error]
    written = [r for r in result.results if r.image_path and not r.error]
    if any(not r.simulated for r in result.results):
        print(
            f"Images écrites : {len(written)} | Échecs : {len(errors)}"
        )
        if errors:
            print(
                f"⚠ {len(errors)} image(s) NON générée(s). "
                f"Première erreur : {errors[0].error}"
            )

    qc_summary = summarize(result.qc)
    print(f"Contrôle qualité : {qc_summary}")
    print("\n--- Aperçu des combinaisons ---")
    for c in result.characters[:limit]:
        rarity = (c.rarity or {}).get("name", "?")
        print(
            f"#{c.id}  pelage={c.fur['name']:<10} yeux={c.eyes['name']:<16} "
            f"style={c.style['name']:<22} objet={c.obj['name']:<18} "
            f"rareté={rarity:<10} seed={c.seed}"
        )


def _cmd_generate(args: argparse.Namespace) -> int:
    allowed = None
    if args.fur or args.eyes or args.styles:
        allowed = {
            "fur_colors": args.fur or [],
            "eye_colors": args.eyes or [],
            "styles": args.styles or [],
        }
    options = PipelineOptions(
        count=args.count,
        provider=args.provider,
        test_mode=(False if args.real else True if args.test else None),
        seed=args.seed,
        width=args.resolution,
        height=args.resolution,
        config_path=args.config,
        write_outputs=not args.no_write,
        resume=args.resume,
        allowed_traits=allowed,
    )
    if args.real and (args.provider in (None, "simulation")):
        print(
            "ERREUR : --real exige un fournisseur réel (--provider openai|flux|...).\n"
            "Aucune génération payante n'est lancée. Utilisez le mode simulation.",
            file=sys.stderr,
        )
        return 2

    result = run_pipeline(options)
    _print_preview(result, limit=10)
    if result.files:
        print("\n--- Fichiers écrits ---")
        print(f"CSV          : {result.files.get('csv')}")
        print(f"Métadonnées  : {len(result.files.get('metadata', []))} fichiers JSON")
        print(f"Prompts      : {result.files.get('prompts')}")
        print(f"Rapport QC   : {result.files.get('quality_report')}")
        print(f"Statistiques : {result.files.get('stats')}")
    return 0


def _cmd_preview(args: argparse.Namespace) -> int:
    options = PipelineOptions(count=args.count, config_path=args.config, write_outputs=False)
    result = run_pipeline(options)
    _print_preview(result, limit=args.count)
    if args.show_prompts:
        print("\n--- Prompts ---")
        for p in result.prompts[: args.count]:
            print(f"\n#{p.id} (seed={p.seed}, {p.width}x{p.height})")
            print(p.positive)
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    bundle = ConfigBundle.load(args.config)
    combiner = CombinationGenerator(bundle)
    print("Collection :", bundle.collection["collection"]["name"])
    print("Pelages    :", len(bundle.fur_colors))
    print("Yeux       :", len(bundle.eye_colors))
    print("Styles     :", len(bundle.styles))
    print("Combinaisons uniques max :", combiner.max_unique_combinations())
    print("Fond actif :", bundle.collection["background"]["active"])
    img = bundle.collection["image"]
    print(f"Résolution : {img['width']}x{img['height']} ({img['aspect_ratio']})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="src.main",
        description="Générateur de collection NFT de lionceaux (cohérence stricte).",
    )
    parser.add_argument(
        "--config", default="config/collection.yaml", help="Chemin du fichier de configuration."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="Génère la collection (simulation par défaut).")
    g.add_argument("--count", type=int, default=10, help="Nombre d'images à générer.")
    g.add_argument("--provider", default=None, help="simulation|openai|stable_diffusion|flux|comfyui")
    g.add_argument("--seed", type=int, default=None, help="Seed maître (reproductibilité).")
    g.add_argument("--resolution", type=int, default=None, help="Côté de l'image carrée en pixels.")
    g.add_argument("--test", action="store_true", help="Force le mode simulation.")
    g.add_argument("--real", action="store_true", help="Active la génération réelle (fournisseur requis).")
    g.add_argument("--resume", action="store_true", help="Poursuit sans réutiliser les combinaisons déjà créées.")
    g.add_argument("--fur", nargs="*", default=None, help="Clés de pelage autorisées (ex: white gold).")
    g.add_argument("--eyes", nargs="*", default=None, help="Clés d'yeux autorisées.")
    g.add_argument("--styles", nargs="*", default=None, help="Clés de styles autorisées.")
    g.add_argument("--no-write", action="store_true", help="N'écrit aucun fichier (aperçu seulement).")
    g.set_defaults(func=_cmd_generate)

    p = sub.add_parser("preview", help="Affiche un aperçu sans rien écrire.")
    p.add_argument("--count", type=int, default=5)
    p.add_argument("--show-prompts", action="store_true", help="Affiche aussi les prompts complets.")
    p.set_defaults(func=_cmd_preview)

    i = sub.add_parser("info", help="Affiche les statistiques de configuration.")
    i.set_defaults(func=_cmd_info)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
