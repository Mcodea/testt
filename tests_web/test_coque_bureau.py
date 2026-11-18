"""Coque de bureau (refonte de l'interface, lot 2a) : menus, explorateur, onglets de documents.

Chaque commande de la coque réutilise une route ou une action existante ; ces essais vérifient qu'elle mène au bon
endroit, au clavier comme à la souris, sans rien écrire dans le projet.
"""
from pathlib import Path

from support import ServeurNavigateur


class TestCoqueBureau(ServeurNavigateur):
    def setUp(self):
        type(self).numero += 1
        self.api('/api/nouveau', {'mode': 'Neuf'})
        if not any(x['code'] == 'XTST' for x in self.api('/api/listes-ouvrage')['lieux']):
            self.api('/api/listes-ouvrage/action', {'action': 'ajouter', 'groupe': 'lieux',
                                                   'code': 'XTST', 'libelle': 'Lieu fictif'})
        self.api('/api/fiche-ouvrage', {'action': 'creer', 'identification': {
            'lieu': 'XTST', 'code_ouvrage': 'RV', 'numero_ouvrage': f'{70 + self.numero:02d}',
            'libelle': 'Coque de bureau fictive', 'automate': 'Sch - M340', 'revision': 'A'}})
        ident = self.api('/api/equipement/ajouter', {'type': 'HV', 'numero': '01', 'se': '00'})['ident']
        self.api('/api/equipement/proposition', {'ident_eq': ident, 'decision': 'retenir'})
        self.api('/api/equipement/valider', {'idents': [ident], 'valide': True})
        self.projet = Path(self.api('/api/ouvrage')['chemin'])
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 900})
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.erreurs = []
        self.page.on('pageerror', lambda e: self.erreurs.append(str(e)))

    def tearDown(self):
        self.assertEqual(self.erreurs, [])

    def ouvrir(self, route='#/dashboard'):
        self.page.goto(self.url + route, wait_until='networkidle')
        self.page.locator('#o-explorateur .o-panneau-tete').wait_for()

    def titre(self, texte):
        self.page.wait_for_function("t => document.querySelector('#v31-title')?.textContent === t", arg=texte)

    def test_menus_a_la_souris_et_au_clavier(self):
        avant = self.projet.read_bytes()
        self.ouvrir()
        noms = self.page.locator('#o-menus > button').all_inner_texts()
        self.assertEqual(noms, ['Fichier', 'Édition', 'Affichage', 'Ouvrage', 'Outils', 'Aide'])
        # Souris : le menu Ouvrage mène à une étape du parcours
        self.page.locator('#o-menus [data-o-menu="3"]').click()
        menu = self.page.locator('.o-menu[role="menu"]')
        self.assertTrue(menu.is_visible())
        menu.get_by_role('menuitem', name='2. Liste des E/S').click()
        self.titre('Liste des E/S')
        self.assertEqual(self.page.locator('.o-menu').count(), 0, 'Le menu se ferme après la commande')
        # Clavier : flèche bas ouvre et donne le focus, flèche droite passe au menu suivant, Échap referme
        self.page.locator('#o-menus [data-o-menu="0"]').focus()
        self.page.keyboard.press('ArrowDown')
        self.assertEqual(self.page.evaluate("document.activeElement.closest('.o-menu')?.getAttribute('aria-label')"), 'Fichier')
        self.page.keyboard.press('ArrowRight')
        self.assertEqual(self.page.locator('.o-menu').get_attribute('aria-label'), 'Édition')
        self.page.keyboard.press('Escape')
        self.assertEqual(self.page.locator('.o-menu').count(), 0)
        self.assertEqual(self.page.evaluate('document.activeElement.dataset.oMenu'), '1')
        # Un clic ailleurs referme aussi le menu
        self.page.locator('#o-menus [data-o-menu="5"]').click()
        self.page.locator('#vue').click(position={'x': 5, 'y': 5})
        self.assertEqual(self.page.locator('.o-menu').count(), 0)
        self.assertEqual(self.projet.read_bytes(), avant)

    def test_explorateur_parcours_et_masquage_memorise(self):
        self.ouvrir()
        etapes = self.page.locator('#o-parcours [data-nav]')
        self.assertEqual(etapes.count(), 5)
        self.assertEqual(self.page.locator('#o-parcours .o-etape.on').count(), 0, 'Tableau de bord : aucune étape active')
        etapes.nth(2).click()
        self.titre('Matériel')
        self.assertEqual(self.page.locator('#o-parcours .o-etape.on .o-etape-lib').inner_text(), 'Matériel')
        self.assertEqual(self.page.locator('#o-parcours [aria-current="step"]').count(), 1)
        # Ctrl B masque l'explorateur ; le choix survit au rechargement ; Ctrl B le réaffiche
        self.page.keyboard.press('Control+b')
        self.assertFalse(self.page.locator('#o-explorateur').is_visible())
        self.assertGreater(self.page.locator('#vue').bounding_box()['x'], -1)
        self.page.reload(wait_until='networkidle')
        self.assertFalse(self.page.locator('#o-explorateur').is_visible())
        self.page.keyboard.press('Control+b')
        self.assertTrue(self.page.locator('#o-explorateur').is_visible())

    def test_onglets_de_documents(self):
        avant = self.projet.read_bytes()
        self.ouvrir('#/es')
        self.titre('Liste des E/S')
        self.page.locator('#o-explorateur [data-nav="#/materiel"]').click()
        self.titre('Matériel')
        onglets = self.page.locator('#o-documents .o-onglet')
        self.assertEqual(onglets.count(), 2)
        self.assertEqual(self.page.locator('#o-documents .o-onglet.on h1#v31-title').inner_text(), 'Matériel')
        # Revenir par l'onglet, puis fermer l'onglet actif : on revient au précédent
        self.page.locator('#o-documents .o-onglet a[data-nav="#/es"]').click()
        self.titre('Liste des E/S')
        self.page.locator('#o-documents .o-onglet.on [data-o-fermer]').click()
        self.titre('Matériel')
        self.assertEqual(onglets.count(), 1)
        self.assertEqual(self.projet.read_bytes(), avant)

    def test_quitter_une_creation_d_ouvrage_ferme_le_brouillon(self):
        """Retour du lot 2a : l'interface appelait /api/fermer en GET (route POST) ; on restait bloqué sur la
        création, sans message. Abandonner une création doit mener à l'écran demandé."""
        self.ouvrir('#/ouvrages')
        self.page.locator('#v31-new-project').click()
        self.titre('Créer un ouvrage')
        reponses = []
        self.page.on('response', lambda r: reponses.append((r.request.method, r.status)) if '/api/fermer' in r.url else None)
        self.page.on('dialog', lambda d: d.accept())
        self.page.locator('#o-explorateur [data-nav="#/referentiel"]').click()
        self.titre('Référentiel métier')
        self.assertEqual(reponses, [('POST', 200)])
