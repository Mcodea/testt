"""V0.30 : garde-fous de la fenêtre commune hors ligne.

Ces tests n'affirment pas la qualification industrielle : ils vérifient le
contrat d'intégration front-end, en complément des captures Playwright.
"""
from pathlib import Path
import unittest
from genvar import VERSION

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "sorep_web" / "static"


class TestInterfaceV030(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (STATIC / "index.html").read_text(encoding="utf-8")
        cls.shell = (STATIC / "v030-shell.js").read_text(encoding="utf-8")
        cls.app = (STATIC / "app.js").read_text(encoding="utf-8")
        cls.css = (STATIC / "app.css").read_text(encoding="utf-8")

    def test_version_unique(self):
        self.assertEqual(VERSION, "0.32")
        self.assertIn('0.32', self.html)
        self.assertIn('V0.32', (ROOT / 'LISEZ-MOI.md').read_text(encoding='utf-8'))

    def test_cadre_commun_sur_application_reelle(self):
        for identifier in ('v30-title', 'v30-ribbon', 'v30-documents',
                           'v30-tree', 'v30-work-heading', 'v30-inspector',
                           'v30-status', 'modale', 'vue'):
            self.assertIn(identifier, self.html)
        self.assertIn('src="v030-shell.js"', self.html)
        self.assertIn('src="app.js"', self.html)

    def test_patrimoine_metier_conserve(self):
        for function in ('vueAccueil', 'vueOuvrage', 'vueES', 'vueMateriel',
                         'vueVariables', 'vueSupervision', 'vueAdressage',
                         'vueRecette', 'vueReferentiel'):
            self.assertIn('function ' + function, self.app)
        for api in ('/api/es/definir', '/api/es/valider', '/api/materiel/action',
                    '/api/referentiel/cycle/action', '/api/adressage/action'):
            self.assertIn(api, self.app)

    def test_theme_et_accessibilite(self):
        for token in ('ogias-ui-theme', 'data-shell-action', 'data-shell-tab',
                      'prefers-reduced-motion', 'focus-visible'):
            self.assertIn(token, self.shell + self.css)
        self.assertIn('data-theme="light"', self.html)
        self.assertIn('aria-label', self.shell)

    def test_ressources_locales(self):
        for name in ('app.css', 'app.js', 'v030-shell.js',
                     'assets/ogias-logo-entete.png', 'aide.html'):
            self.assertTrue((STATIC / name).is_file(), name)
        # Les scripts, CSS et la fenêtre doivent fonctionner sans service externe.
        for x in ('https://fonts.googleapis.com', 'https://cdn.', 'http://cdn.'):
            self.assertNotIn(x, self.html + self.css + self.shell)


if __name__ == '__main__':
    unittest.main()
