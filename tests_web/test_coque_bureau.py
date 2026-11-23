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

    def test_outils_ingenierie_supervision_et_regles_propres(self):
        """18/11 : outils d'ingénierie de l'ouvrage, choisis dans les listes ; règles propres affichées et appliquées."""
        self.ouvrir('#/inventaire')
        bloc = self.page.locator('#bloc-outils')
        bloc.locator('#outil-supervision').wait_for()
        texte = bloc.inner_text()
        self.assertIn('Sch - M340', texte)
        self.assertIn('M340 : valeur 32 bits sur une adresse %MW paire.', texte)
        self.assertIn('TOPKAPI : libellé de 40 caractères au plus.', texte)
        self.assertEqual(bloc.locator('#outil-supervision').input_value(), 'TOPKAPI')
        # Supervision « Aucune » : la règle TOPKAPI n'est plus listée ni appliquée
        bloc.locator('#outil-supervision').select_option('')
        self.page.wait_for_function("() => !document.querySelector('#bloc-outils').innerText.includes('TOPKAPI : libellé')")
        self.assertEqual(self.api('/api/outils')['supervision'], '')
        self.assertEqual(self.api('/api/outils')['contraintes'], ['M340 : valeur 32 bits sur une adresse %MW paire.'])
        # IHM : choix dans la liste ; une valeur absente du référentiel est refusée côté serveur
        bloc = self.page.locator('#bloc-outils')
        bloc.locator('#outil-ihm').select_option('Vijeo Designer')
        self.page.wait_for_function("() => document.querySelector('#outil-ihm')?.value === 'Vijeo Designer'")
        self.assertEqual(self.api('/api/outils')['ihm'], 'Vijeo Designer')
        with self.assertRaises(Exception):
            self.api('/api/outils/action', {'supervision': 'Outil inventé'})
        self.assertEqual(self.api('/api/outils')['supervision'], '')

    def test_plan_memoire_et_reprise_des_reglages(self):
        """18/11 : plan mémoire %MW modifiable dans Adressage ; refus d'un recouvrement sans rien écrire ; reprise des
        réglages d'un autre ouvrage depuis le bloc Outils d'ingénierie."""
        self.ouvrir('#/adressage')
        self.page.locator('[data-plage-debut="TS"]').wait_for()
        self.page.locator('[data-plage-fin="TS"]').fill('2100')                  # recouvre TC : refusé
        self.page.locator('#ad-plages').click()
        self.page.wait_for_function("() => document.querySelector('#toasts')?.innerText.includes('recouvrement')")
        self.assertEqual(self.api('/api/adressage')['plages']['TS'], [1000, 1999])
        self.page.locator('[data-plage-debut="TS"]').fill('5000')
        self.page.locator('[data-plage-fin="TS"]').fill('5999')
        self.page.locator('#ad-plages').click()
        self.page.wait_for_function("() => document.querySelector('[data-plage-debut=\"TS\"]')?.value === '5000'")
        self.assertEqual(self.api('/api/adressage')['plages']['TS'], [5000, 5999])
        # Reprise : un second ouvrage fictif enregistré sert de source (supervision « aucune », TS %MW8000-8999)
        cible = self.api('/api/ouvrage')['chemin']
        self.api('/api/nouveau', {'mode': 'Neuf'})
        self.api('/api/fiche-ouvrage', {'action': 'creer', 'identification': {
            'lieu': 'XTST', 'code_ouvrage': 'RV', 'numero_ouvrage': f'{40 + self.numero:02d}',
            'libelle': 'Source fictive des réglages', 'automate': 'Sch - M340', 'revision': 'A'}})
        self.api('/api/outils/action', {'supervision': ''})
        plages = self.api('/api/adressage')['plages_defaut'] | {'TS': [8000, 8999]}
        self.api('/api/adressage/action', {'action': 'plages', 'plages': plages})
        source = self.api('/api/ouvrage')['chemin']
        self.api('/api/ouvrir', {'chemin': cible})
        sources = self.api('/api/reglages/sources')['ouvrages']
        self.assertNotIn(cible, [x['chemin'] for x in sources])
        self.assertIn(source, [x['chemin'] for x in sources])
        self.ouvrir('#/inventaire')
        self.page.locator('#outils-reprendre').click()
        self.page.locator('#reprendre-source').select_option(source)
        self.page.locator('#reprendre-ok').click()
        self.page.wait_for_function("() => document.querySelector('#toasts')?.innerText.includes('Repris')")
        self.assertEqual(self.api('/api/ouvrage')['chemin'], cible)
        self.assertEqual(self.api('/api/ouvrage')['identification']['libelle'], 'Coque de bureau fictive')
        self.assertEqual(self.api('/api/adressage')['plages']['TS'], [8000, 8999])
        self.assertEqual(self.api('/api/outils')['supervision'], '')

    def test_standards_ingenierie_ecran_et_creation(self):
        """19/11 : écran « Standards d'ingénierie » (explorateur), choix du standard à la création, mention « créé
        selon… » et écarts dans le bloc Outils d'ingénierie de l'ouvrage."""
        self.assertEqual(self.api('/api/outils')['standard']['ident'], 'standard-initial')
        self.ouvrir('#/dashboard')
        self.page.locator('#o-explorateur a[href="#/standards"]').click()
        self.titre("Standards d’ingénierie")
        self.page.locator('[data-std="standard-initial"]').wait_for()
        texte = self.page.locator('.std-detail').inner_text()
        for attendu in ('Référentiel métier', 'Charte de nommage', "Plan d'adressage", "Chaîne d'outils", 'TOPKAPI', '%MW1000'):
            self.assertIn(attendu, texte)
        self.assertGreaterEqual(int(self.page.locator('[data-std="standard-initial"] td.num').inner_text()), 1)
        # Création d'un ouvrage : le standard actif est proposé et envoyé
        self.api('/api/nouveau', {'mode': 'Neuf'})
        self.ouvrir('#/inventaire')
        self.page.wait_for_function("() => document.querySelector('#standard-choix')?.value === 'standard-initial'")
        with self.assertRaisesRegex(RuntimeError, 'Standard d.ingénierie introuvable'):
            self.api('/api/fiche-ouvrage', {'action': 'creer', 'standard': 'client-inexistant', 'identification': {
                'lieu': 'XTST', 'code_ouvrage': 'RV', 'numero_ouvrage': f'{20 + self.numero:02d}',
                'libelle': 'Standard inconnu', 'automate': 'Sch - M340', 'revision': 'A'}})
        # Bloc Outils de l'ouvrage existant : mention du standard puis écart local signalé
        self.api('/api/ouvrir', {'chemin': str(self.projet)})
        self.api('/api/outils/action', {'ihm': 'Vijeo Designer'})
        self.page.reload(wait_until='networkidle')                      # même adresse : rechargement explicite
        self.page.wait_for_function("() => document.querySelector('.outils-standard')?.innerText.includes('Standard initial')")
        self.assertIn('IHM : Vijeo Designer', self.page.locator('.outils-standard').inner_text())

    def test_standards_bibliotheque_et_application(self):
        """19/11, étape 2 : nouvelle brique et nouveau standard depuis l'écran, puis application à un ouvrage existant
        après aperçu (rien n'est écrit avant la confirmation)."""
        n = self.numero
        self.ouvrir('#/standards')
        self.page.locator('[data-nouvelle-brique="adressage"]').click()
        self.page.locator('#brique-nom').fill(f'Plan fictif {n}')
        self.page.locator('[data-brique-debut="TS"]').fill('5000')
        self.page.locator('[data-brique-fin="TS"]').fill('5999')
        self.page.locator('#brique-ok').click()
        self.page.wait_for_function("t => document.querySelector('.std-bibliotheque')?.innerText.includes(t)", arg=f'Plan fictif {n}')
        self.page.locator('#std-nouveau').click()
        self.page.locator('#std-nom').fill(f'Client fictif {n}')
        plan = next(b['ident'] for b in self.api('/api/standards')['bibliotheque']['adressage'] if b['nom'] == f'Plan fictif {n}')
        self.page.locator('#std-adressage').select_option(plan)
        self.page.locator('#std-ok').click()
        self.page.wait_for_function("t => document.querySelector('.std-detail h2')?.innerText.includes(t)", arg=f'Client fictif {n}')
        ident = next(s['ident'] for s in self.api('/api/standards')['standards'] if s['nom'] == f'Client fictif {n}')
        # Application à l'ouvrage ouvert : aperçu d'abord, rien d'écrit
        self.ouvrir('#/inventaire')
        self.page.locator('#outils-appliquer-standard').click()
        self.page.locator('#appliquer-standard').select_option(ident)
        self.page.wait_for_function("() => document.querySelector('#appliquer-apercu')?.innerText.includes('%MW5000')")
        self.assertEqual(self.api('/api/adressage')['plages']['TS'], [1000, 1999])
        self.page.locator('#appliquer-ok').click()
        self.page.wait_for_function("() => document.querySelector('#toasts')?.innerText.includes('appliqué')")
        self.assertEqual(self.api('/api/adressage')['plages']['TS'], [5000, 5999])
        self.assertEqual(self.api('/api/outils')['standard']['ident'], ident)
        # Nouvelle version du standard : l'ouvrage n'est pas modifié, l'évolution est signalée
        self.api('/api/standards/action', {'action': 'reviser', 'ident': ident, 'motif': 'Essai fictif',
                                           'choix': {'adressage': 'adressage-defaut', 'outils': 'outils-topkapi'}})
        self.assertEqual(self.api('/api/adressage')['plages']['TS'], [5000, 5999])
        self.page.reload(wait_until='networkidle')
        self.page.wait_for_function("() => document.querySelector('#outils-appliquer-standard')?.innerText.includes('version 2')")
        self.assertIn('a évolué', self.page.locator('.outils-standard').inner_text())

    def test_charte_de_nommage_construite_dans_ogias(self):
        """19/11 : charte d'un client construite segment par segment, aperçu contrôlé en direct ; un ouvrage créé
        selon le standard de ce client a ses repères et ses noms fabriqués selon la charte."""
        n = self.numero
        self.ouvrir('#/standards')
        self.page.locator('[data-nouvelle-brique="charte"]').click()
        self.page.locator('#brique-nom').fill(f'Charte fictive {n}')
        self.page.wait_for_function("() => document.querySelector('#charte-apercu')?.innerText.includes('XTSTRV01PM01')")
        self.page.locator('[data-ajout="ouvrage"]').select_option('texte')
        self.page.locator('[data-ajouter="ouvrage"]').click()
        self.page.wait_for_function("() => document.querySelector('#charte-apercu')?.innerText.includes('Texte fixe')")
        self.page.locator('.std-seg[data-partie="ouvrage"][data-i="3"] [data-champ="valeur"]').fill('EAU')
        self.page.locator('.std-seg[data-partie="ouvrage"][data-i="3"] [data-bouger="-1"]').click()
        self.page.locator('#charte-separateur').select_option('_')
        self.page.wait_for_function("() => document.querySelector('#charte-apercu')?.innerText.includes('XTST_RV_EAU_01_PM01')")
        self.assertIn('exports', self.page.locator('#charte-apercu').inner_text())
        self.page.locator('#brique-ok').click()
        self.page.wait_for_function("t => document.querySelector('.std-bibliotheque')?.innerText.includes(t)", arg=f'Charte fictive {n}')
        b = next(x for x in self.api('/api/standards')['bibliotheque']['charte'] if x['nom'] == f'Charte fictive {n}')
        self.assertEqual(b['exemple']['equipement'], 'XTST_RV_EAU_01_PM01')
        r = self.api('/api/standards/action', {'action': 'creer', 'nom': f'Client charte {n}',
                                               'choix': {'charte': b['ident'], 'adressage': 'adressage-defaut', 'outils': 'outils-topkapi'}})
        # Un ouvrage déjà équipé ne change pas de charte
        with self.assertRaisesRegex(RuntimeError, 'autre charte'):
            self.api('/api/standards/appliquer', {'ident': r['ident'], 'confirme': True})
        # Création selon ce standard : la fiche suit la charte (aperçu du repère), puis repères et noms
        self.api('/api/nouveau', {'mode': 'Neuf'})
        self.ouvrir('#/inventaire')
        self.page.locator('#standard-choix').wait_for()
        self.page.wait_for_function("() => document.querySelectorAll('#standard-choix option').length > 1")
        self.page.locator('#standard-choix').select_option(r['ident'])
        self.page.locator('#lieu').select_option('XTST')
        self.page.locator('#type_ouvrage').select_option('RV')
        num = f'{10 + n:02d}'          # plage propre à cet essai (fiches d'essai : 40+ et 70+)
        self.page.wait_for_load_state('networkidle')     # proposition de numéro en cours : attendre sa réponse
        for _ in range(3):                                # un rafraîchissement de la fiche peut survenir pendant la saisie
            self.page.locator('#numero_ouvrage').fill(num)
            self.page.locator('#numero_ouvrage').dispatch_event('input')
            try:
                self.page.wait_for_function("t => document.querySelector('#code-ouvrage-affiche')?.textContent === t",
                                            arg=f'XTST_RV_EAU_{num}', timeout=5000)
                break
            except Exception:
                self.page.wait_for_load_state('networkidle')
        else:
            etat = self.page.evaluate("() => ({code: document.querySelector('#code-ouvrage-affiche')?.textContent, "
                                      "std: document.querySelector('#standard-choix')?.value, lieu: document.querySelector('#lieu')?.value, "
                                      "type: document.querySelector('#code_ouvrage')?.value, num: document.querySelector('#numero_ouvrage')?.value})")
            self.fail(f'Code affiché inattendu : {etat}')
        self.api('/api/fiche-ouvrage', {'action': 'creer', 'standard': r['ident'], 'identification': {
            'lieu': 'XTST', 'code_ouvrage': 'RV', 'numero_ouvrage': num,
            'libelle': 'Ouvrage fictif charte client', 'automate': 'Sch - M340', 'revision': 'A'}})
        self.assertTrue(Path(self.api('/api/ouvrage')['chemin']).stem.startswith(f'XTST_RV_EAU_{num}'))
        ident = self.api('/api/equipement/ajouter', {'type': 'HV', 'numero': '01', 'se': '00'})['ident']
        self.api('/api/equipement/proposition', {'ident_eq': ident, 'decision': 'retenir'})
        noms = [v['nom'] for v in self.api('/api/variables')['lignes'] if v.get('ident_eq') == ident]
        self.assertTrue(noms and all(f'RV_EAU_{num}_HV01' in x for x in noms), noms[:3])
        with self.assertRaisesRegex(RuntimeError, 'autre charte'):
            self.api('/api/standards/appliquer', {'ident': 'standard-initial', 'confirme': True})

    def test_aller_retour_excel_des_equipements(self):
        """19/11 : export de la liste, modification dans « Excel », réimport comparé : modifié, nouveau, absent du
        fichier gardé ou supprimé sur choix ; rien n'est écrit avant la confirmation."""
        import tempfile
        from genvar import tableur
        from genvar.export_xlsx import ecrire_xlsx
        self.api('/api/equipement/ajouter', {'type': 'HV', 'numero': '02', 'se': '00', 'libelle': 'Vanne fictive 2'})
        self.ouvrir('#/inventaire')
        with self.page.expect_download() as telechargement:
            self.page.locator('#o-ruban #b-export-eq').click()
        dossier = Path(tempfile.mkdtemp())
        chemin = dossier / telechargement.value.suggested_filename
        telechargement.value.save_as(chemin)
        feuille = tableur.lire_classeur(chemin)['Équipements']
        lignes = [list(map(str, x)) for x in feuille[1:]]
        rep = self.api('/api/ouvrage')['identification']
        prefixe = rep['lieu'] + rep['code_ouvrage'] + rep['numero_ouvrage']
        hv1 = next(x for x in lignes if x[0] == prefixe + 'HV01')
        hv1[1] = 'Vanne fictive modifiée'
        lignes = [x for x in lignes if x[0] != prefixe + 'HV02']
        lignes.append([prefixe + 'HV03', 'Vanne fictive ajoutée', 'HV', '', '', '', ''])
        ecrire_xlsx(chemin, [('Équipements', feuille[0], lignes, [20] * len(feuille[0]))])
        avant = self.api('/api/ouvrage')['equipements']
        self.page.locator('#o-ruban #b-import').click()
        self.assertEqual(self.page.locator('#i-nature').input_value(), 'equipements_aller_retour')
        self.page.locator('#i-f').set_input_files(str(chemin))
        self.page.wait_for_function("() => document.querySelector('#i-res')?.innerText.includes('À modifier')")
        self.assertIn('Vanne fictive modifiée', self.page.locator('#i-res').inner_text())
        self.assertEqual(self.api('/api/ouvrage')['equipements'], avant)          # aperçu : rien d'écrit
        self.assertEqual(self.page.locator('#m-ok').inner_text(), 'Confirmer : 1 ajout(s), 1 modification(s)')
        self.page.locator('[data-obsolete]').select_option('supprimer')
        self.assertEqual(self.page.locator('#m-ok').inner_text(), 'Confirmer : 1 ajout(s), 1 modification(s), 1 suppression(s)')
        self.page.locator('#m-ok').click()
        self.page.wait_for_function("() => document.querySelector('#toasts')?.innerText.includes('Liste appliquée')")
        eqs = {e['pcf']: e for e in self.api('/api/ouvrage')['equipements']}
        self.assertEqual(set(eqs), {prefixe + 'HV01', prefixe + 'HV03'})
        self.assertEqual(eqs[prefixe + 'HV01']['libelle'], 'Vanne fictive modifiée')

    def test_modeles_de_livrables(self):
        """19/11, lot 1 : modèle à variables ajouté à la bibliothèque, état de ses variables, génération pour
        l'ouvrage dans Recette et livrables ; un modèle à corriger n'est jamais généré."""
        import tempfile
        self.ouvrir('#/standards')
        if self.page.locator('#ml-exemple').count():
            self.page.locator('#ml-exemple').click()
            self.page.wait_for_function("() => document.querySelector('.std-modeles')?.innerText.includes('Exemple - liste des variables')")
        fautif = Path(tempfile.mkdtemp()) / f'modele_fictif_{self.numero}.txt'
        fautif.write_text('<#OUVRAGE#>;<#VARIABLE_FICTIVE#>\n', encoding='utf-8')
        self.page.locator('#ml-importer').click()
        self.page.locator('#ml-nom').fill(f'Modèle fictif à corriger {self.numero}')
        self.page.locator('#ml-fichier').set_input_files(str(fautif))
        self.page.locator('#ml-ok').click()
        self.page.wait_for_function("t => document.querySelector('.std-modeles')?.innerText.includes(t)", arg=f'Modèle fictif à corriger {self.numero}')
        ligne = self.page.locator('[data-ml]', has_text=f'Modèle fictif à corriger {self.numero}')
        self.assertIn('à corriger', ligne.inner_text())
        ligne.click()
        self.page.wait_for_function("() => document.querySelector('.ml-apercu')?.textContent.includes('VARIABLE_FICTIVE')")
        self.assertIn("variable inconnue d'OGIAS", self.page.locator('.boite').inner_text())
        self.page.locator('.boite [data-fermer]').last.click()
        # Recette : l'exemple se génère pour l'ouvrage ; le modèle fautif est désactivé avec sa raison
        self.ouvrir('#/recette')
        self.page.wait_for_function("() => document.querySelectorAll('[data-modele-livrable]').length >= 2")
        fautif_btn = self.page.locator('#rc-modeles tr', has_text=f'Modèle fictif à corriger {self.numero}').locator('[data-modele-livrable]')
        self.assertTrue(fautif_btn.is_disabled())
        with self.page.expect_download() as telechargement:
            self.page.locator('#rc-modeles tr', has_text='Exemple - liste des variables').locator('[data-modele-livrable]').click()
        chemin = Path(tempfile.mkdtemp()) / telechargement.value.suggested_filename
        telechargement.value.save_as(chemin)
        lignes = chemin.read_text(encoding='utf-8').splitlines()
        self.assertEqual(lignes[0], 'Repère;Variable;Famille;Type;Adresse automate;Registre Modbus;Libellé')
        rep = self.api('/api/ouvrage')['identification']
        self.assertTrue(len(lignes) > 1 and all(x.startswith(rep['lieu'] + rep['code_ouvrage']) for x in lignes[1:]))

    def test_cahiers_d_essais(self):
        """19/11, lot 3 : cahier SAT édité, rempli, reporté avec aperçu ; avancement visible dans Recette."""
        import tempfile
        from genvar import tableur
        from genvar.export_xlsx import ecrire_xlsx
        self.ouvrir('#/recette')
        self.page.locator('[data-essai="SAT"]').wait_for()
        with self.page.expect_download() as telechargement:
            self.page.locator('[data-essai-cahier="SAT"]').click()
        chemin = Path(tempfile.mkdtemp()) / telechargement.value.suggested_filename
        telechargement.value.save_as(chemin)
        feuilles = tableur.lire_classeur(chemin)
        sortie = []
        for nom, lignes in feuilles.items():
            lignes = [list(map(str, x)) for x in lignes]
            if nom != 'Sommaire':
                lignes[1][8] = 'Conforme'
                if len(lignes) > 2:
                    lignes[2][8], lignes[2][9] = 'NOK', 'Libellé fictif inversé'
            sortie.append((nom, lignes[0], lignes[1:], [20] * len(lignes[0])))
        ecrire_xlsx(chemin, sortie)
        avant = self.api('/api/essais')['SAT']['compte']
        self.page.locator('[data-essai-reporter="SAT"]').click()
        self.page.locator('#essai-fichier').set_input_files(str(chemin))
        try:
            self.page.wait_for_function("() => document.querySelector('#essai-ok')?.textContent.startsWith('Confirmer : reporter')", timeout=8000)
        except Exception:
            self.fail(self.page.locator('#essai-apercu').inner_text())
        self.assertEqual(self.api('/api/essais')['SAT']['compte'], avant)          # aperçu : rien d'écrit
        self.page.locator('#essai-ok').click()
        try:
            self.page.wait_for_function("() => document.querySelector('#toasts')?.innerText.includes('reporté')", timeout=8000)
        except Exception:
            self.fail(self.page.locator('.boite').inner_text() if self.page.locator('.boite').count() else self.page.locator('#toasts').inner_text())
        compte = self.api('/api/essais')['SAT']['compte']
        self.assertEqual((compte['Conforme'], compte['Non conforme']), (1, 1))
        self.page.wait_for_function("() => document.querySelector('[data-essai=\"SAT\"]')?.innerText.includes('Libellé fictif inversé')")

    def test_attributs_d_equipement(self):
        """19/11, lot 4 : attribut créé dans la bibliothèque de l'atelier, saisi sur la fiche (contrôlé), signalé
        tant qu'il manque (obligatoire)."""
        code = f'MARQUE_T{self.numero}'
        self.ouvrir('#/standards')
        self.page.locator('#at-nouveau').click()
        self.page.locator('#at-code').fill(code)
        self.page.locator('#at-nom').fill(f'Marque fictive {self.numero}')
        self.page.locator('#at-type').select_option('liste')
        self.page.locator('#at-valeurs').fill('Marque A\nMarque B')
        self.page.locator('#at-types').fill('HV')
        self.page.locator('#at-oblig').check()
        self.page.locator('#at-ok').click()
        self.page.wait_for_function("c => document.querySelector('.std-attributs')?.innerText.includes(c)", arg=code)
        ident = next(e['ident'] for e in self.api('/api/ouvrage')['equipements'] if e['type'] == 'HV')
        self.assertTrue(any(f'Marque fictive {self.numero}' in m for m in self.api(f'/api/equipement?ident={ident}')['alertes']))
        self.ouvrir('#/inventaire')
        self.page.locator(f'.noeud[data-n="eq"][data-v="{ident}"]').first.click()
        champ = self.page.locator(f'[data-attribut="{code}"]')
        champ.wait_for()
        champ.select_option('Marque B')
        self.page.wait_for_function("() => document.querySelector('#toasts')?.innerText.includes('Attribut enregistré')")
        fiche = self.api(f'/api/equipement?ident={ident}')
        self.assertEqual(next(a['valeur'] for a in fiche['attributs'] if a['code'] == code), 'Marque B')
        self.assertFalse(any(f'Marque fictive {self.numero}' in m for m in fiche['alertes']))
        with self.assertRaisesRegex(RuntimeError, 'hors liste'):
            self.api('/api/equipement/attribut', {'ident_eq': ident, 'code': code, 'valeur': 'Marque Z'})

    def test_grille_d_ingenierie(self):
        """19/11, lot 5 : saisie dans la cellule, modification en masse avec confirmation ; type et modèle en lecture
        seule ; aucun équipement ne repasse « à valider »."""
        self.api('/api/equipement/ajouter', {'type': 'HV', 'numero': '02', 'se': '00', 'libelle': 'Vanne fictive 2'})
        self.ouvrir('#/dashboard')
        self.page.locator('#o-explorateur a[href="#/grille"]').click()
        self.titre("Grille d’ingénierie")
        self.page.locator('.grille-table tbody tr').first.wait_for()
        lignes = self.api('/api/grille')['lignes']
        premier = lignes[0]
        champ = self.page.locator(f'input[data-g-champ="libelle"][data-g-ident="{premier["ident"]}"]')
        champ.fill('Désignation fictive grille')
        champ.press('Enter')
        self.page.wait_for_function("i => document.querySelector(`input[data-g-champ='libelle'][data-g-ident='${i}']`)?.classList.contains('g-ok')", arg=premier['ident'])
        self.assertEqual(self.api('/api/grille')['lignes'][0]['libelle'], 'Désignation fictive grille')
        # Masse : local pour tous
        self.page.locator('#g-tout').check()
        self.page.locator('.grille-masse').wait_for()
        self.page.locator('#g-m-col').select_option('local')
        self.page.locator('#g-m-val').fill('Local fictif')
        self.page.locator('#g-m-ok').click()
        self.page.locator('.boite #m-ok').click()
        self.page.wait_for_function("() => document.querySelector('#toasts')?.innerText.includes('modifié')")
        apres = self.api('/api/grille')['lignes']
        self.assertTrue(all(l['local'] == 'Local fictif' for l in apres))
        self.assertEqual([l['valide'] for l in apres], [l['valide'] for l in lignes])
        self.assertEqual(self.page.locator('input[data-g-champ="modele"], select[data-g-champ="type"]').count(), 0)
        with self.assertRaisesRegex(RuntimeError, 'non modifiable'):
            self.api('/api/grille/appliquer', {'idents': [premier['ident']], 'champ': 'modele', 'valeur': 'X'})

    def test_generation_groupee(self):
        """19/11, lot 6 : un zip rangé par destination, journal des pièces produites et non produites avec motif ;
        les destinations décochées ne sont pas produites."""
        import csv
        import io
        import zipfile
        self.ouvrir('#/recette')
        bouton = self.page.locator('#o-ruban [aria-label="Livraison"] #r-groupe')
        bouton.wait_for()
        bouton.click()
        boite = self.page.locator('.boite')
        self.assertEqual(boite.locator('.gg-familles input:checked').count(), 6)
        boite.locator('.gg-familles input[value="automate"]').uncheck()
        try:
            with self.page.expect_download(timeout=15000) as telechargement:
                boite.locator('#m-ok').click()
        except Exception:
            self.fail(self.page.locator('#toasts').inner_text())
        self.assertTrue(telechargement.value.suggested_filename.endswith('_livrables.zip'))
        z = zipfile.ZipFile(telechargement.value.path())
        journal = list(csv.DictReader(io.StringIO(z.read('00_journal.csv').decode('utf-8-sig')), delimiter=';'))
        self.assertNotIn('Automate (Control Expert)', {j['Destination'] for j in journal})
        self.assertFalse(any(n.startswith('01_Automate/') for n in z.namelist()))
        for j in journal:
            self.assertTrue(j['Fichier'] in z.namelist() if j['État'] == 'produit' else j['Motif ou remarque'])
        self.page.wait_for_function("() => document.querySelector('#toasts')?.innerText.includes('non produite')")
        # Aucune destination : refus dans la boîte, rien n'est téléchargé
        bouton.click()
        self.page.locator('.boite .gg-familles input').evaluate_all("l => l.forEach(x => x.checked = false)")
        self.page.locator('.boite #m-ok').click()
        self.assertIn('au moins une destination', self.page.locator('.boite #m-err').inner_text())

    def test_declarer_la_gamme_d_un_automate_non_decrit(self):
        """22/11 : un automate d'un autre constructeur (fictif) mène de l'écran Matériel à la déclaration de sa gamme,
        préremplie ; une fois déclarée, l'écran Matériel la reconnaît et n'affiche que ses cartes."""
        automate = f'Xyz - Automate fictif {self.numero}'
        code = f'XYZ{self.numero}'
        self.api('/api/listes-ouvrage/action', {'action': 'ajouter', 'groupe': 'automates', 'code': automate, 'regie': 'Automate'})
        self.api('/api/nouveau', {'mode': 'Neuf'})
        self.api('/api/fiche-ouvrage', {'action': 'creer', 'identification': {
            'lieu': 'XTST', 'code_ouvrage': 'RV', 'numero_ouvrage': f'{40 + self.numero:02d}',
            'libelle': 'Automate fictif', 'automate': automate, 'revision': 'A'}})
        ident = self.api('/api/equipement/ajouter', {'type': 'HV', 'numero': '01', 'se': '00'})['ident']
        self.api('/api/equipement/proposition', {'ident_eq': ident, 'decision': 'retenir'})
        self.api('/api/equipement/valider', {'idents': [ident], 'valide': True})
        self.ouvrir('#/materiel')
        self.page.locator('#m-declarer-gamme').click()
        boite = self.page.locator('.boite')
        boite.locator('#gm-code').wait_for()
        self.assertIn('AUTOMATEFICTIF', boite.locator('#gm-motifs').input_value().replace(' ', ''))
        boite.locator('#gm-code').fill(code)
        boite.locator('#gm-motifs').fill(f'AUTOMATE FICTIF {self.numero}')
        boite.locator('#gm-nom').fill('Gamme fictive')
        boite.locator('#gm-constructeur').fill('Xyz')
        boite.locator('#gm-racks').fill('Châssis 10 ; 10')
        boite.locator('#gm-cartes').fill('XDI-16\tET\t16\t16 entrées\nXDO-16 ; ST ; 16\nXAI-8 ; EA ; 8\nXAO-4 ; SA ; 4')
        boite.locator('#gm-ok').click()
        ligne = self.page.locator('[data-gm]', has_text=code)
        ligne.wait_for()
        self.addCleanup(self.api, '/api/gammes-materiel/action', {'action': 'supprimer', 'ident': ligne.get_attribute('data-gm')})
        self.assertIn('ET 1', ligne.inner_text())
        self.ouvrir('#/materiel')
        self.page.wait_for_function("c => document.querySelector('.bandeau-materiel b')?.textContent === c", arg=code)
        self.assertEqual(self.page.locator('#m-declarer-gamme').count(), 0)
        cartes = self.api('/api/materiel')['cartes_catalogue']
        self.assertEqual({c['reference'] for c in cartes}, {'XDI-16', 'XDO-16', 'XAI-8', 'XAO-4'})

    def test_apprendre_un_format_d_export(self):
        """22/11 : un export FICTIF d'une liste d'E/S (forme octet.bit, guillemets, commentaires avant l'en-tête) est
        appris : colonnes proposées, aperçu sur l'ouvrage, enregistrement, puis qualification après essai réel."""
        import tempfile
        avant = self.projet.read_bytes()
        exemple = Path(tempfile.mkdtemp()) / 'liste_es_fictive.csv'
        exemple.write_text('// Export fictif\n"Name","Data Type","Logical Address","Comment"\n'
                           '"Marche","Bool","%I4.0","Marche"\n"Niveau","Int","%IW64","Niveau"\n', encoding='utf-8')
        nom = f'Liste E/S fictive {self.numero}'
        self.ouvrir('#/standards')
        self.page.locator('#fa-apprendre').click()
        boite = self.page.locator('.boite')
        boite.locator('#fa-fichier').set_input_files(str(exemple))
        boite.locator('#fa-analyser').click()
        boite.locator('.fa-colonnes').wait_for()
        self.assertEqual(boite.locator('[data-fa-col="2"]').input_value(), 'adresse')
        self.assertEqual(boite.locator('#fa-adr-ET').input_value(), '%I{OCTET}.{BIT}')
        self.assertEqual(boite.locator('#fa-type-EA').input_value(), 'Int')
        boite.locator('#fa-apercu').click()
        boite.locator('.fa-comparaison').wait_for()
        self.assertIn('"Name","Data Type","Logical Address","Comment"', boite.locator('.fa-comparaison').inner_text())
        boite.locator('#fa-logiciel').fill('Control Expert')
        boite.locator('#fa-nom').fill(nom)
        boite.locator('#fa-ok').click()
        ligne = self.page.locator('[data-fa]', has_text=nom)
        ligne.wait_for()
        self.addCleanup(self.api, '/api/formats-appris/action', {'action': 'supprimer', 'ident': ligne.get_attribute('data-fa')})
        self.assertIn('Non qualifié', ligne.inner_text())
        ligne.click()
        boite = self.page.locator('.boite')
        boite.locator('#faq-version').fill('V16')
        boite.locator('#faq-cr').fill('Fichier importé dans le logiciel, toutes les E/S créées.')
        boite.locator('#faq-ok').click()
        self.page.wait_for_function("t => [...document.querySelectorAll('[data-fa]')].some(r => r.innerText.includes(t) && r.innerText.includes('Qualifié'))", arg=nom)
        self.assertEqual(self.projet.read_bytes(), avant, "Apprendre un format ne modifie pas l'ouvrage")

    def test_apprendre_un_format_excel(self):
        """22/11 : un classeur FICTIF de la forme d'une table de variables TIA Portal est appris (feuille, gabarit)."""
        import tempfile
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'PLC Tags'
        ws.append(['Name', 'Path', 'Data Type', 'Logical Address', 'Comment', 'Hmi Visible'])
        ws.append(['Marche', 'Table fictive', 'Bool', '%I4.0', 'Marche', True])
        ws.append(['Niveau', 'Table fictive', 'Int', '%IW64', 'Niveau', True])
        wb.create_sheet('User Constants').append(['Name', 'Path', 'Data Type', 'Value'])
        exemple = Path(tempfile.mkdtemp()) / 'PLCTags_fictif.xlsx'
        wb.save(exemple)
        nom = f'Table TIA fictive {self.numero}'
        self.ouvrir('#/standards')
        self.page.locator('#fa-apprendre').click()
        boite = self.page.locator('.boite')
        boite.locator('#fa-fichier').set_input_files(str(exemple))
        boite.locator('#fa-analyser').click()
        boite.locator('#fa-feuille').wait_for()
        self.assertEqual(boite.locator('#fa-feuille').input_value(), 'PLC Tags')
        self.assertEqual(boite.locator('#fa-autres').input_value(), 'vider')
        self.assertEqual(boite.locator('[data-fa-col="3"]').input_value(), 'adresse')
        boite.locator('#fa-apercu').click()
        boite.locator('.fa-comparaison').wait_for()
        self.assertIn('Name | Path | Data Type | Logical Address', boite.locator('.fa-comparaison').inner_text())
        boite.locator('#fa-logiciel').fill('Sch - M340')
        boite.locator('#fa-nom').fill(nom)
        boite.locator('#fa-ok').click()
        ligne = self.page.locator('[data-fa]', has_text=nom)
        ligne.wait_for()
        self.addCleanup(self.api, '/api/formats-appris/action', {'action': 'supprimer', 'ident': ligne.get_attribute('data-fa')})
        ligne.click()
        self.assertIn('classeur Excel, feuille « PLC Tags »', self.page.locator('.boite').inner_text())

    def test_apprendre_un_format_de_supervision(self):
        """22/11, lot 2 : la nature « Télétransmission » adapte la fenêtre (familles TS…CP, jetons, alarme)."""
        import tempfile
        exemple = Path(tempfile.mkdtemp()) / 'supervision_fictive.csv'
        exemple.write_text('Tag;Address;DataType;Alarm\nP1;%MW100.0;BOOL;1\nNIV;%MW300;REAL;0\n', encoding='utf-8')
        self.ouvrir('#/standards')
        self.page.locator('#fa-apprendre').click()
        boite = self.page.locator('.boite')
        boite.locator('#fa-fichier').set_input_files(str(exemple))
        boite.locator('#fa-analyser').click()
        boite.locator('#fa-adr-ET').wait_for()
        boite.locator('#fa-nature').select_option('teletransmission')
        boite.locator('#fa-adr-TS').wait_for()
        self.assertEqual(boite.locator('#fa-adr-ET').count(), 0)
        self.assertEqual(boite.locator('#fa-adr-TS').input_value(), '%MW{MOT}.{BIT}')
        self.assertEqual(boite.locator('#fa-adr-TM').input_value(), '%MW{MOT}')
        self.assertEqual((boite.locator('#fa-alarme-oui').input_value(), boite.locator('#fa-alarme-non').input_value()), ('1', '0'))
        self.assertIn('{REGISTRE}', boite.inner_text())

    def test_modeles_par_logiciel_cible(self):
        """Lot 8 : un modèle déclaré pour un autre logiciel que celui de l'ouvrage est « non retenu », un type sans brique
        est signalé, et la destination se corrige depuis la fiche du modèle sans toucher à l'ouvrage."""
        import base64
        avant = self.projet.read_bytes()
        sup = self.api('/api/modeles-livrables')['logiciels_ouvrage']['supervision']
        self.assertTrue(sup, "L'ouvrage d'essai déclare une supervision")
        noms = {}
        for cle, logiciel in (('a', sup[0]), ('b', 'Logiciel fictif')):
            nom = f'Pompes {cle} {self.numero}'
            r = self.api('/api/modeles-livrables/action', {
                'action': 'importer', 'nom': nom, 'fichier': 'pompes.csv', 'destination': 'supervision', 'logiciel': logiciel,
                'contenu': base64.b64encode(b'<#DEBUT_EQUIPEMENTS_PM#><#REPERE#>\r\n<#FIN_EQUIPEMENTS_PM#>').decode()})
            noms[cle] = (nom, r['ident'])
            self.addCleanup(self.api, '/api/modeles-livrables/action', {'action': 'supprimer', 'ident': r['ident']})
        self.ouvrir('#/standards')
        bloc = self.page.locator('.std-modeles')
        bloc.locator('#ml-manques').wait_for()
        self.assertIn('HV', bloc.locator('#ml-manques').inner_text())
        ligne_a = self.page.locator('[data-ml]', has_text=noms['a'][0])
        ligne_b = self.page.locator('[data-ml]', has_text=noms['b'][0])
        self.assertIn(f'Supervision · {sup[0]}', ligne_a.inner_text())
        self.assertIn('PM', ligne_a.inner_text())
        self.assertIn('Prêt', ligne_a.inner_text())
        self.assertIn('Non retenu', ligne_b.inner_text())
        self.assertIn('Logiciel fictif', bloc.locator('[data-o-cle="modeles-couverture"]').inner_text())
        ligne_b.click()
        boite = self.page.locator('.boite')
        self.assertIn(f"l'ouvrage utilise {sup[0]}", boite.inner_text())
        boite.locator('#mlc-logiciel').fill(sup[0])
        boite.locator('#mlc-ok').click()
        self.page.wait_for_function("t => [...document.querySelectorAll('[data-ml]')].some(r => r.innerText.includes(t) && r.innerText.includes('Prêt'))",
                                    arg=noms['b'][0])
        self.assertEqual(self.projet.read_bytes(), avant, "Les modèles de l'atelier ne modifient pas l'ouvrage")

    def test_assistant_modele_depuis_export(self):
        """19/11, lot 7 : un export FICTIF d'un équipement devient un modèle ; une valeur décochée reste écrite ;
        le contrôle de reproduction est affiché ; le modèle rejoint la bibliothèque prêt à générer."""
        import tempfile
        ouvrage = self.api('/api/ouvrage')
        eq = ouvrage['equipements'][0]
        noms = [v['nom'] for v in self.api('/api/variables')['lignes'] if v['repere'].endswith(eq['pcf'][-4:])][:3]
        self.assertTrue(noms)
        export = Path(tempfile.mkdtemp()) / 'export_fictif_vanne.csv'
        export.write_text('Nom;Objet;Type\n' + ''.join(f'{n};{eq["pcf"]};BOOL\n' for n in noms), encoding='utf-8')
        self.ouvrir('#/standards')
        self.page.locator('#ml-assistant').click()
        boite = self.page.locator('.boite')
        boite.locator('#as-fichier').set_input_files(str(export))
        boite.locator('#as-analyser').click()
        boite.locator('.as-verif').wait_for()
        self.assertIn('<#DEBUT_EQUIPEMENTS_HV#>', boite.locator('.ml-apercu').last.inner_text())
        self.assertIn('<#NOM#>;<#REPERE#>', boite.locator('.ml-apercu').last.inner_text())
        boite.locator('[data-as-var="REPERE"]').uncheck()
        self.page.wait_for_function("() => document.querySelector('.as-props tr.refusee')")
        self.assertIn(f'<#NOM#>;{eq["pcf"]};', boite.locator('.ml-apercu').last.inner_text())
        boite.locator('[data-as-var="REPERE"]').check()
        self.page.wait_for_function("() => !document.querySelector('.as-props tr.refusee')")
        boite.locator('#as-nom').fill(f'Vanne - export fictif {self.numero}')
        boite.locator('#as-ok').click()
        self.page.wait_for_function("t => document.querySelector('.std-modeles')?.innerText.includes(t)", arg=f'Vanne - export fictif {self.numero}')
        ligne = self.page.locator('[data-ml]', has_text=f'Vanne - export fictif {self.numero}')
        self.assertIn('Prêt', ligne.inner_text())
