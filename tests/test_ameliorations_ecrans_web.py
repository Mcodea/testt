"""Non-régression : surfaces web nouvelles, sans prétendre qualifier les formats industriels."""
import pytest
from sorep_web.serveur import Application, ROUTES_GET, ROUTES_POST
from genvar.session import RegleMetier


def test_routes_dingenierie_declares():
    assert ROUTES_GET['/api/variables'] == 'variables_web'
    assert ROUTES_GET['/api/supervision'] == 'supervision_web'
    assert ROUTES_GET['/api/recette'] == 'recette_web'
    assert ROUTES_POST['/api/variables/action'] == 'variables_action'


def test_projet_neuf_brouillon_avec_erreur_de_recette_et_aucune_adresse_inventee():
    app = Application()
    app.nouveau({'mode': 'Neuf'})
    assert app.variables_web({})['lignes'] == []
    assert app.supervision_web({})['lignes'] == []
    recette = app.recette_web({})
    assert recette['erreurs'] > 0
    assert recette['export_qualifie'] is False
    with pytest.raises(RegleMetier, match='Export XSY refusé'):
        app.exporter({'quoi': 'xsy'})


def test_existant_ne_peut_pas_reaffecter_adresse():
    app = Application()
    app.nouveau({'mode': 'Existant'})
    assert app.variables_web({})['mode'] == 'Existant'
    with pytest.raises(RegleMetier, match='ne sont jamais réadressées'):
        app.variables_action({'action': 'adresse', 'ident_eq': 'inventé', 'cle': 'TS_ETAT', 'adresse': '%MW999'})


def test_interfaces_affichent_statut_non_qualifie():
    from pathlib import Path
    js = (Path(__file__).resolve().parents[1] / 'sorep_web/static/app.js').read_text(encoding='utf-8')
    assert 'function vueVariables()' in js
    assert 'function vueSupervision()' in js
    assert 'function vueRecette()' in js
    assert 'NON QUALIFIÉ' in js
