"""Recette de lecture XSY/SCY publics par SOREP.

Script non destructif : ne modifie ni les fichiers sources ni les ouvrages.
Usage : py tester_import_schneider.py "chemin_vers_fichier.xsy" ["autre_fichier.SCY"]
Placer ce script à la racine du projet SOREP (au même niveau que genvar/).
Le rapport est écrit dans un dossier d'essai distinct.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def inspection_xsy(path: Path):
    root = ET.parse(path).getroot()
    if root.tag != "VariablesExchangeFile":
        raise ValueError(f"Racine XSY inattendue : {root.tag!r}")
    block = root.find("dataBlock")
    if block is None:
        raise ValueError("Bloc dataBlock absent du fichier XSY")
    values = []
    for v in block.findall("variables"):
        c = v.find("comment")
        values.append((v.get("name", ""), v.get("typeName", ""),
                       v.get("topologicalAddress", "") or "",
                       (c.text or "").strip() if c is not None else ""))
    return values, {"variables_premier_niveau":len(values),
                    "ddt_declares":len(block.findall("DDTSource")),
                    "dfb_declares":len(block.findall("DFBSource"))}


def inspection_scy(path: Path, import_sources):
    headers, raw = import_sources.charger_table(path)
    mapping = import_sources._colonnes(headers)
    lines, warnings = import_sources.preparer_lignes(headers, raw, mapping)
    return lines, {"lignes_lues":len(raw), "avertissements_preparation":len(warnings)}


def inspect(path: Path):
    # N'autoriser que le traitement de fichiers locaux explicitement transmis.
    if not path.is_file():
        raise FileNotFoundError(f"Fichier introuvable : {path}")
    if path.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("Fichier > 20 Mio : examen manuel requis")
    from genvar.existant import lire_xsy, importer_lignes
    from genvar.modele import Ouvrage
    from genvar import import_sources
    if path.suffix.lower() == ".xsy":
        source, details = inspection_xsy(path)
        read = lire_xsy(str(path))
    elif path.suffix.lower() == ".scy":
        source, details = inspection_scy(path, import_sources)
        read = list(source)
    else:
        raise ValueError("Formats acceptés : XSY et SCY")
    # Comparaison indépendante sur les 4 champs ; on vérifie la conservation, pas la pertinence SCADA.
    lecture_identique = source == read
    ouvrage = Ouvrage(mode="Existant", automate="TSX" if path.suffix.lower()==".scy" else "M580")
    n, ajout = importer_lignes(ouvrage, read)
    final = [(v.nom, v.type_logique, v.adresse, v.commentaire) for v in ouvrage.existantes]
    source_set = set(source)
    conserve = all(t in source_set for t in final)
    perdus = [t for t in source if t not in set(final)]
    names = [x[0] for x in source]
    doublons = [name for name, count in Counter(names).items() if count > 1]
    return {
      "fichier":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
      "source":"fichier fourni par l'utilisateur, contenu non modifié",
      "format":path.suffix.lower(),"lignes_source":len(source),
      "lignes_lues_par_sorep":len(read),"variables_ajoutees":ajout,
      "variables_referencees":n,"adresses_manquantes":sum(not x[2] for x in source),
      "types_manquants":sum(not x[1] for x in source),
      "noms_en_doublon":doublons,
      "lecture_identique_sur_4_champs":lecture_identique,
      "variables_perdues":len(perdus),"integration_conserve_donnees":conserve,
      "details":details,
      "limite":"Aucune vérification de l'accessibilité Topkapi ni du classement TS/TC/TM/TR/RTR/CP. Aucun taux de rapprochement sans corrigé indépendant."
    }


def main():
    p = argparse.ArgumentParser(description="Test sans mutation de l'import XSY / SCY dans SOREP")
    p.add_argument("fichiers", nargs="+", help="Chemin(s) vers XSY ou SCY localement téléchargés")
    p.add_argument("--rapport", default="rapport_import_schneider.json")
    args = p.parse_args()
    if not (Path(__file__).resolve().parent / "genvar").is_dir() and not (Path.cwd() / "genvar").is_dir():
        print("ERREUR : placer le script à la racine de SOREP (dossier contenant genvar), puis réessayer.",file=sys.stderr)
        return 2
    reports=[]
    for value in args.fichiers:
        path=Path(value).resolve()
        try:
            result = inspect(path)
            reports.append({"statut":"PASS" if result["lecture_identique_sur_4_champs"] and result["integration_conserve_donnees"] and result["variables_perdues"]==0 else "FAIL",**result})
            print(f'{reports[-1]["statut"]} {path.name}: {result["lignes_source"]} entrées, {result["variables_ajoutees"]} intégrées, {result["variables_perdues"]} perdues')
        except Exception as exc:
            reports.append({"statut":"FAIL","fichier":path.name,"erreur":f"{type(exc).__name__}: {exc}"})
            print(f'FAIL {path.name}: {exc}')
    out = Path(args.rapport)
    out.write_text(json.dumps({"date_utc":datetime.now(timezone.utc).isoformat(),
                               "objectif":"intégrité import XSY/SCY, sans vérité de supervision",
                               "resultats":reports},ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Rapport : {out.resolve()}")
    return 0 if all(r["statut"]=="PASS" for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
