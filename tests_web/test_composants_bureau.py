"""Composants de bureau (refonte de l'interface, lot 3) : tableau dense, menu contextuel, grille de propriétés,
raccourcis. Essais sur le tableau des contrôles de la Recette (lecture seule), sans écriture dans le projet."""
from pathlib import Path

from support import ServeurNavigateur

LIGNES = "() => [...document.querySelectorAll('table.o-tableau tbody tr')].map(r => r.cells[3].innerText.trim())"


class TestComposantsBureau(ServeurNavigateur):
    def setUp(self):
        type(self).numero += 1
        self.api('/api/nouveau', {'mode': 'Neuf'})
        if not any(x['code'] == 'XTST' for x in self.api('/api/listes-ouvrage')['lieux']):
            self.api('/api/listes-ouvrage/action', {'action': 'ajouter', 'groupe': 'lieux',
                                                   'code': 'XTST', 'libelle': 'Lieu fictif'})
        self.api('/api/fiche-ouvrage', {'action': 'creer', 'identification': {
            'lieu': 'XTST', 'code_ouvrage': 'RV', 'numero_ouvrage': f'{80 + self.numero:02d}',
            'libelle': 'Composants fictifs', 'automate': 'Sch - M340', 'revision': 'A'}})
        for numero in ('01', '02'):
            ident = self.api('/api/equipement/ajouter', {'type': 'HV', 'numero': numero, 'se': '00'})['ident']
            self.api('/api/equipement/proposition', {'ident_eq': ident, 'decision': 'retenir'})
            self.api('/api/equipement/valider', {'idents': [ident], 'valide': True})
        self.projet = Path(self.api('/api/ouvrage')['chemin'])
        self.avant = self.projet.read_bytes()
        self.context = self.browser.new_context(viewport={'width': 1600, 'height': 900})
        self.context.grant_permissions(['clipboard-read', 'clipboard-write'], origin=self.url.rstrip('/'))
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.erreurs = []
        self.page.on('pageerror', lambda e: self.erreurs.append(str(e)))

    def tearDown(self):
        self.assertEqual(self.erreurs, [])
        self.assertEqual(self.projet.read_bytes(), self.avant, 'Les composants ne doivent rien écrire')

    def tableau(self):
        self.page.goto(self.url + '#/recette', wait_until='networkidle')
        self.page.evaluate("document.querySelector('details.rc-controles').open = true")
        self.page.locator('[data-rc-vue="detail"]').click()          # 18/11 : vue « Détail », un constat par ligne
        self.page.evaluate("document.querySelector('details.rc-controles').open = true")
        t = self.page.locator('table[data-o-cle="recette-controles"]')
        t.wait_for()
        t.scroll_into_view_if_needed()
        self.assertGreaterEqual(t.locator('tbody tr').count(), 3, 'Jeu d\'essai : au moins trois contrôles')
        return t

    def test_tri_trois_etats(self):
        t = self.tableau()
        origine = self.page.evaluate(LIGNES)
        titre = t.locator('thead th').nth(3)
        titre.click()
        self.assertEqual(titre.get_attribute('aria-sort'), 'ascending')
        croissant = self.page.evaluate(LIGNES)
        self.assertEqual(croissant, sorted(origine, key=lambda s: s.lower()))
        titre.click()
        self.assertEqual(titre.get_attribute('aria-sort'), 'descending')
        self.assertEqual(self.page.evaluate(LIGNES), croissant[::-1])
        titre.click()
        self.assertIsNone(titre.get_attribute('aria-sort'))
        self.assertEqual(self.page.evaluate(LIGNES), origine, 'Troisième clic : ordre d\'origine')
        # Clavier : Entrée sur le titre trie aussi
        titre.focus()
        self.page.keyboard.press('Enter')
        self.assertEqual(titre.get_attribute('aria-sort'), 'ascending')

    def test_selection_souris_et_clavier_puis_copie_excel(self):
        t = self.tableau()
        lignes = t.locator('tbody tr')
        lignes.nth(0).click()
        lignes.nth(2).click(modifiers=['Shift'])
        self.assertEqual(t.locator('tbody tr[aria-selected="true"]').count(), 3)
        lignes.nth(1).click(modifiers=['Control'])
        self.assertEqual(t.locator('tbody tr[aria-selected="true"]').count(), 2)
        # Copie : titres puis lignes sélectionnées, séparés par des tabulations ; colonne d'actions ignorée
        self.page.keyboard.press('Control+c')
        texte = self.page.evaluate('navigator.clipboard.readText()').split('\r\n')
        self.assertEqual(texte[0], 'Niveau\tRègle\tÉtape\tConstat')
        self.assertEqual(len(texte), 3)
        self.assertTrue(all(len(x.split('\t')) == 4 for x in texte))
        self.assertIn('copiée', self.page.locator('#o-sortie .o-journal li').first.inner_text())
        # Clavier : Échap vide, flèche bas avec Maj étend, Ctrl A sélectionne tout
        lignes.nth(0).focus()
        self.page.keyboard.press('Escape')
        self.assertEqual(t.locator('tbody tr[aria-selected="true"]').count(), 0)
        self.page.keyboard.press('Shift+ArrowDown')
        self.page.keyboard.press('Shift+ArrowDown')
        self.assertEqual(t.locator('tbody tr[aria-selected="true"]').count(), 3)
        self.page.keyboard.press('Control+a')
        self.assertEqual(t.locator('tbody tr[aria-selected="true"]').count(), lignes.count())

    def test_action_d_une_ligne_garde_son_comportement(self):
        t = self.tableau()
        bouton = t.locator('tbody tr').first.locator('button.r-corr')
        bouton.click()
        self.page.wait_for_function("location.hash !== '#/recette'")

    def test_menu_contextuel_filtres_et_redimensionnement(self):
        t = self.tableau()
        total = t.locator('tbody tr').count()
        t.locator('thead th').nth(2).click(button='right')
        menu = self.page.locator('.o-contextuel')
        self.assertTrue(menu.is_visible())
        self.assertIn('Trier « Étape »', menu.inner_text())
        self.page.keyboard.press('Escape')
        self.assertEqual(self.page.locator('.o-contextuel').count(), 0)
        # Menu au clavier (Maj F10) puis filtres par colonne
        t.locator('tbody tr').first.focus()
        self.page.keyboard.press('Shift+F10')
        self.page.locator('.o-contextuel button', has_text='Filtrer les colonnes').click()
        filtre = t.locator('tr.o-filtres input').nth(0)
        filtre.fill('Alerte')
        visibles = t.locator('tbody tr:visible').count()
        self.assertGreaterEqual(visibles, 1)
        self.assertLess(visibles, total)
        self.assertIn('filtre actif', self.page.locator('.o-tableau-filtre').inner_text())
        t.locator('thead th').nth(0).click(button='right')
        self.page.locator('.o-contextuel button', has_text='Masquer les filtres').click()
        self.assertEqual(t.locator('tbody tr:visible').count(), total)
        # Redimensionner une colonne à la souris
        titre = t.locator('thead th').nth(1)
        avant = titre.bounding_box()['width']
        poignee = titre.locator('.o-poignee').bounding_box()
        self.page.mouse.move(poignee['x'] + 3, poignee['y'] + 10)
        self.page.mouse.down()
        self.page.mouse.move(poignee['x'] + 83, poignee['y'] + 10, steps=4)
        self.page.mouse.up()
        self.assertGreater(titre.bounding_box()['width'], avant + 40)

    def test_grille_de_proprietes_et_raccourcis(self):
        self.tableau()
        html = self.page.evaluate("""() => { const d = document.createElement('div');
          d.innerHTML = Composants.grille([{titre: 'Variable', proprietes: [
            {libelle: 'Nom', valeur: 'TS_RV01HV01_FER', mono: true},
            {libelle: 'Règle', valeur: '<b>texte</b>', lecture: true},
            {libelle: 'Commentaire', valeur: ''}]}]);
          document.body.append(d); const r = {
            groupes: d.querySelectorAll('details[open]').length, props: d.querySelectorAll('.o-prop').length,
            mono: d.querySelector('dd.mono').textContent, echappe: d.querySelectorAll('dd b').length,
            lecture: d.querySelectorAll('.o-prop.lecture').length, vide: d.querySelector('.o-sans-valeur').textContent};
          d.remove(); return r; }""")
        self.assertEqual(html, {'groupes': 1, 'props': 3, 'mono': 'TS_RV01HV01_FER', 'echappe': 0,
                                'lecture': 1, 'vide': '—'})
        self.page.keyboard.press('Control+/')
        boite = self.page.locator('#modale .o-raccourcis')
        boite.wait_for()
        self.assertIn('Ctrl C', boite.inner_text())
        self.assertIn('Copier vers Excel', boite.inner_text())
