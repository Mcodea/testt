"""V1-3-01 : le référentiel de modèles livré reprend exactement le classeur V1."""
import json
from pathlib import Path
import re

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]


def _classeur():
    workbook = load_workbook(ROOT / "docs/referentiel/OGIAS_V031_informations_modeles.xlsx",
                             read_only=True, data_only=True)
    try:
        rows = list(workbook["Informations"].values)
    finally:
        workbook.close()
    head = rows[0]
    return {r[0]: dict(zip(head, r)) for r in rows[1:] if r[0]}


def _lignes_livrees():
    data = json.loads((ROOT / "genvar/data/referentiel_modeles.json").read_text(encoding="utf-8"))
    return {ligne["id"]: (nom, ligne) for nom, modele in data["modeles"].items() for ligne in modele["lignes"]}


def test_lignes_conservees_exactes_et_retirees_absentes():
    classeur, livrees = _classeur(), _lignes_livrees()
    conservees = {i for i, x in classeur.items() if x["Évolution"] != "Retiré"}
    assert len(conservees) == 732
    assert set(livrees) == conservees
    for identifiant in conservees:
        attendu, (modele, ligne) = classeur[identifiant], livrees[identifiant]
        assert (modele, ligne["role"], ligne["libelle"], ligne["suffixe"]) == (
            attendu["Modèle"], attendu["Rôle"], attendu["Libellé"], attendu["Suffixe"]), identifiant


def test_suffixes_livres_courts_majuscules_et_uniques_par_modele():
    vus = set()
    for modele, ligne in _lignes_livrees().values():
        assert re.fullmatch(r"[A-Z0-9_]{1,12}", ligne["suffixe"]), ligne["id"]
        cle = (modele, ligne["role"], ligne["suffixe"])
        assert cle not in vus, ligne["id"]
        vus.add(cle)
