"""Étape 4 : les vues restent des projections sans effet du moteur central d'adressage.

Aucune donnée industrielle réelle et aucune qualification d'export ne sont utilisées ici.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.modele import Equipement
from genvar.session import Session, RegleMetier
from sorep_web.serveur import Application


def nouveau(mode: str = "Neuf", automate: str = "M340") -> Application:
    session = Session(catalogue=Catalogue.charger(chemins.fichier_catalogue_origine()))
    session.nouveau(lieu_dans_le_nom=(mode == "Existant"))
    session.definir("mode", mode)
    session.definir("lieu", "XTST")
    session.definir("code_ouvrage", "RV")
    session.definir("numero_ouvrage", "01")
    session.definir("libelle", "Ouvrage fictif")
    session.definir("automate", automate)
    session.ajouter_sous_ensemble("11", "Hydraulique")
    session.ajouter_uf("UF01", "Mesures")
    app = Application()
    app.s = session
    app.ouvert = True
    return app


def avec_debitmetre(automate: str = "M340") -> Application:
    app = nouveau(automate=automate)
    s = app.s
    e = s.ajouter_equipement(Equipement("11", "FT", "01", "Débitmètre fictif", uf="UF01"))
    s.definir_analogique(e.ident, "ES_DEB", {"signal_min": 4, "signal_max": 20,
                                            "phys_min": 0, "phys_max": 500, "unite": "m³/h"})
    s.decider_propositions(e.ident, "retenir")
    s.valider_equipements([e.ident])
    return app


def test_table_echange_pas_de_variables_e_s_et_pas_de_mutation():
    app = avec_debitmetre()
    avant = copy.deepcopy(app.s.ouvrage.vers_dict())
    api = app.variables_web({})
    assert api["mode"] == "Neuf"
    assert api["lignes"]
    assert all(v["famille"] not in ("ET", "ST", "EA", "SA", "ES") for v in api["lignes"])
    assert all(not v["nom"].startswith(("ET_", "ST_", "EA_", "SA_", "ES_")) for v in api["lignes"])
    assert {"adresse", "adresse_proposee", "etat_adressage", "origine_adressage",
            "regle", "motif", "source_es", "voie_es", "validee_le", "validee_par"} <= set(api["lignes"][0])
    assert app.s.ouvrage.vers_dict() == avant


def test_teletransmission_plan_sans_doublon_ni_adresse_fictive():
    app = avec_debitmetre()
    avant = copy.deepcopy(app.s.ouvrage.vers_dict())
    res = app.supervision_web({})
    ids = [l["identifiant_point"] for l in res["lignes"]]
    assert len(ids) == len(set(ids))
    assert all(l["variable_source"] == l["nom"] for l in res["lignes"])
    assert all("adresse_protocole_proposee" in l for l in res["lignes"])
    assert all(not l["adresse_protocole_proposee"] for l in res["lignes"] if l["etat_adressage"] == "non résolue")
    assert app.s.ouvrage.vers_dict() == avant


def test_s4w_ne_recoit_jamais_de_mw_propose_par_la_vue():
    app = avec_debitmetre("S4W")
    tab = app.variables_web({})
    assert tab["lignes"]
    assert all(not l["adresse_proposee"].startswith("%MW") for l in tab["lignes"])
    assert all(l["etat_adressage"] == "non résolue" for l in tab["lignes"] if not l["adresse"])
    tele = app.supervision_web({})
    assert all(not l["adresse_protocole_proposee"] for l in tele["lignes"])


def test_projet_existant_en_lecture_seule():
    app = nouveau("Existant")
    tab = app.variables_web({})
    assert tab["mode"] == "Existant"
    assert tab["lignes"] == []
    assert "lecture seule" in tab["note"]
    assert app.supervision_web({})["lignes"] == []
    with pytest.raises(RegleMetier, match="jamais réadressées"):
        app.variables_action({"action": "adresse", "ident_eq": "x", "cle": "TS_TEST", "adresse": "%MW4"})


def test_interface_trois_onglets_sans_memoire_et_adressage_protege():
    js = (Path(__file__).resolve().parents[1] / "sorep_web/static/app.js").read_text(encoding="utf-8")
    assert 'Table d\'échange</a>' in js
    assert '>Télétransmission</a>' in js
    assert '>Adressage automatique</a>' in js
    assert 'function vueAdressage()' in js
    assert 'function vueVariables()' in js
    assert 'function vueSupervision()' in js
    assert 'data-niv=' in js and 'd.empreinte' in js
    assert 'action: "appliquer", empreinte: d.empreinte' in js
    assert 'Calcul de prévisualisation sans écriture' in js
    assert 'voie non placée — étape Matériel' in js
