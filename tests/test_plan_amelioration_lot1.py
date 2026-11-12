"""Non-régression du premier lot du plan d'amélioration OGIAS."""
from pathlib import Path
from sorep_web.serveur import Application
from genvar.modele import Equipement
from genvar.session import Session
from genvar.catalogue import Catalogue
from genvar import chemins


def test_alerte_modele_non_valide(tmp_path, monkeypatch):
    monkeypatch.setenv('SOREP_DATA_DIR', str(tmp_path))
    s = Session(catalogue=Catalogue.charger(chemins.fichier_catalogue_origine()))
    s.nouveau(False)
    s.definir('lieu', 'X999')
    s.definir('code_ouvrage', 'RV')
    s.ajouter_sous_ensemble('11', 'Test')
    nom = s.creer_modele('FT', 'MODELE_FT_OGIAS_TEST', True)
    eq = s.ajouter_equipement(Equipement('11', 'FT', '01', 'Fictif', modele=nom))
    app = Application()
    app.s = s
    app.ouvert = True
    fiche = app.equipement({'ident': eq.ident})
    assert fiche['statut_modele'] == 'à valider'
    assert 'pas validé' in fiche['alerte_modele']
    s.valider_modele(nom, True)
    fiche = app.equipement({'ident': eq.ident})
    assert fiche['statut_modele'] == 'validé'
    assert not fiche['alerte_modele']


def test_parcours_web_et_ecrans_maintenant_operationnels():
    js = (Path(__file__).resolve().parents[1] / 'sorep_web/static/app.js').read_text(encoding='utf-8')
    for route in ('#/inventaire', '#/es', '#/variables', '#/supervision', '#/recette'):
        assert route in js
    # Ce texte était attendu en V0.22 ; la V0.26 dispose désormais de ces écrans.
    for screen in ('function vueVariables()', 'function vueSupervision()', 'function vueRecette()'):
        assert screen in js
    assert 'Référentiel à contrôler' in js
