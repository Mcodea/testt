"""Recette du référentiel OGIAS par modèle, avec projets fictifs et anciens fichiers intacts."""
import copy

import pytest

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.modele import Equipement
from genvar.session import RegleMetier, Session
from sorep_web.serveur import Application


@pytest.fixture
def session(tmp_path, monkeypatch):
    monkeypatch.setenv("SOREP_DATA_DIR", str(tmp_path))
    s = Session(catalogue=Catalogue.charger(chemins.fichier_catalogue_origine()))
    s.nouveau(False)
    s.definir("lieu", "X999")
    s.definir("code_ouvrage", "RV")
    s.definir("numero_ouvrage", "01")
    s.ajouter_sous_ensemble("11", "Essai fictif")
    return s


def ajout_debit(s, numero, modele):
    return s.ajouter_equipement(Equipement("11", "FT", numero, "Débitmètre fictif", modele=modele))


def test_deux_modeles_du_meme_type_possedent_des_es_differentes(session):
    s = session
    original = s.creer_modele("FT", "FT_COMPLET_TEST", True)
    reduit = s.creer_modele("FT", "FT_SANS_IMP_TEST", True)
    # Le second modèle a une possibilité physique de moins, et le CP est une
    # information fonctionnelle indépendante de l'E/S impulsions optionnelle.
    s.supprimer_signal_modele(reduit, "ES", "IMP")
    modele_complet = s.modeles["modeles"][original]
    assert any(x["code"] == "IMP" and x["famille"] == "ES" for x in modele_complet["signaux"])
    assert not any(x["code"] == "IMP" and x["famille"] == "ES" for x in s.modeles["modeles"][reduit]["signaux"])
    # Lien de référence devenu invalide : le modèle ne doit pas pouvoir être validé.
    with pytest.raises(RegleMetier, match="source physique"):
        s.valider_modele(reduit)
    # Corriger le lien fonctionnel : le CP pourra être alimenté autrement dans l'automate.
    cp = next(x for x in s.modeles["modeles"][reduit]["signaux"] if (x["famille"], x["code"]) == ("CP", "VOL"))
    s.modifier_signal_modele(reduit, "CP", "VOL", {**cp, "source": "", "logique": "Comptage ou totalisation dans l'automate, à paramétrer."})
    s.valider_modele(reduit)
    eq1 = ajout_debit(s, "01", original)
    eq2 = ajout_debit(s, "02", reduit)
    assert "Sortie impulsions câblée" in s.options_equipement(eq1)
    assert "Sortie impulsions câblée" not in s.options_equipement(eq2)
    s.choisir_option_es(eq1.ident, "Sortie impulsions câblée", True)
    assert "ES_IMP" in {p.cle for p in s.points() if p.ident_eq == eq1.ident}
    assert "ES_IMP" not in {p.cle for p in s.points() if p.ident_eq == eq2.ident}
    assert [(v.famille, v.code) for v in s.variables() if v.ident_eq == eq1.ident].count(("CP", "VOL")) == 1
    assert not any(p.point == "ST" for p in s.points() if p.ident_eq in (eq1.ident, eq2.ident))


def test_champs_installation_refuses_dans_modele_et_personnalisation_locale(session):
    s = session
    nom = s.creer_modele("FT", "FT_PERSONNALISATION_TEST", True)
    for invalide in ({"phys_min": 0}, {"adresse": "%IW0.0"}, {"impulsion": {"poids": 2}}):
        with pytest.raises(RegleMetier, match="inventaire"):
            s.ajouter_signal_modele(nom, {"famille": "ES", "code": "ABC", "information": "Essai", **invalide})
    e1 = ajout_debit(s, "01", nom)
    e2 = ajout_debit(s, "02", nom)
    s.definir_analogique(e1.ident, "ES_DEB", {"signal_min": 4, "signal_max": 20,
                       "phys_min": 0, "phys_max": 280, "unite": "m³/h"})
    assert s.ouvrage.equipement(e1.ident).es_meta["ES_DEB"]["analogique"]["phys_max"] == 280
    assert not s.ouvrage.equipement(e2.ident).es_meta.get("ES_DEB", {}).get("analogique")
    assert not any("phys_max" in x or "adresse" in x for x in s.modeles["modeles"][nom]["signaux"])


def test_anciens_ouvrages_nont_pas_de_migration_implicite(session, tmp_path):
    s = session
    nom = s.creer_modele("FT", "FT_ANCIEN_TEST", True)
    eq = ajout_debit(s, "01", nom)
    # Simulation exacte du modèle d'avant refonte : sans la nouvelle liste « signaux ».
    s.ouvrage.modeles_snapshot[nom].pop("signaux")
    old_points = [p.cle for p in s.points()]
    f = tmp_path / "ancien.ouvrage.json"
    s.enregistrer(str(f))
    avant = f.read_bytes()
    r = Session()
    r.ouvrir(str(f))
    assert f.read_bytes() == avant
    assert r.ouvrage.modeles_snapshot[nom].get("signaux") is None
    assert [p.cle for p in r.points()] == old_points
    assert r.ouvrage.equipements[0].ident == eq.ident


def test_actualiser_modele_revalide_tous_les_equipements_concernes(session):
    s = session
    nom = s.creer_modele("FT", "FT_PARTAGE_TEST", True)
    e1 = ajout_debit(s, "01", nom)
    e2 = ajout_debit(s, "02", nom)
    e1.valide = e2.valide = True
    e1.validees = ["TM_DEB"]
    e1.es_meta["ES_DEB"] = {"validee": True}
    c = copy.deepcopy(s.modeles["modeles"][nom]["signaux"])
    s.supprimer_signal_modele(nom, "ES", "SENS")
    # Modification du référentiel : aucune conséquence avant reprise explicite.
    assert s.ouvrage.modeles_snapshot[nom]["signaux"] == c
    s.actualiser_modele_eq(e1.ident)
    assert not e1.valide and not e2.valide
    assert not e1.validees and not e1.es_meta["ES_DEB"]["validee"]
    assert "ES_SENS" not in [f"{x['famille']}_{x['code']}" for x in s.ouvrage.modeles_snapshot[nom]["signaux"]]


def test_api_referentiel_unifie_et_blocage_doublons(session):
    s = session
    nom = s.creer_modele("FT", "FT_API_TEST", True)
    api = Application()
    api.s = s
    api.ouvert = True
    detail = api.modele({"nom": nom})
    assert any(x["famille"] == "ES" for x in detail["signaux"])
    assert any(x["famille"] == "CP" and x["code"] == "VOL" for x in detail["signaux"])
    assert len([x for x in detail["signaux"] if x["famille"] == "CP" and x["code"] == "VOL"]) == 1
    api.referentiel_cycle_action({"action": "creer_brouillon"})          # toute modification : dans un brouillon
    with pytest.raises(RegleMetier, match="existe déjà"):
        api.referentiel_action({"action": "ajouter_signal", "nom": nom,
            "champs": {"famille": "CP", "code": "VOL", "information": "Doublon", "es": "Interne",
                       "presence": "Par défaut", "type_logique": "DINT"}})


def test_vue_deux_modeles_pas_d_es_imposee_lors_de_l_ouverture(session):
    s = session
    nom = s.creer_modele("FT", "FT_VUE_TEST", True)
    ajout_debit(s, "01", nom)
    assert [p.point for p in s.points()] == ["EA"]
    assert set((v.famille, v.code) for v in s.variables()).issuperset({("TS", "HS"), ("TM", "DEB"), ("TS", "DEF")})
    assert ("CP", "VOL") not in [(v.famille, v.code) for v in s.variables()]
