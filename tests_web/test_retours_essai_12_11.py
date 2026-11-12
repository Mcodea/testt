"""Écrans des retours d'essai du 12/11/2026 : points bloquants, thème, dossier de recette, répartition, îlot STB."""
from support import ServeurNavigateur


class TestRetoursEssai(ServeurNavigateur):
    def setUp(self):
        type(self).numero += 1
        self.api('/api/nouveau', {'mode': 'Neuf'})
        if not any(x['code'] == 'XTST' for x in self.api('/api/listes-ouvrage')['lieux']):
            self.api('/api/listes-ouvrage/action', {'action': 'ajouter', 'groupe': 'lieux',
                                                   'code': 'XTST', 'libelle': 'Lieu fictif'})
        self.api('/api/fiche-ouvrage', {'action': 'creer', 'identification': {
            'lieu': 'XTST', 'code_ouvrage': 'RV', 'numero_ouvrage': f'{40 + self.numero:02d}',
            'libelle': 'Essai du 12/11', 'automate': 'M340', 'revision': 'A'}})
        self.context = self.browser.new_context(viewport={'width': 1600, 'height': 1000})
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.erreurs = []
        self.page.on('pageerror', lambda e: self.erreurs.append(str(e)))

    def tearDown(self):
        self.assertEqual(self.erreurs, [])

    def test_points_bloquants_listes_et_cliquables(self):
        self.api('/api/equipement/ajouter', {'type': 'MV', 'numero': '01', 'se': '00'})
        self.page.goto(self.url + '#/inventaire', wait_until='networkidle')
        panneau = self.page.locator('.parcours-points .pp-bloquants')
        panneau.wait_for()
        self.assertIn("Pour passer à l'étape suivante", panneau.inner_text())
        self.assertIn('MV01', panneau.inner_text())
        self.assertGreaterEqual(panneau.locator('button[data-pp-vue]').count(), 1)

    def test_bouton_de_theme_soleil_lune(self):
        self.page.goto(self.url + '#/ouvrages', wait_until='networkidle')
        bouton = self.page.locator('#v31-settings')
        self.assertIn('Thème', bouton.get_attribute('title'))
        avant = bouton.locator('svg').get_attribute('data-lucide')
        self.assertIn(avant, ('sun', 'moon'))
        bouton.click()
        self.assertNotEqual(bouton.locator('svg').get_attribute('data-lucide'), avant)

    def test_dossier_de_recette_telechargeable(self):
        self.page.goto(self.url + '#/recette', wait_until='networkidle')
        self.page.locator('#r-dossier').click()
        with self.page.expect_download() as dl:
            self.page.locator('#m-ok').click()
        self.assertTrue(dl.value.suggested_filename.endswith('_dossier_recette.zip'))

    def test_groupe_de_secours_propose_puis_confirme(self):
        for n in ('01', '02'):
            self.equipement_valide(n)
        self.page.goto(self.url + '#/materiel', wait_until='networkidle')
        bouton = self.page.locator('[data-rp-confirmer]')
        bouton.first.wait_for()
        bouton.first.click()
        self.page.locator('[data-rp-retirer]').first.wait_for()
        self.assertEqual(len(self.api('/api/materiel')['repartition']['groupes_secours']), 1)

    def equipement_valide(self, numero):
        i = self.api('/api/equipement/ajouter', {'type': 'MV', 'numero': numero, 'se': '00'})['ident']
        self.api('/api/equipement/proposition', {'ident_eq': i, 'decision': 'retenir'})
        self.api('/api/equipement/valider', {'idents': [i], 'valide': True})
        return i

    def test_ilot_stb_numerote_comme_advantys(self):
        if 'STBNIP2212' not in self.api('/api/listes-ouvrage')['automates']:
            self.api('/api/listes-ouvrage/action', {'action': 'ajouter', 'groupe': 'automates',
                                                   'code': 'STBNIP2212', 'libelle': 'Îlot Advantys STB'})
        self.api('/api/nouveau', {'mode': 'Neuf'})
        self.api('/api/fiche-ouvrage', {'action': 'creer', 'identification': {
            'lieu': 'XTST', 'code_ouvrage': 'RV', 'numero_ouvrage': f'{70 + self.numero:02d}',
            'libelle': 'Îlot fictif', 'automate': 'STBNIP2212', 'revision': 'A'}})
        self.equipement_valide('01')
        pts = self.api('/api/es')['points']
        self.api('/api/es/valider', {'niveau': 'contenu',
                                     'paires': [{'ident_eq': p['ident_eq'], 'cle': p['cle']} for p in pts]})
        mat = self.api('/api/materiel')
        self.assertEqual(mat['plateforme'], 'STB')
        self.assertEqual(mat['proposition']['racks'][0]['composition'][0]['noeud'], 127)
        self.page.goto(self.url + '#/materiel', wait_until='networkidle')
        self.page.locator('text=Îlot 0').first.wait_for()
        texte = self.page.locator('#vue').inner_text()
        self.assertIn('1/127', texte)
        self.assertIn('2/-', texte)
        self.assertIn('STB XMP 1100', texte)


class TestCommunicationCasesACocher(ServeurNavigateur):
    def test_protocoles_choisis_sans_fenetre(self):
        self.api('/api/nouveau', {'mode': 'Neuf'})
        protocoles = self.api('/api/listes-ouvrage')['protocoles']
        if not protocoles:
            self.api('/api/listes-ouvrage/action', {'action': 'ajouter', 'groupe': 'protocoles',
                                                   'code': 'Modbus TCP', 'libelle': ''})
            protocoles = self.api('/api/listes-ouvrage')['protocoles']
        context = self.browser.new_context(viewport={'width': 1500, 'height': 1000})
        self.addCleanup(context.close)
        page = context.new_page()
        erreurs = []
        page.on('pageerror', lambda e: erreurs.append(str(e)))
        page.goto(self.url + '#/inventaire', wait_until='networkidle')
        page.locator('summary:has-text("Paramètres du projet")').click()
        bouton = page.locator('#communication-choix')
        bouton.wait_for()
        bouton.click()
        liste = page.locator('.deroulant-protocoles')
        liste.wait_for()
        self.assertEqual(page.locator('#modale:not([hidden])').count(), 0)     # aucune fenêtre
        liste.locator('input').first.check()
        self.assertIn(protocoles[0], bouton.get_attribute('data-valeur'))
        page.mouse.click(5, 5)
        self.assertEqual(page.locator('.deroulant-protocoles').count(), 0)
        self.assertEqual(erreurs, [])


class TestEtatVide(ServeurNavigateur):
    def test_premier_equipement_propose_d_emblee(self):
        self.api('/api/nouveau', {'mode': 'Neuf'})
        if not any(x['code'] == 'XTST' for x in self.api('/api/listes-ouvrage')['lieux']):
            self.api('/api/listes-ouvrage/action', {'action': 'ajouter', 'groupe': 'lieux',
                                                   'code': 'XTST', 'libelle': 'Lieu fictif'})
        self.api('/api/fiche-ouvrage', {'action': 'creer', 'identification': {
            'lieu': 'XTST', 'code_ouvrage': 'RV', 'numero_ouvrage': '88', 'libelle': 'Vide',
            'automate': 'M340', 'revision': 'A'}})
        context = self.browser.new_context(viewport={'width': 1500, 'height': 1000})
        self.addCleanup(context.close)
        page = context.new_page()
        erreurs = []
        page.on('pageerror', lambda e: erreurs.append(str(e)))
        page.goto(self.url + '#/inventaire', wait_until='networkidle')
        bouton = page.locator('#vide-ajout-eq')
        bouton.wait_for()
        bouton.click()
        page.locator('#modale:not([hidden])').wait_for()
        self.assertEqual(erreurs, [])


class TestVoiesCarte(ServeurNavigateur):
    def test_deplacer_une_e_s_vers_une_voie_libre(self):
        self.api('/api/nouveau', {'mode': 'Neuf'})
        if not any(x['code'] == 'XTST' for x in self.api('/api/listes-ouvrage')['lieux']):
            self.api('/api/listes-ouvrage/action', {'action': 'ajouter', 'groupe': 'lieux',
                                                   'code': 'XTST', 'libelle': 'Lieu fictif'})
        self.api('/api/fiche-ouvrage', {'action': 'creer', 'identification': {
            'lieu': 'XTST', 'code_ouvrage': 'RV', 'numero_ouvrage': '77', 'libelle': 'Voies',
            'automate': 'M340', 'revision': 'A'}})
        i = self.api('/api/equipement/ajouter', {'type': 'MV', 'numero': '01', 'se': '00'})['ident']
        self.api('/api/equipement/proposition', {'ident_eq': i, 'decision': 'retenir'})
        self.api('/api/equipement/valider', {'idents': [i], 'valide': True})
        pts = self.api('/api/es')['points']
        self.api('/api/es/valider', {'niveau': 'contenu',
                                     'paires': [{'ident_eq': p['ident_eq'], 'cle': p['cle']} for p in pts]})
        self.api('/api/materiel/action', {'action': 'appliquer'})
        self.api('/api/modules', {'action': 'implanter'})
        es = self.api('/api/es')
        place = next(p for p in es['points'] if p['adresse'])
        carte = next(m for m in es['modules'] if m['nature'] == place['point'])
        context = self.browser.new_context(viewport={'width': 1500, 'height': 1000})
        self.addCleanup(context.close)
        page = context.new_page()
        erreurs = []
        page.on('pageerror', lambda e: erreurs.append(str(e)))
        page.goto(self.url + '#/materiel', wait_until='networkidle')
        page.locator(f'[data-carte="{carte["module"]}"]').first.click()
        page.locator('.voies-carte').wait_for()
        choix = page.locator(f'.cv-deplacer[data-cle="{place["cle"]}"]')
        cible = choix.locator('option').nth(1).get_attribute('value')
        choix.select_option(cible)
        page.wait_for_function("t => document.querySelector('#toasts').innerText.includes(t)", arg='à valider')
        apres = next(p for p in self.api('/api/es')['points'] if p['cle'] == place['cle'] and p['ident_eq'] == place['ident_eq'])
        module, voie = cible.split('|')
        self.assertEqual((apres['module'], str(apres['voie'])), (module, voie))
        self.assertFalse(apres['validee'])
        self.assertEqual(erreurs, [])


class TestMaterielComplet(ServeurNavigateur):
    def test_composition_rack_et_nomenclature(self):
        self.api('/api/nouveau', {'mode': 'Neuf'})
        if not any(x['code'] == 'XTST' for x in self.api('/api/listes-ouvrage')['lieux']):
            self.api('/api/listes-ouvrage/action', {'action': 'ajouter', 'groupe': 'lieux',
                                                   'code': 'XTST', 'libelle': 'Lieu fictif'})
        self.api('/api/fiche-ouvrage', {'action': 'creer', 'identification': {
            'lieu': 'XTST', 'code_ouvrage': 'RV', 'numero_ouvrage': '66', 'libelle': 'Matériel',
            'automate': 'M340', 'revision': 'A'}})
        i = self.api('/api/equipement/ajouter', {'type': 'PM', 'numero': '01', 'se': '00'})['ident']
        self.api('/api/equipement/proposition', {'ident_eq': i, 'decision': 'retenir'})
        self.api('/api/equipement/valider', {'idents': [i], 'valide': True})
        pts = self.api('/api/es')['points']
        self.api('/api/es/valider', {'niveau': 'contenu',
                                     'paires': [{'ident_eq': p['ident_eq'], 'cle': p['cle']} for p in pts]})
        context = self.browser.new_context(viewport={'width': 1500, 'height': 1000})
        self.addCleanup(context.close)
        page = context.new_page()
        erreurs = []
        page.on('pageerror', lambda e: erreurs.append(str(e)))
        page.goto(self.url + '#/materiel', wait_until='networkidle')
        page.locator('[data-cfg="alimentation"]').select_option('BMX CPS 3500')
        page.wait_for_function("() => document.querySelector('[data-cfg=\"alimentation\"]')?.value === 'BMX CPS 3500'")
        page.locator('[data-cfg="processeur"]').select_option('BMX P34 2020')
        page.wait_for_function("() => document.querySelector('[data-cfg=\"processeur\"]')?.value === 'BMX P34 2020'")
        self.api('/api/materiel/action', {'action': 'appliquer'})
        page.reload(wait_until='networkidle')
        page.locator('.emplacement.alim').first.wait_for()
        self.assertIn('BMX CPS 3500', page.locator('.emplacement.alim').first.inner_text())
        self.assertIn('BMX P34 2020', page.locator('.emplacement.cpu').first.inner_text())
        self.assertIn('Nomenclature de commande', page.locator('#vue').inner_text())
        with page.expect_download() as dl:
            page.locator('#m-nomenclature').click()
        self.assertTrue(dl.value.suggested_filename.endswith('_nomenclature_materiel.xlsx'))
        self.assertEqual(erreurs, [])
