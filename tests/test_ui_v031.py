"""Tests de non-régression structurels de l'interface OGIAS V0.31.

Ces tests ne remplacent pas une recette Chromium. Ils contrôlent les raccordements
entre le nouveau rendu et les API métier conservées.
"""
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / 'sorep_web' / 'static'


def test_sidebar_is_the_only_global_navigation() -> None:
    ui = (STATIC / 'v031-ui.js').read_text(encoding='utf-8')
    css = (STATIC / 'v031.css').read_text(encoding='utf-8')
    assert "id='v31-sidebar'" in ui
    assert 'id=\'v31-progress\'' in ui
    for old in ('#v30-title', '#v30-documents', '.v30-ribbon', '#etapes'):
        assert old in css
    assert 'display:none!important' in css


def test_variable_validation_still_uses_address_fingerprint() -> None:
    js = (STATIC / 'v031-variables.js').read_text(encoding='utf-8')
    assert "'/api/adressage'" in js
    assert "action:'appliquer',empreinte:plan.empreinte" in js
    assert "action:'valider',niveau:'automate',paires:pairs" in js
    assert "api('/api/variables/action'" in js
    assert "if(conflicts.length)" in js
    assert "mode!=='Neuf'" in js


def test_old_business_buttons_are_moved_not_cloned() -> None:
    ui = (STATIC / 'v031-ui.js').read_text(encoding='utf-8')
    css = (STATIC / 'v031.css').read_text(encoding='utf-8')
    for button_id in ('x-val-tout', 'es-export', 'm-calc', 'm-valider',
                      'ad-recalc', 'ad-app', 'ad-val', 'rf-creer', 'rf-exp',
                      'r-actualiser'):
        assert button_id in ui
    assert 'appendChild(b)' in ui
    assert '.v31-page-actions .v30-source-command' in css
    assert '.v31-actions-menu .v30-source-command' in css


def test_local_design_dependencies_only() -> None:
    index = (STATIC / 'index.html').read_text(encoding='utf-8')
    for name in ('v031.css', 'v031-ui.js', 'v031-variables.js'):
        assert name in index
    assert 'https://' not in index
    assert 'http://' not in index
