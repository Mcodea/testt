"""Décision D5 du référentiel V2 : règles documentaires, aucun algorithme imposé, textes d'origine archivés."""
import csv
from pathlib import Path

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.regles import GOUVERNANCES, NOTES_GOUVERNANCE, texte

ROOT = Path(__file__).resolve().parents[1]


def test_toutes_les_regles_ont_une_gouvernance_et_aucun_algorithme_actif():
    cat = Catalogue.charger(chemins.fichier_catalogue_origine())
    assert len(cat.regles) == 64
    assert {r["gouvernance"] for r in cat.regles} <= set(GOUVERNANCES)
    assert [r["id"] for r in cat.regles if r.get("logique")] == []
    assert all(texte(r) == NOTES_GOUVERNANCE[r["gouvernance"]] for r in cat.regles)
    assert cat.anomalies() == []


def test_textes_d_origine_archives_pour_audit():
    with open(ROOT / "docs/referentiel/REGLES_AVANT.csv", encoding="utf-8") as f:
        lignes = list(csv.reader(f, delimiter=";"))[1:]
    cat = Catalogue.charger(chemins.fichier_catalogue_origine())
    assert [l[0] for l in lignes] == [r["id"] for r in cat.regles]
    assert sum(1 for l in lignes if l[4]) == 40


def test_gouvernance_inconnue_refusee():
    cat = Catalogue.charger(chemins.fichier_catalogue_origine())
    cat.regles[0]["gouvernance"] = "algorithme imposé"
    assert any("gouvernance « algorithme imposé » inconnue" in m for m in cat.anomalies())


def test_regle_ancienne_sans_gouvernance_garde_son_texte():
    assert texte({"logique": "texte historique"}) == "texte historique"
    assert texte({}) == ""
