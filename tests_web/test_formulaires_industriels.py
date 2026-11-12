"""Contraste et présentation des formulaires réels ; aucune donnée injectée dans le DOM."""
from pathlib import Path
import os
import re

from support import ServeurNavigateur
import test_variables_v031 as variables_fixture


def contraste_wcag(texte, fond):
    def luminance(couleur):
        composantes = [int(n) / 255 for n in re.findall(r'\d+', couleur)[:3]]
        lineaires = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in composantes]
        return sum(v * poids for v, poids in zip(lineaires, (.2126, .7152, .0722)))
    clair, sombre = sorted((luminance(texte), luminance(fond)), reverse=True)
    return (clair + .05) / (sombre + .05)


class _RecetteVisuelle(ServeurNavigateur):
    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1366, 'height': 768})
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.erreurs = []
        self.page.on('pageerror', lambda e: self.erreurs.append(str(e)))
        self.page.goto(self.url + '#/ouvrages', wait_until='networkidle')

    def tearDown(self):
        self.assertEqual(self.erreurs, [])

    def ouvrir(self, mode='Neuf'):
        self.page.goto(self.url + '#/ouvrages', wait_until='networkidle')
        self.page.locator('#v31-new-project' if mode == 'Neuf' else '#v31-import-project').click()
        self.page.locator('.creation-champ').first.wait_for()

    def capture(self, nom):
        dossier = Path(os.environ.get('OGIAS_CAPTURE_DIR', 'artifacts/ci/captures'))
        dossier.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(dossier / nom), full_page=True)

    def contraste(self, selecteur):
        for e in self.page.locator(selecteur).all():
            if not e.is_visible():
                continue
            couleurs = e.evaluate('''el => {
                let p=el;
                while(p && ['rgba(0, 0, 0, 0)','transparent'].includes(getComputedStyle(p).backgroundColor)) p=p.parentElement;
                return [getComputedStyle(el).color, getComputedStyle(p||document.body).backgroundColor];
            }''')
            self.assertGreaterEqual(contraste_wcag(*couleurs), 4.5, f'{selecteur}: {couleurs}')


class TestCreationIndustrielle(_RecetteVisuelle):
    def test_creation_sombre_labels_et_titres_lisibles(self):
        self.page.locator('#v31-settings').click()
        for mode in ('Neuf', 'Existant'):
            self.ouvrir(mode)
            self.page.locator('.creation-avance summary').click()
            avant = self.api('/api/ouvrage')
            for largeur, hauteur in ((1366, 768), (1920, 1080), (2560, 1440)):
                with self.subTest(mode=mode, largeur=largeur):
                    self.page.set_viewport_size({'width': largeur, 'height': hauteur})
                    self.capture(f'formulaire-{mode.lower()}-sombre-{largeur}.png')
                    self.contraste('.creation-champ>label, .creation-contenu .bloc-tete h2, .creation-avance summary, .creation-avance summary span')
            self.assertEqual(self.api('/api/ouvrage'), avant)

    def test_creation_controles_et_modes_herites_de_la_palette(self):
        self.ouvrir()
        self.page.locator('.creation-avance summary').click()
        avant = self.api('/api/ouvrage')
        requetes = []
        self.page.on('request', lambda r: requetes.append(r.url) if r.method not in ('GET', 'HEAD') else None)
        for theme, fond in (('light', 'rgb(255, 255, 255)'), ('dark', 'rgb(17, 24, 39)')):
            if self.page.locator('html').get_attribute('data-theme') != theme:
                self.page.locator('#v31-settings').click()
            self.page.wait_for_function("bg => ['gerer-listes','proposer-numero'].every(id => getComputedStyle(document.getElementById(id)).backgroundColor === bg)", arg=fond)
            with self.subTest(theme=theme):
                for selecteur in ('#gerer-listes', '#proposer-numero'):
                    self.assertEqual(self.page.locator(selecteur).evaluate('e=>getComputedStyle(e).backgroundColor'), fond)
                    self.contraste(selecteur)
                self.assertNotEqual(self.page.locator('.creation-projet').evaluate('e=>getComputedStyle(e).backgroundColor'), 'rgb(233, 242, 255)')
                self.contraste('.creation-projet')
                self.page.locator('#libelle').focus()
                self.assertNotEqual(self.page.locator('#libelle').evaluate('e=>getComputedStyle(e).outlineStyle'), 'none')
        self.assertEqual(self.api('/api/ouvrage'), avant)
        self.assertEqual(requetes, [])

    def test_creation_une_carte_et_actions_accessibles_aux_trois_resolutions(self):
        self.ouvrir()
        self.page.locator('.creation-avance summary').click()
        avant = self.api('/api/ouvrage')
        for largeur, hauteur in ((1366, 768), (1920, 1080), (2560, 1440)):
            with self.subTest(largeur=largeur):
                self.page.set_viewport_size({'width': largeur, 'height': hauteur})
                self.assertEqual(self.page.locator('.creation-contenu').evaluate('e=>getComputedStyle(e).borderTopWidth'), '0px')
                self.assertEqual(self.page.locator('.creation-contenu').evaluate('e=>getComputedStyle(e).paddingLeft'), '0px')
                self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                creer = self.page.locator('#fiche-creer')
                creer.scroll_into_view_if_needed()
                boite = creer.bounding_box()
                self.assertGreaterEqual(boite['y'], 0)
                self.assertLessEqual(boite['y'] + boite['height'], hauteur)
                self.assertFalse(creer.is_disabled())  # Comportement historique : validation à la soumission.
                self.assertTrue(self.page.locator('#fiche-brouillon').is_visible())
        self.assertEqual(self.api('/api/ouvrage'), avant)

    def test_liste_et_protocoles_sans_modification(self):
        self.page.locator('#v31-settings').click()
        self.ouvrir()
        self.page.locator('.creation-avance summary').click()
        avant, listes = self.api('/api/ouvrage'), self.api('/api/listes-ouvrage')
        self.page.locator('#communication-choix').click()
        self.page.locator('.deroulant-protocoles').wait_for()
        self.assertEqual(self.page.locator('.deroulant-protocoles').evaluate('e=>getComputedStyle(e).backgroundColor'), 'rgb(17, 24, 39)')
        self.page.mouse.click(5, 5)
        self.page.locator('#gerer-listes').click()
        self.page.locator('.onglets-listes').wait_for()
        for groupe in ('lieux', 'types_ouvrage', 'automates', 'protocoles'):
            with self.subTest(groupe=groupe):
                self.page.locator(f'[data-liste="{groupe}"]').click()
                self.contraste('.onglets-listes button, .boite-tete h2, .boite-corps label')
                self.assertEqual(self.page.locator('.onglets-listes button.active').evaluate('e=>getComputedStyle(e).backgroundColor'), 'rgb(37, 99, 235)')
        self.capture('formulaire-listes-sombre-1366.png')
        self.page.locator('#modale [data-fermer]').click()
        self.assertEqual(self.api('/api/ouvrage'), avant)
        self.assertEqual(self.api('/api/listes-ouvrage'), listes)


class TestNiveauxAdressageIndustriels(_RecetteVisuelle):
    # La fixture Variables existante fournit les vraies données, calculées par le moteur.
    def setUp(self):
        variables_fixture.TestVariablesV031.setUp(self)
        self.erreurs = self.errors
        self.page.locator('#v31-settings').click()
        self.page.goto(self.url + '#/adressage', wait_until='networkidle')
        self.page.locator('.carte-niv').first.wait_for()

    def test_cartes_adressage_sombres_et_selection_visible_sans_ecriture(self):
        fichier = Path(self.api('/api/ouvrage')['chemin'])
        avant = fichier.read_bytes()
        adresses = self.api('/api/adressage')
        for niveau in ('physique', 'automate', 'teletransmission'):
            with self.subTest(niveau=niveau):
                carte = self.page.locator(f'[data-niv="{niveau}"]')
                carte.click()
                self.page.mouse.click(5, 5)
                self.assertIn('on', self.page.locator(f'[data-niv="{niveau}"]').get_attribute('class').split())
                active = self.page.locator('.carte-niv.on')
                self.assertEqual(active.evaluate('el=>getComputedStyle(el).outlineStyle'), 'solid')
                self.assertEqual(active.evaluate('el=>getComputedStyle(el).outlineWidth'), '2px')
                for e in self.page.locator('.carte-niv').all():
                    self.assertEqual(e.evaluate('el=>getComputedStyle(el).backgroundColor'), 'rgb(17, 24, 39)')
                self.contraste('.carte-niv b, .carte-niv small')
        self.capture('formulaire-niveaux-sombre-1366.png')
        self.assertEqual(self.api('/api/adressage'), adresses)
        self.assertEqual(fichier.read_bytes(), avant)
