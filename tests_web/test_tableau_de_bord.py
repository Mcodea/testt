"""Indicateurs et navigation du tableau de bord, sans écriture dans le projet."""
from collections import Counter
from pathlib import Path

from support import ServeurNavigateur


class TestTableauDeBord(ServeurNavigateur):
    def setUp(self):
        type(self).numero += 1
        self.api('/api/nouveau', {'mode': 'Neuf'})
        if not any(x['code'] == 'XTST' for x in self.api('/api/listes-ouvrage')['lieux']):
            self.api('/api/listes-ouvrage/action', {'action': 'ajouter', 'groupe': 'lieux',
                                                   'code': 'XTST', 'libelle': 'Lieu fictif'})
        self.api('/api/fiche-ouvrage', {'action': 'creer', 'identification': {
            'lieu': 'XTST', 'code_ouvrage': 'RV', 'numero_ouvrage': f'{self.numero:02d}',
            'libelle': 'Tableau de bord fictif', 'automate': 'M340', 'revision': 'A'}})
        self.ident = self.api('/api/equipement/ajouter', {'type': 'HV', 'numero': '01', 'se': '00'})['ident']
        self.api('/api/equipement/proposition', {'ident_eq': self.ident, 'decision': 'retenir'})
        self.api('/api/equipement/valider', {'idents': [self.ident], 'valide': True})
        self.projet = Path(self.api('/api/ouvrage')['chemin'])
        self.context = self.browser.new_context(viewport={'width': 1920, 'height': 1080})
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.erreurs = []
        self.page.on('pageerror', lambda e: self.erreurs.append(str(e)))

    def tearDown(self):
        self.assertEqual(self.erreurs, [])

    def ouvrir(self):
        self.page.goto(self.url + '#/dashboard', wait_until='networkidle')
        self.page.wait_for_selector('.v31-dashboard')

    def test_repartition_es_identique_aux_points_du_moteur(self):
        points = self.api('/api/es')['points']
        attendus = Counter(p['point'] for p in points)
        self.assertTrue(attendus)
        avant = self.projet.read_bytes()
        self.ouvrir()
        legende = self.page.locator('.v31-stack-legend').inner_text()
        self.assertTrue(legende)
        for nature, nombre in attendus.items():
            self.assertIn(f'{nature} {nombre}', legende)
            segment = self.page.locator(f'.v31-stack-piece[title="{nature}: {nombre}"]')
            self.assertEqual(segment.count(), 1)
            self.assertGreater(segment.bounding_box()['width'], 0)
        self.assertEqual(self.projet.read_bytes(), avant)

    def test_quatre_natures_du_contrat_affichees_sans_second_accent_corail(self):
        # Contrat visuel synthétique uniquement : aucune adresse, aucun matériel créé.
        donnees = {'points': [{'point': nature} for nature in ('ET', 'ST', 'EA', 'SA')]}
        self.page.route('**/api/es', lambda r: r.fulfill(status=200, json=donnees))
        self.ouvrir()
        for nature in ('ET', 'ST', 'EA', 'SA'):
            self.assertEqual(self.page.locator(f'.v31-stack-piece[title="{nature}: 1"]').count(), 1)
            self.assertIn(f'{nature} 1', self.page.locator('.v31-stack-legend').inner_text())
        couleur = self.page.locator('.v31-f-SA').evaluate('e => getComputedStyle(e).backgroundColor')
        self.assertNotEqual(couleur, 'rgb(242, 140, 91)')

    def test_cinq_etapes_accessibles_sans_ecriture(self):
        avant = self.projet.read_bytes()
        self.ouvrir()
        for route, titre in (('inventaire', 'Équipements'), ('es', 'Liste des E/S'),
                             ('materiel', 'Matériel'), ('variables', 'Variables'), ('recette', 'Recette')):
            with self.subTest(route=route):
                etape = self.page.locator(f'#v31-progress [data-nav="#/{route}"]')
                self.assertTrue(etape.is_visible())
                self.assertIn(' : ', etape.get_attribute('title'))
                etape.click()
                self.page.wait_for_url(self.url + '#/' + route)
                self.page.wait_for_function("titre => document.querySelector('#v31-title')?.textContent === titre", arg=titre)
                self.assertEqual(self.page.locator('#v31-title').inner_text(), titre)
                self.assertEqual(self.projet.read_bytes(), avant)
                self.page.goto(self.url + '#/dashboard', wait_until='networkidle')

    def test_chargement_lent_du_tableau_de_bord_ne_remplace_pas_l_etape_choisie(self):
        # Course reproduite en CI Windows : la réponse tardive d'un écran quitté
        # ne doit jamais réafficher cet écran par-dessus l'étape demandée ensuite.
        self.ouvrir()
        retenues = []
        self.page.route('**/api/es', lambda r: retenues.append(r))
        self.page.evaluate("location.hash = '#/ouvrages'")
        self.page.wait_for_function("document.querySelector('#v31-title')?.textContent === 'Mes ouvrages'")
        self.page.evaluate("location.hash = '#/dashboard'")
        for _ in range(100):
            if retenues:
                break
            self.page.wait_for_timeout(20)
        self.assertEqual(len(retenues), 1)
        self.page.evaluate("location.hash = '#/recette'")
        self.page.wait_for_function("document.querySelector('#v31-title')?.textContent === 'Recette'")
        with self.page.expect_response('**/api/variables'):
            retenues[0].continue_()
        self.page.wait_for_timeout(300)
        self.assertEqual(self.page.locator('#v31-title').inner_text(), 'Recette')
        self.assertTrue(self.page.url.endswith('#/recette'))

    def test_es_indisponibles_ne_sont_pas_affichees_comme_zero(self):
        self.api('/api/equipement/valider', {'idents': [self.ident], 'valide': False})
        avant = self.projet.read_bytes()
        self.ouvrir()
        carte = self.page.locator('.v31-kpi').nth(1)
        self.assertIn('Non disponible', carte.inner_text())
        self.assertNotIn('0 contenu', carte.inner_text())
        self.assertIn('indisponible', self.page.locator('.v31-dash-activity').inner_text().lower())
        self.assertEqual(self.page.locator('.v31-stack').count(), 0)
        self.assertEqual(self.projet.read_bytes(), avant)

    def test_zero_connu_signale_sans_compteur_nul_ni_taux_de_recette_fabrique(self):
        # Contrat d'affichage : réponse synthétique à zéro, sans modifier le moteur.
        def recette_sans_anomalie(route):
            route.fulfill(status=200, json={'erreurs': 0, 'alertes': 0, 'controles': []})
        self.page.route('**/api/recette', recette_sans_anomalie)
        self.ouvrir()
        carte = self.page.locator('.v31-kpi').nth(3)
        self.assertIn('Aucun point à traiter', carte.inner_text())
        self.assertEqual(carte.locator('.v31-kpi-value').count(), 0)
        self.assertNotIn('Non disponible', carte.inner_text())
        self.assertNotRegex(carte.inner_text(), r'\b0\b')
        self.assertEqual(self.page.locator('.v31-ring').count(), 0)
        self.assertIn('taux', self.page.locator('.v31-dash-recette').inner_text().lower())

    def test_ouvrage_sans_equipement_signale_ses_etats_vides_sans_compteur_nul(self):
        self.api('/api/equipement/supprimer', {'idents': [self.ident]})
        avant = self.projet.read_bytes()
        self.ouvrir()
        for index, texte in ((0, 'Aucun équipement'), (1, 'Aucune E/S'), (2, 'Aucune variable')):
            carte = self.page.locator('.v31-kpi').nth(index)
            self.assertIn(texte, carte.inner_text())
            self.assertNotIn('Non disponible', carte.inner_text())
            self.assertEqual(carte.locator('.v31-kpi-value').count(), 0)
            self.assertNotRegex(carte.inner_text(), r'\b0\b')
        self.assertIn('Aucune E/S', self.page.locator('.v31-dash-activity').inner_text())
        self.assertNotRegex(self.page.locator('.v31-dash-activity').inner_text(), r'\b0\b')
        self.assertEqual(self.projet.read_bytes(), avant)

    def test_taux_incoherent_non_affiche(self):
        self.page.route('**/api/recette', lambda r: r.fulfill(status=200, json={
            'erreurs': 0, 'alertes': 0, 'controles': [], 'controles_total': 1, 'controles_conformes': 2}))
        self.ouvrir()
        self.assertEqual(self.page.locator('.v31-ring').count(), 0)

    def test_resume_non_nul_sans_detail_ne_devient_pas_aucune_anomalie(self):
        self.page.route('**/api/recette', lambda r: r.fulfill(status=200, json={
            'erreurs': 2, 'alertes': 0, 'controles': []}))
        self.ouvrir()
        self.assertEqual(self.page.locator('.v31-kpi').nth(3).locator('.v31-kpi-value').inner_text(), '2')
        self.assertNotIn('Aucune anomalie', self.page.locator('.v31-dash-recette').inner_text())

    def test_recette_indisponible_ne_donne_pas_un_faux_bilan_sans_anomalie(self):
        self.page.route('**/api/recette', lambda r: r.fulfill(status=503, json={'erreur': 'Essai fictif'}))
        self.ouvrir()
        self.assertIn('Non disponible', self.page.locator('.v31-kpi').nth(3).inner_text())
        recette = self.page.locator('.v31-dash-recette').inner_text()
        self.assertIn('indisponible', recette.lower())
        self.assertNotIn('Aucune anomalie', recette)
        self.assertEqual(self.page.locator('.v31-ring').count(), 0)
