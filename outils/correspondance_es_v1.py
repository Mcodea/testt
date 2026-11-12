"""Correspondance déterministe entre les E/S du catalogue livré et la bibliothèque V1 (classeur 2).

Lecture seule : n'écrit que le rapport demandé. Règles de rapprochement, dans l'ordre :
1. même type, même nature, même code ;
2. même type, même nature, code d'origine du classeur = code du catalogue ;
3. même type, même nature, télétransmission du classeur = famille_code du catalogue.
Une ligne n'est rapprochée qu'une fois ; toute ambiguïté reste non rapprochée.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
NATURES = ("ET", "ST", "EA", "SA")


def charger():
    catalogue = json.loads((ROOT / "genvar/data/catalogue_defaut.json").read_text(encoding="utf-8"))
    signaux = [(i, s) for i, s in enumerate(catalogue["signaux"]) if s["es"] in NATURES]
    classeur = load_workbook(ROOT / "docs/referentiel/OGIAS_V031_bibliotheque_ES_physiques.xlsx",
                             read_only=True, data_only=True)
    try:
        lignes = list(classeur["Bibliothèque E-S"].values)
    finally:
        classeur.close()
    tete = lignes[0]
    return signaux, [dict(zip(tete, ligne)) for ligne in lignes[1:] if ligne[0]]


def rapprocher(signaux, bibliotheque):
    criteres = (
        ("code", lambda s: s["code"], lambda x: x["Code"]),
        ("code d'origine", lambda s: s["code"], lambda x: x["Code d'origine"]),
        ("télétransmission", lambda s: f"{s['famille']}_{s['code']}", lambda x: x["Télétransmission"]),
    )
    libres_s, libres_x, paires = dict(signaux), {x["Identifiant"]: x for x in bibliotheque}, []
    for nom, cle_s, cle_x in criteres:
        index_s, index_x = {}, {}
        for i, s in libres_s.items():
            index_s.setdefault((s["type"], s["es"], cle_s(s)), []).append(i)
        for ident, x in libres_x.items():
            if cle_x(x):
                index_x.setdefault((x["Type"], x["Nature"], cle_x(x)), []).append(ident)
        for cle, candidats in index_s.items():
            # Une ligne de catalogue par option : départager par la variante si nécessaire.
            idents = index_x.get(cle, [])
            for i in list(candidats):
                choix = idents if len(idents) == 1 and len(candidats) == 1 else [
                    d for d in idents if (libres_x[d]["Variante / option"] or "Base") in
                    (libres_s[i]["option"] or "Base", "Base") and d in libres_x]
                if len(choix) == 1 and choix[0] in libres_x:
                    paires.append((i, choix[0], nom))
                    libres_x.pop(choix[0])
                    libres_s.pop(i)
                    idents = [d for d in idents if d != choix[0]]
    return paires, libres_s, libres_x


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sortie", type=Path, default=ROOT / "validation/referentiel/correspondance_es_v1.csv")
    args = parser.parse_args()
    signaux, bibliotheque = charger()
    paires, seuls_s, seuls_x = rapprocher(signaux, bibliotheque)
    par_ident = {x["Identifiant"]: x for x in bibliotheque}
    s_index = dict(signaux)
    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    with args.sortie.open("w", encoding="utf-8", newline="") as flux:
        w = csv.writer(flux, delimiter=";")
        w.writerow(["Identifiant V1", "Évolution", "Rapprochement", "Index catalogue", "Type", "Nature",
                    "Code catalogue", "Famille catalogue", "Code V1", "Télétransmission V1", "Variante V1"])
        for i, ident, nom in sorted(paires, key=lambda p: p[1]):
            s, x = s_index[i], par_ident[ident]
            w.writerow([ident, x["Évolution"], nom, i, s["type"], s["es"], s["code"], s["famille"],
                        x["Code"], x["Télétransmission"], x["Variante / option"]])
        for ident, x in sorted(seuls_x.items()):
            w.writerow([ident, x["Évolution"], "absent du catalogue", "", x["Type"], x["Nature"], "", "",
                        x["Code"], x["Télétransmission"], x["Variante / option"]])
        for i, s in sorted(seuls_s.items()):
            w.writerow(["", "", "absent du classeur", i, s["type"], s["es"], s["code"], s["famille"], "", "", s["option"]])
    resume = {"rapprochees": len(paires), "classeur_seul": len(seuls_x), "catalogue_seul": len(seuls_s)}
    print(json.dumps(resume, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
