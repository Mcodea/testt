"""Reprise contrôlée d'un modèle figé dans l'ouvrage (migration dédiée signalée par la passation du 10/11).

Mêmes garanties que l'adoption du catalogue (L2) : aperçu sans effet, blocage si une clé qui disparaît porte
des données, renommages confirmés, report des données par correspondance, sauvegarde, journal, retour arrière.
"""
import copy

import pytest

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.modele import Equipement
from genvar.referentiel_depot import empreinte
from genvar.session import RegleMetier, Session


@pytest.fixture
def s(tmp_path, monkeypatch):
    monkeypatch.setenv("SOREP_DATA_DIR", str(tmp_path))
    s = Session(catalogue=Catalogue.charger(chemins.fichier_catalogue_origine()))
    s.nouveau(False)
    s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.definir("numero_ouvrage", "01")
    s.ajouter_sous_ensemble("11", "Essai fictif")
    s.nom_modele = s.creer_modele("FT", "FT_FIGE_TEST", True)
    s.e1 = s.ajouter_equipement(Equipement("11", "FT", "01", "Débitmètre fictif", modele=s.nom_modele))
    s.e2 = s.ajouter_equipement(Equipement("11", "FT", "02", "Débitmètre fictif", modele=s.nom_modele))
    s.chemin_test = str(tmp_path / "XTSTRV01.ouvrage.json")
    s.enregistrer(s.chemin_test)
    return s


def _publie(s):
    return s.modeles["modeles"][s.nom_modele]


def _signal(m, cle):
    return next(x for x in m["signaux"] if f"{x['famille']}_{x['code']}" == cle)


def test_modele_a_jour_rien_a_reprendre(s):
    a = s.apercu_modele(s.nom_modele)
    assert a["identique"] and a["adoptable"]
    with pytest.raises(RegleMetier, match="à jour"):
        s.adopter_modele(s.nom_modele)


def test_reprise_simple_avec_sauvegarde_journal_et_retour_arriere(s):
    s.e1.valide = s.e2.valide = True
    avant = empreinte(s.ouvrage.vers_dict())
    m = _publie(s)
    m["signaux"] = [x for x in m["signaux"] if f"{x['famille']}_{x['code']}" != "ES_SENS"]
    _signal(m, "TM_DEB")["information"] += " (révisée)"
    a = s.apercu_modele(s.nom_modele)
    assert a["retirees"] == ["ES_SENS"] and a["modifiees"] == ["TM_DEB"] and a["adoptable"]
    assert sorted(a["equipements"]) == sorted([s.e1.code_court(), s.e2.code_court()])
    assert empreinte(s.ouvrage.vers_dict()) == avant                                # aperçu sans effet
    s.adopter_modele(s.nom_modele)
    assert s.ouvrage.modeles_snapshot[s.nom_modele] == m
    assert not s.e1.valide and not s.e2.valide
    assert s.sauvegarde_adoption
    j = [(x["action"], x["ident_eq"]) for x in s.ouvrage.journal_referentiel]
    assert j == [("adoption du modèle", s.e1.ident), ("adoption du modèle", s.e2.ident)]
    s.annuler_adoption()
    assert empreinte(s.ouvrage.vers_dict()) == avant


def test_cle_qui_disparait_et_porte_des_donnees_bloque(s):
    s.e1.es_meta["ES_SENS"] = {"note": "Câblage vérifié"}
    m = _publie(s)
    m["signaux"] = [x for x in m["signaux"] if f"{x['famille']}_{x['code']}" != "ES_SENS"]
    a = s.apercu_modele(s.nom_modele)
    assert not a["adoptable"] and any("ES_SENS" in b for b in a["bloquants"])
    avant = empreinte(s.ouvrage.vers_dict())
    with pytest.raises(RegleMetier):
        s.adopter_modele(s.nom_modele, renommages_confirmes=True)
    with pytest.raises(RegleMetier):
        s.actualiser_modele_eq(s.e1.ident)                  # l'ancienne reprise directe est aussi protégée
    assert empreinte(s.ouvrage.vers_dict()) == avant


def test_changement_de_nom_physique_confirme(s):
    _signal(_publie(s), "ES_DEB")["suffixe_es"] = "DEBIT"
    a = s.apercu_modele(s.nom_modele)
    assert [(r["ancienne"], r["nouvelle"]) for r in a["renommages"]] == [("ES_DEB", "ES_DEB")]
    with pytest.raises(RegleMetier, match="confirm"):
        s.adopter_modele(s.nom_modele)
    with pytest.raises(RegleMetier):
        s.actualiser_modele_eq(s.e1.ident)
    s.adopter_modele(s.nom_modele, renommages_confirmes=True)
    assert any(p.nom.endswith("_DEBIT") for p in s.points() if p.ident_eq == s.e1.ident)


def test_correspondance_reporte_les_donnees(s):
    s.e1.adresses_es["ES_SENS"] = "%I0.2.3"
    m = _publie(s)
    sens = _signal(m, "ES_SENS")
    sens["code"] = "SENS_ECO"
    s.modeles["correspondances"] = list(s.modeles.get("correspondances", [])) + [
        {"type": "FT", "ancienne": "ES_SENS", "type_nouveau": "FT", "nouvelle": "ES_SENS_ECO", "motif": "Essai."}]
    a = s.apercu_modele(s.nom_modele)
    assert [(r["ancienne"], r["nouvelle"]) for r in a["renommages"]] == [("ES_SENS", "ES_SENS_ECO")]
    assert a["adoptable"]
    s.adopter_modele(s.nom_modele, renommages_confirmes=True)
    assert s.e1.adresses_es == {"ES_SENS_ECO": "%I0.2.3"}                           # adresse jamais recalculée


def test_modele_absent_ou_type_change_bloque(s):
    m = s.modeles["modeles"].pop(s.nom_modele)
    assert not s.apercu_modele(s.nom_modele)["adoptable"]
    s.modeles["modeles"][s.nom_modele] = dict(copy.deepcopy(m), type="PT")
    assert any("type" in b for b in s.apercu_modele(s.nom_modele)["bloquants"])


def test_routes_web(s):
    from sorep_web.serveur import ROUTES_GET, ROUTES_POST, Application
    assert ROUTES_GET["/api/referentiel/apercu-modele"] == "apercu_modele"
    assert ROUTES_POST["/api/referentiel/adopter-modele"] == "adopter_modele"
    app = Application()
    app.s, app.ouvert = s, True
    with pytest.raises(RegleMetier):
        app.apercu_modele({"nom": "inconnu"})
    _signal(_publie(s), "ES_DEB")["suffixe_es"] = "DEBIT"
    assert app.apercu_modele({"nom": s.nom_modele})["renommages"]
    with pytest.raises(RegleMetier):
        app.adopter_modele({"nom": s.nom_modele})
    r = app.adopter_modele({"nom": s.nom_modele, "renommages_confirmes": True})
    assert r["sauvegarde"]
    from genvar.modele import Ouvrage
    assert Ouvrage.ouvrir(s.chemin_test).modeles_snapshot[s.nom_modele] == _publie(s)


def test_ancienne_copie_sans_signaux_equivalente_est_a_jour(s):
    fige = s.ouvrage.modeles_snapshot[s.nom_modele]
    fige.pop("signaux")
    fige.pop("origine_signaux", None)
    _publie(s)["signaux"] = copy.deepcopy(s.catalogue.signaux_du_type("FT", avec_ecartes=True))
    assert s.apercu_modele(s.nom_modele)["identique"]
