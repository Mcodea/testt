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

    def test_panneau_de_sortie_controles_et_journal(self):
        """Lot 2b : contrôles de l'étape et journal des messages dans le panneau de sortie, réductible (mémorisé)."""
        self.api('/api/equipement/ajouter', {'type': 'MV', 'numero': '02', 'se': '00'})   # équipement à valider
        avant = self.projet.read_bytes()
        self.ouvrir('#/inventaire')
        sortie = self.page.locator('#o-sortie')
        bloquants = sortie.locator('.parcours-points .pp-bloquants')
        bloquants.wait_for()
        self.assertIn('MV02', bloquants.inner_text())
        self.assertEqual(self.page.locator('#vue .parcours-points').count(), 0, 'Plus de bloc de contrôles dans l\'écran')
        self.assertIn('à régler', sortie.locator('.o-sortie-resume').inner_text())
        self.assertTrue(sortie.locator('[data-o-compte="controles"]').inner_text().strip())
        # Réduire : le résumé reste visible, la liste disparaît ; le choix survit au rechargement
        sortie.locator('.o-sortie-plier').click()
        self.assertFalse(bloquants.is_visible())
        self.assertTrue(sortie.locator('.o-sortie-resume').is_visible())
        self.page.reload(wait_until='networkidle')
        self.assertIn('plie', self.page.locator('#o-sortie').get_attribute('class'))
        # Cliquer un onglet réaffiche le panneau ; un message affiché reste au journal
        self.page.locator('#o-sortie [data-o-sortie="journal"]').click()
        self.assertNotIn('plie', self.page.locator('#o-sortie').get_attribute('class'))
        self.page.evaluate("toast('Message fictif de démonstration')")
        self.page.evaluate("toast('Refus fictif', true)")
        journal = self.page.locator('#o-sortie .o-journal li')
        self.assertEqual(journal.count(), 2)
        self.assertIn('Refus fictif', journal.first.inner_text())
        self.assertIn('err', journal.first.get_attribute('class'))
        self.assertEqual(self.page.locator('#o-sortie [data-o-compte="journal"]').inner_text(), '2')
        # Écran sans étape : aucun contrôle
        self.page.locator('#o-explorateur [data-nav="#/referentiel"]').click()
        self.titre('Référentiel métier')
        self.page.locator('#o-sortie [data-o-sortie="controles"]').click()
        self.assertIn('Aucun contrôle', self.page.locator('#o-sortie [data-o-sortie-panneau="controles"]').inner_text())
        self.assertEqual(self.projet.read_bytes(), avant)

    def test_fil_de_l_information(self):
        """Lot 4 : fil de l'équipement sélectionné ; chaque maillon mène à l'écran filtré sur l'équipement."""
        avant = self.projet.read_bytes()
        self.ouvrir('#/inventaire')
        self.assertTrue(self.page.locator('#o-fil').is_hidden(), 'Pas de fil sans équipement sélectionné')
        self.page.locator('#vue [data-v]', has_text='HV01').first.click()
        fil = self.page.locator('#o-fil')
        fil.wait_for()
        self.assertTrue(self.page.locator('#o-fil .o-fil-titre .mono').inner_text().endswith('HV01'))
        maillons = fil.locator('[data-o-maillon]')
        self.assertEqual([m.get_attribute('data-o-maillon') for m in maillons.all()],
                         ['equipement', 'es', 'carte', 'variables', 'supervision'])
        self.assertEqual(fil.locator('[aria-current="true"]').get_attribute('data-o-maillon'), 'equipement')
        self.assertIn('ok', fil.locator('[data-o-maillon="equipement"]').get_attribute('class'))
        # Maillon E/S : liste des E/S filtrée sur l'équipement
        repere = self.page.evaluate("document.querySelector('#o-fil .o-fil-titre .mono').textContent")
        fil.locator('[data-o-maillon="es"]').click()
        self.titre('Liste des E/S')
        self.assertEqual(self.page.locator('#x-equip').input_value(), repere)
        # Maillon Variables (depuis la fiche) : variables de l'équipement seulement
        self.page.locator('#o-explorateur [data-nav="#/inventaire"]').click()
        self.page.locator('#vue [data-v]', has_text='HV01').first.click()
        self.page.locator('#o-fil [data-o-maillon="variables"]').click()
        self.titre('Variables')
        noms = self.page.locator('.v31-variable-row').evaluate_all('rs => rs.map(r => r.dataset.variable)')
        self.assertTrue(noms and all('HV01' in n for n in noms), noms)
        self.assertEqual(self.projet.read_bytes(), avant)

    def test_ruban_equipements_et_fil_des_informations(self):
        """Lot 5a : commandes de l'écran Équipements au ruban (boutons déplacés, identifiants uniques) ; chaque
        commande agit sur l'équipement sélectionné, même après un changement de sélection ; vue « Fil des
        informations » de la fiche."""
        mv = self.api('/api/equipement/ajouter', {'type': 'MV', 'numero': '02', 'se': '00'})['ident']
        self.api('/api/equipement/proposition', {'ident_eq': mv, 'decision': 'retenir'})
        self.api('/api/equipement/valider', {'idents': [mv], 'valide': True})
        avant = self.projet.read_bytes()
        self.ouvrir('#/inventaire')
        ruban = self.page.locator('#o-ruban')
        self.assertEqual(ruban.locator('[role="group"]').evaluate_all('g => g.map(x => x.getAttribute("aria-label"))'),
                         ['Inventaire'])
        for repere in ('HV01', 'MV02', 'HV01'):
            self.page.locator('#vue [data-v]', has_text=repere).first.click()
            self.page.locator('#o-ruban #e-mod').wait_for()
            self.assertEqual(self.page.evaluate("['e-val','e-mod','e-dep','e-sup','b-eq'].map(i => document.querySelectorAll('#' + i).length)"),
                             [1, 1, 1, 1, 1])
            self.page.locator('#o-ruban #e-mod').click()
            self.assertIn(repere, self.page.locator('#modale h2').first.inner_text(), 'La commande vise la sélection courante')
            self.page.keyboard.press('Escape')
            self.page.locator('#modale').wait_for(state='hidden')
        # Retour à l'ouvrage : le groupe de l'équipement disparaît ; autre écran : ruban masqué
        self.page.locator('#vue .noeud.racine').click()
        self.page.wait_for_function("!document.querySelector('#o-ruban #e-val')")
        self.page.locator('#o-explorateur [data-nav="#/es"]').click()
        self.titre('Liste des E/S')
        # Autre écran : ses propres commandes, plus aucune de l'écran Équipements (lot 5b)
        self.page.locator('#o-ruban #x-val').wait_for()
        self.assertEqual(self.page.evaluate("['e-val','b-eq'].map(i => document.querySelectorAll('#' + i).length)"), [0, 0])
        # Fil des informations : une ligne par variable, copiable (tableau dense)
        self.page.locator('#o-explorateur [data-nav="#/inventaire"]').click()
        self.page.locator('#vue [data-v]', has_text='HV01').first.click()
        self.page.locator('[data-onglet-eq="fil"]').click()
        lignes = self.page.locator('#fil-informations table.o-tableau tbody tr')
        lignes.first.wait_for()
        variables = [v for v in self.api('/api/variables')['lignes'] if v['repere'].endswith('HV01')]
        self.assertEqual(self.page.locator('#fil-informations tbody td:nth-child(5)').evaluate_all(
            'cs => cs.map(c => c.innerText.trim()).filter(x => x !== "—").sort()'), sorted(v['nom'] for v in variables))
        self.assertEqual(self.projet.read_bytes(), avant)

    def test_liste_des_es_ruban_et_tableau_dense(self):
        """Lot 5b : commandes de la Liste des E/S au ruban (l'ancien bandeau factice disparaît) ; tableau dense sans
        sélection propre (les cases à cocher de l'écran restent la sélection) ; tri conservé quand l'écran se
        redessine (ouverture d'une ligne)."""
        avant = self.projet.read_bytes()
        self.ouvrir('#/es')
        self.titre('Liste des E/S')
        groupes = self.page.locator('#o-ruban [role="group"]').evaluate_all('g => g.map(x => x.getAttribute("aria-label"))')
        self.assertEqual(groupes, ['Validation du contenu', 'Échanges', 'Étape suivante'])
        self.assertEqual(self.page.locator('.es-ruban').count(), 0, 'Plus de bandeau aux onglets inactifs')
        t = self.page.locator('table.t-es')
        self.assertEqual(t.get_attribute('data-o-pret'), '1')
        self.assertIsNone(t.get_attribute('aria-multiselectable'))
        t.locator('thead th').nth(2).click()
        self.assertEqual(t.locator('thead th').nth(2).get_attribute('aria-sort'), 'ascending')
        self.page.locator('.x-coche').first.check()
        self.assertIn('(1)', self.page.locator('#o-ruban #x-val').inner_text())
        self.assertEqual(self.page.locator('#o-ruban #x-val .o-ico').count(), 1, 'Icône conservée')
        self.page.locator('.es-ligne').first.click()
        self.page.locator('.es-panneau').wait_for()
        self.assertEqual(self.page.locator('table.t-es thead th').nth(2).get_attribute('aria-sort'), 'ascending')
        self.assertEqual(self.page.evaluate("['x-val','x-val-tout','es-export','es-detail-toggle'].map(i => document.querySelectorAll('#' + i).length)"),
                         [1, 1, 1, 1])
        self.assertEqual(self.projet.read_bytes(), avant)

    def test_materiel_ruban_et_grille_de_proprietes(self):
        """Lot 5c : commandes du Matériel au ruban (plus de barre « Autres actions »), propriétés de l'emplacement
        sélectionné en grille, plus d'onglet « Contrôles » en double avec le panneau de sortie."""
        points = self.api('/api/es')['points']
        self.api('/api/es/valider', {'niveau': 'contenu', 'paires': [{'ident_eq': p['ident_eq'], 'cle': p['cle']} for p in points]})
        self.api('/api/materiel/action', {'action': 'appliquer'})
        self.api('/api/modules', {'action': 'implanter'})
        avant = self.projet.read_bytes()
        self.ouvrir('#/materiel')
        self.titre('Matériel')
        groupes = self.page.locator('#o-ruban [role="group"]').evaluate_all('g => g.map(x => x.getAttribute("aria-label"))')
        self.assertEqual(groupes, ['Matériel', 'Voies des E/S', 'Livrables'])
        self.assertEqual(self.page.locator('.v31-actions-more').count(), 0)
        ids = ['m-calc', 'm-valider', 'm-cartes', 'm-impl', 'm-lib', 'x-val', 'x-val-tout', 'm-livrables']
        self.assertEqual(self.page.evaluate("ids => ids.map(i => document.querySelectorAll('#o-ruban #' + i).length)", ids), [1] * len(ids))
        self.page.locator('.rack [data-carte]').first.click()
        self.page.locator('[data-pt-onglet="props"]').click()
        grille = self.page.locator('#pt-inspecteur .pt-props .o-grille')
        self.assertIn('Référence', grille.inner_text())
        self.assertEqual(grille.locator('details[open]').count(), 2)
        self.assertEqual(self.page.locator('[data-pt-onglet="controles"]').count(), 0)
        self.assertEqual(self.projet.read_bytes(), avant)

    def test_variables_ruban_tableau_dense_et_detail(self):
        """Lot 5d : commandes des Variables au ruban (plus de menu « ··· »), table dense triable, détail en grille,
        livrables renvoyés vers Recette."""
        points = self.api('/api/es')['points']
        self.api('/api/es/valider', {'niveau': 'contenu', 'paires': [{'ident_eq': p['ident_eq'], 'cle': p['cle']} for p in points]})
        self.api('/api/materiel/action', {'action': 'appliquer'})
        self.api('/api/materiel/action', {'action': 'valider'})
        avant = self.projet.read_bytes()
        self.ouvrir('#/variables')
        self.page.locator('.v31-variable-row').first.wait_for()
        groupes = self.page.locator('#o-ruban [role="group"]').evaluate_all('g => g.map(x => x.getAttribute("aria-label"))')
        self.assertEqual(groupes, ['Adressage', 'Livrables'])
        ids = ['v31-calculate', 'v31-validate-proposed', 'v31-validate-selection', 'v31-adr-settings', 'v31-livrables']
        self.assertEqual(self.page.evaluate("ids => ids.map(i => document.querySelectorAll('#o-ruban #' + i).length)", ids), [1] * len(ids))
        self.assertEqual(self.page.locator('#v31-var-more').count(), 0)
        # Tri par la colonne Variable, conservé quand le détail s'ouvre (l'écran est redessiné)
        self.page.locator('table.v31-table thead th').nth(1).click()
        self.page.locator('.v31-variable-row').first.click()
        self.page.locator('.v31-variable-detail .o-grille').wait_for()
        self.assertEqual(self.page.locator('table.v31-table thead th').nth(1).get_attribute('aria-sort'), 'ascending')
        self.assertTrue(self.page.evaluate('''() => { const n = [...document.querySelectorAll('.v31-variable-row')].map(x => x.dataset.variable);
          return n.length > 1 && n.every((v, i) => !i || n[i - 1].localeCompare(v, 'fr', {numeric: true}) <= 0); }'''))
        self.assertIn('Adresse télétransmission', self.page.locator('.v31-variable-detail .o-grille').inner_text())
        # Plusieurs pages (150 lignes) : le tri porte sur toute la liste, pas sur la page affichée. Lignes fictives
        # ajoutées en mémoire du navigateur seulement (aucun appel au serveur).
        self.page.locator('#v31-close-detail').click()
        self.page.evaluate('''() => { const base = E.detailEtape.lignes[0];
          E.detailEtape.lignes = Array.from({length: 400}, (_, k) => ({...base, nom: 'ZZ_' + String(399 - k).padStart(3, '0')}))
            .concat([{...base, nom: 'AA_PREMIERE'}]); E.v31Page = 0; vueVariablesV31(); }''')
        entete = self.page.locator('table.v31-table thead th').nth(1)
        premiere = lambda: self.page.locator('.v31-variable-row').first.get_attribute('data-variable')
        self.assertEqual(premiere(), 'AA_PREMIERE')         # tri croissant mémorisé, appliqué à toute la liste
        entete.click()                                       # décroissant
        self.assertEqual(premiere(), 'ZZ_399')
        entete.click()                                       # ordre d'origine
        self.assertEqual(premiere(), 'ZZ_399')
        entete.click()                                       # croissant
        self.assertEqual(premiere(), 'AA_PREMIERE')
        self.assertEqual(self.page.locator('.v31-variable-row').count(), 150)
        self.assertIn('page 1/3', self.page.locator('.v31-table-footer').inner_text())
        # Valider la sélection sans case cochée : refus explicite, rien n'est écrit
        self.page.locator('#v31-validate-selection').click()
        self.assertEqual(self.page.locator('#modale:not([hidden])').count(), 0)
        self.page.locator('#v31-livrables').click()
        self.page.wait_for_function('() => location.hash === "#/recette"')
        self.page.locator('[data-export="variables"]').wait_for()
        self.assertEqual(self.projet.read_bytes(), avant)
