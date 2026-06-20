"""Interface en ligne de commande (utile pour tests et usage avancé).

L'utilisateur final n'a PAS besoin du terminal : l'application graphique
(``python -m anto_designer``) est le mode normal. La CLI sert au diagnostic,
à l'automatisation et aux tests.
"""

from __future__ import annotations

import argparse
import sys

from . import __full_name__, __version__, config
from .layer_engine import backend_name


def _cmd_info(args) -> int:
    print(f"{__full_name__}  v{__version__}")
    print(f"Backend image : {backend_name()}")
    paths = config.ensure_dirs()
    print(f"Dossier données : {paths['root']}")
    print(f"Base de données : {paths['db']}")
    return 0


def _cmd_demo(args) -> int:
    from demo.build_demo import build_demo  # type: ignore

    summary = build_demo(count=args.count)
    print("Démo générée :", summary)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="anto-designer",
                                description="ANTO DESIGNER — NFT Collection Studio (CLI)")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("info", help="Afficher les informations système.").set_defaults(
        func=_cmd_info)
    d = sub.add_parser("demo", help="Construire et générer le projet de démonstration.")
    d.add_argument("--count", type=int, default=8)
    d.set_defaults(func=_cmd_demo)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
