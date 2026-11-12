"""Prévisualisation CLI, en lecture seule, d'un import OGIAS.

Exemple : python -m genvar.inbound --projet ouvrage.ouvrage.json \\
            --source inventaire.xlsx --kind inventaire
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from genvar.session import Session
from . import InputKind, InboundError, preview_import


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OGIAS : prévisualiser un import sans enregistrer de projet")
    parser.add_argument("--projet", required=True, type=Path, help="Fichier .ouvrage.json à ouvrir en lecture seule")
    parser.add_argument("--source", required=True, type=Path, help="Source CSV/XLSX/ODS/SCY")
    parser.add_argument("--kind", required=True, choices=[kind.value for kind in InputKind])
    parser.add_argument("--feuille", help="Nom de la feuille, si plusieurs feuilles pertinentes")
    parser.add_argument("--resume", action="store_true", help="Ne pas afficher les lignes individuelles")
    args = parser.parse_args(argv)
    try:
        session = Session()
        session.ouvrir(str(args.projet))
        preview = preview_import(args.source, InputKind(args.kind), session, sheet=args.feuille)
        print(json.dumps(preview.to_report(include_rows=not args.resume),
                         indent=2, ensure_ascii=False))
        return 2 if preview.errors else 0
    except (InboundError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"OGIAS Inbound : {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
