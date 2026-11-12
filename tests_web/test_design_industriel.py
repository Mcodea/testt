"""Présentation industrielle du 12/11 : vraie API, fixture isolée, aucun contenu injecté."""
from pathlib import Path
import json
import os

from support import ServeurNavigateur
import test_variables_v031 as variables_fixture


class TestDesignIndustriel(ServeurNavigateur):
    def setUp(self):
        # Même ouvrage temporaire et mêmes données servies que la recette Variables.
        variables_fixture.TestVariablesV031.setUp(self)

    def tearDown(self):
        self.assertEqual(self.errors, [])

    def capture(self, name):
        folder = Path(os.environ.get('OGIAS_CAPTURE_DIR', 'artifacts/ci/captures'))
        folder.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(folder / name), full_page=True)
        return folder

    def style(self, selector, property):
        return self.page.locator(selector).first.evaluate('(el, p) => getComputedStyle(el)[p]', property)

    def test_palette_typographie_et_theme_sans_ecriture(self):
        project = Path(self.api('/api/ouvrage')['chemin'])
        before = project.read_bytes()
        variables = self.api('/api/variables')['lignes']
        writes = []
        self.page.on('request', lambda r: writes.append(r.url) if r.method not in ('GET', 'HEAD') else None)
        self.assertEqual(self.page.locator('html').get_attribute('data-theme'), 'light')
        self.page.locator('#v31-settings').click()
        self.assertEqual(self.style('body', 'backgroundColor'), 'rgb(11, 15, 25)')
        self.assertEqual(self.style('#v31-sidebar', 'backgroundColor'), 'rgb(15, 22, 35)')
        self.assertEqual(self.style('.v31-main-table', 'backgroundColor'), 'rgb(17, 24, 39)')
        self.assertEqual(self.style('.v31-main-table', 'borderTopColor'), 'rgb(30, 41, 59)')
        self.assertEqual(self.style('.v31-main-table', 'borderTopWidth'), '1px')
        self.assertEqual(self.style('#v31-sidebar', 'backgroundImage'), 'none')
        for selector in ('.v31-main-table', '#v31-current', '#v31-global-search', '#v31-validate-proposed'):
            self.assertEqual(self.style(selector, 'boxShadow'), 'none')
        self.assertIn('OGIAS-Inter', self.style('body', 'fontFamily'))
        for selector in ('.v31-variable-row .mono', '.v31-family'):
            self.assertIn('OGIAS-Mono', self.style(selector, 'fontFamily'))
            self.assertEqual(self.style(selector, 'fontVariantNumeric'), 'tabular-nums')
        for token, color in (('--brand-schneider', '#10b981'), ('--brand-sofrel', '#0ea5e9'),
                             ('--brand-topkapi', '#f59e0b'), ('--status-review', '#8b5cf6'),
                             ('--status-error', '#ef4444')):
            self.assertEqual(self.page.locator('html').evaluate(
                '(el, token) => getComputedStyle(el).getPropertyValue(token).trim().toLowerCase()', token), color)
        self.page.locator('.v31-variable-row').first.press('Enter')
        self.assertEqual(self.style('.v31-variable-detail', 'backgroundColor'), 'rgb(15, 22, 35)')
        self.page.locator('#v31-close-detail').press('Escape')
        self.assertNotEqual(self.style('.v31-variable-row', 'outlineStyle'), 'none')
        self.page.reload(wait_until='networkidle')
        self.assertEqual(self.page.locator('html').get_attribute('data-theme'), 'dark')
        self.page.locator('#v31-settings').click()
        self.assertEqual(self.page.locator('html').get_attribute('data-theme'), 'light')
        self.assertEqual(self.style('body', 'backgroundColor'), 'rgb(241, 245, 249)')
        self.assertEqual(self.api('/api/variables')['lignes'], variables)
        self.assertEqual(project.read_bytes(), before)
        self.assertEqual(writes, [])

    def test_workspace_et_captures_trois_resolutions(self):
        project = Path(self.api('/api/ouvrage')['chemin'])
        before = project.read_bytes()
        self.page.locator('#v31-settings').click()
        measurements = {}
        for width, height in ((1366, 768), (1920, 1080), (2560, 1440)):
            with self.subTest(width=width):
                self.page.set_viewport_size({'width': width, 'height': height})
                for route, selector, name in (('#/dashboard', '.v31-dashboard', 'dashboard'),
                                               ('#/variables', '.v31-main-table', 'variables'),
                                               ('#/materiel', '.rack', 'materiel'),
                                               ('#/inventaire', '#contenu', 'equipements'),
                                               ('#/es', '.es-table', 'es'),
                                               ('#/referentiel', '.ref-corps', 'referentiel'),
                                               ('#/recette', '#r-dossier', 'exports')):
                    self.page.goto(self.url + route, wait_until='networkidle')
                    self.page.locator(selector).first.wait_for()
                    self.page.evaluate('document.fonts.ready')
                    self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                    sidebar = self.page.locator('#v31-sidebar').bounding_box()
                    self.assertEqual(sidebar['width'], 80 if width <= 1400 else 188)
                    self.assertLessEqual(self.page.locator('#v31-top').bounding_box()['height'], 80)
                    self.assertTrue(self.page.locator('#v31-about').is_visible())
                    self.assertTrue(self.page.locator('#v31-sidebar [data-nav="#/recette"] span').is_visible())
                    if route == '#/inventaire':
                        self.assertEqual(self.style('#communication-choix', 'backgroundColor'), 'rgb(17, 24, 39)')
                        self.assertEqual(self.style('.repere-live', 'backgroundColor'), 'rgb(15, 22, 35)')
                    self.capture(f'industriel-{name}-{width}.png')
                self.page.goto(self.url + '#/variables', wait_until='networkidle')
                self.page.locator('.v31-variable-row').first.click()
                self.assertTrue(self.page.locator('#v31-validate-proposed').is_visible())
                self.assertTrue(self.page.locator('#v31-close-detail').is_visible())
                self.assertAlmostEqual(self.page.locator('.v31-variable-row').first.bounding_box()['height'], 44, delta=1)
                folder = self.capture(f'industriel-detail-{width}.png')
                measurements[width] = {'sidebar': sidebar, 'table': self.page.locator('.v31-main-table').bounding_box(),
                                       'detail': self.page.locator('.v31-variable-detail').bounding_box()}
        (folder / 'industriel-mesures.json').write_text(json.dumps(measurements, indent=2) + '\n', encoding='utf-8')
        self.assertEqual(project.read_bytes(), before)

    def test_raccourcis_existants_et_exports_identifies(self):
        project = Path(self.api('/api/ouvrage')['chemin'])
        before = project.read_bytes()
        self.page.locator('#v31-settings').click()
        for route, title in (('#/referentiel', 'Référentiel métier'), ('#/inventaire', 'Équipements'),
                             ('#/es', 'Liste des E/S'), ('#/materiel', 'Matériel'),
                             ('#/variables', 'Variables'), ('#/recette', 'Recette')):
            self.page.locator(f'#v31-sidebar [data-nav="{route}"]').click()
            self.page.wait_for_function('(title) => document.querySelector("#v31-title").textContent === title', arg=title)
            self.assertEqual(self.page.url, self.url + route)
        self.page.locator('#v31-sidebar [data-nav="#/materiel"]').click()
        self.page.locator('#m-calc').wait_for()
        self.page.locator('.v31-actions-more summary').click()
        for selector in ('#x-xsy', '#x-txt'):
            self.assertTrue(self.page.locator(selector).is_visible())
            self.assertEqual(self.style(selector, 'borderLeftColor'), 'rgb(16, 185, 129)')
        self.assertEqual(project.read_bytes(), before)

    def test_cibles_sofrel_et_topkapi_sans_inventer_de_donnees(self):
        automates = self.api('/api/listes-ouvrage')['automates']
        sofrel = next(a for a in automates if 'S4W' in a.upper())
        self.api('/api/nouveau', {'mode': 'Neuf'})
        self.api('/api/fiche-ouvrage', {'action': 'creer', 'identification': {
            'lieu': 'XTST', 'code_ouvrage': 'RV', 'numero_ouvrage': '99',
            'libelle': 'Recette visuelle SOFREL fictive', 'automate': sofrel, 'revision': 'A'}})
        ident = self.api('/api/equipement/ajouter', {'type': 'HV', 'numero': '01', 'se': '00'})['ident']
        self.api('/api/equipement/proposition', {'ident_eq': ident, 'decision': 'retenir'})
        self.api('/api/equipement/valider', {'idents': [ident], 'valide': True})
        points = self.api('/api/es')['points']
        self.api('/api/es/valider', {'niveau': 'contenu', 'paires': [
            {'ident_eq': p['ident_eq'], 'cle': p['cle']} for p in points]})
        project = Path(self.api('/api/ouvrage')['chemin'])
        before = project.read_bytes()
        self.page.locator('#v31-settings').click()
        self.page.goto(self.url + '#/materiel', wait_until='networkidle')
        # La fixture a changé d'ouvrage via l'API : recharger celui-ci dans le navigateur.
        self.page.reload(wait_until='networkidle')
        self.page.locator('.bandeau-materiel').wait_for()
        self.assertEqual(self.api('/api/materiel')['plateforme'], 'S4W')
        self.assertTrue(self.page.locator('.bandeau-materiel.v31-platform-sofrel').is_visible())
        self.assertEqual(self.style('.v31-platform-sofrel', 'borderLeftColor'), 'rgb(14, 165, 233)')
        self.capture('industriel-sofrel-1366.png')
        self.page.goto(self.url + '#/adressage', wait_until='networkidle')
        self.page.locator('.v31-actions-more summary').click()
        self.assertTrue(self.page.locator('#ad-tpk').is_visible())
        self.assertEqual(self.style('#ad-tpk', 'borderLeftColor'), 'rgb(245, 158, 11)')
        self.assertIn('non qualifié', self.page.locator('#ad-tpk').inner_text())
        self.assertEqual(project.read_bytes(), before)

    def test_composition_et_rack_existant_en_sombre_sans_ecriture(self):
        project = Path(self.api('/api/ouvrage')['chemin'])
        before = project.read_bytes()
        material = self.api('/api/materiel')
        self.page.locator('#v31-settings').click()
        self.page.goto(self.url + '#/materiel', wait_until='networkidle')
        self.page.locator('.grille-compo').wait_for()
        self.assertEqual(self.style('.grille-compo', 'display'), 'grid')
        self.assertEqual(self.style('.grille-compo fieldset', 'borderTopColor'), 'rgb(30, 41, 59)')
        self.assertIn('OGIAS-Mono', self.style('.grille-compo select', 'fontFamily'))
        for field in ('alimentation', 'processeur'):
            self.assertTrue(self.page.locator(f'[data-cfg="{field}"]').is_visible())
        self.capture('industriel-composition-1366.png')
        self.page.locator('.rack').first.scroll_into_view_if_needed()
        self.assertEqual(self.style('.emplacement.a-choisir', 'borderTopStyle'), 'dashed')
        self.assertEqual(self.style('.emplacement.a-choisir', 'borderTopColor'), 'rgb(139, 92, 246)')
        self.assertEqual(self.style('.emplacement.alim', 'backgroundColor'), 'rgb(15, 22, 35)')
        references = self.page.locator('.emplacement.carte b').all_text_contents()
        self.assertEqual(references, [m['reference'] for m in self.api('/api/es')['modules']])
        self.assertTrue(self.page.locator('#m-nomenclature').is_visible())
        self.capture('industriel-rack-1366.png')
        self.assertEqual(self.api('/api/materiel'), material)
        self.assertEqual(project.read_bytes(), before)

    def test_voies_occupees_et_libres_gardent_leurs_actions(self):
        self.api('/api/modules', {'action': 'implanter'})
        project = Path(self.api('/api/ouvrage')['chemin'])
        before = project.read_bytes()
        self.page.locator('#v31-settings').click()
        self.page.goto(self.url + '#/materiel', wait_until='networkidle')
        self.assertEqual(self.style('.rack-corps', 'display'), 'grid')
        self.assertEqual(self.style('.rack-tete', 'backgroundColor'), 'rgb(15, 22, 35)')
        self.assertEqual(self.style('#vue .bloc', 'backgroundColor'), 'rgb(17, 24, 39)')
        self.assertEqual(self.style('#vue .bloc', 'borderTopColor'), 'rgb(30, 41, 59)')
        self.page.locator('[data-carte]').first.click()
        table = self.page.locator('.voies-carte')
        table.wait_for()
        self.assertGreater(table.locator('tbody tr.libre').count(), 0)
        self.assertGreater(table.locator('tbody tr:not(.libre)').count(), 0)
        self.assertEqual(self.style('.voies-carte th', 'position'), 'sticky')
        self.assertEqual(self.style('.voies-carte tr.libre td', 'backgroundColor'), 'rgb(15, 22, 35)')
        self.assertEqual(self.style('.voies-carte tr:not(.libre) td', 'borderLeftColor'), 'rgb(16, 185, 129)')
        self.assertTrue(self.page.locator('.cv-deplacer').first.is_visible())
        self.assertIn('OGIAS-Mono', self.style('.voies-carte select', 'fontFamily'))
        self.capture('industriel-voies-1366.png')
        self.page.locator('#modale [data-fermer]').click()
        self.assertEqual(project.read_bytes(), before)

    def test_entete_reste_visible_au_defilement_sans_modifier_les_variables(self):
        for number in range(2, 13):
            ident = self.api('/api/equipement/ajouter', {'type': 'HV', 'numero': f'{number:02d}', 'se': '00'})['ident']
            self.api('/api/equipement/proposition', {'ident_eq': ident, 'decision': 'retenir'})
        project = Path(self.api('/api/ouvrage')['chemin'])
        before = project.read_bytes()
        self.page.reload(wait_until='networkidle')
        self.page.locator('#v31-settings').click()
        area = self.page.locator('.v31-table-area')
        self.assertGreater(area.evaluate('el => el.scrollHeight - el.clientHeight'), 100)
        header = self.page.locator('.v31-table th').first
        top = header.bounding_box()['y']
        area.evaluate('el => el.scrollTop = 300')
        self.assertAlmostEqual(header.bounding_box()['y'], top, delta=1)
        self.assertEqual(self.style('.v31-table th', 'position'), 'sticky')
        self.assertEqual(project.read_bytes(), before)
