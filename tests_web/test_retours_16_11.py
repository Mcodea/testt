"""Retours de l'utilisateur du 16/11/2026 : en-tête de l'arborescence, rack équipé emplacement par emplacement,
sources d'acquisition classées."""
from support import ServeurNavigateur


class TestRetours1611(ServeurNavigateur):
    def setUp(self):
        type(self).numero += 1
        self.api('/api/nouveau', {'mode': 'Neuf'})
        if not any(x['code'] == 'XTST' for x in self.api('/api/listes-ouvrage')['lieux']):
            self.api('/api/listes-ouvrage/action', {'action': 'ajouter', 'groupe': 'lieux',
                                                   'code': 'XTST', 'libelle': 'Lieu fictif'})
        self.api('/api/fiche-ouvrage', {'action': 'creer', 'identification': {
            'lieu': 'XTST', 'code_ouvrage': 'RV', 'numero_ouvrage': f'{20 + self.numero:02d}',
            'libelle': 'Essai du 16/11', 'automate': 'Sch - M340', 'revision': 'A'}})
        i = self.api('/api/equipement/ajouter', {'type': 'PM', 'numero': '01', 'se': '00'})['ident']
        self.api('/api/equipement/proposition', {'ident_eq': i, 'decision': 'retenir'})
        self.api('/api/equipement/valider', {'idents': [i], 'valide': True})
        pts = self.api('/api/es')['points']
        self.api('/api/es/valider', {'niveau': 'contenu',
                                     'paires': [{'ident_eq': p['ident_eq'], 'cle': p['cle']} for p in pts]})
        self.api('/api/materiel/action', {'action': 'appliquer'})
        self.context = self.browser.new_context(viewport={'width': 1366, 'height': 768})
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.erreurs = []
        self.page.on('pageerror', lambda e: self.erreurs.append(str(e)))

    def tearDown(self):
        self.assertEqual(self.erreurs, [])

    def test_en_tete_de_l_arborescence_compact_et_lisible(self):
        self.page.goto(self.url + '#/inventaire', wait_until='networkidle')
        self.page.locator('#vue > aside .aside-btns').wait_for()
        hauts = {round(self.page.locator(s).bounding_box()['y']) for s in ('#b-eq', '#b-uf', '#b-import')}
        self.assertEqual(len(hauts), 1, 'Les trois commandes sur une seule ligne')
        for s in ('#b-eq', '#b-uf', '#b-import'):
            self.assertLessEqual(self.page.locator(s).evaluate('e => e.scrollWidth - e.clientWidth'), 1, s)
        self.assertIn("Arborescence", self.page.locator('#vue > aside h2').inner_text())

    def test_emplacement_libre_equipe_d_une_carte_puis_d_un_module_de_communication(self):
        self.page.goto(self.url + '#/materiel', wait_until='networkidle')
        libres = self.page.locator('.emplacement.libre[data-emplacement]')
        libres.first.wait_for()
        cle = libres.first.get_attribute('data-emplacement')
        libres.first.click()
        self.page.locator('#e-ref').select_option('BMX DRA 1605')
        self.page.locator('#e-ok').click()
        self.page.wait_for_function('c => !!document.querySelector(`[data-carte="${c}"]`)', arg=cle)
        module = next(m for m in self.api('/api/es')['modules'] if m['module'] == cle)
        self.assertEqual((module['reference'], module['nature'], module['voies']), ('BMX DRA 1605', 'ST', 16))
        # Un autre emplacement libre reçoit un module de communication
        cle2 = self.page.locator('.emplacement.libre[data-emplacement]').first.get_attribute('data-emplacement')
        self.page.locator('.emplacement.libre[data-emplacement]').first.click()
        self.page.locator('input[name="e-type"][value="com"]').check()
        self.page.locator('#e-com-ref').select_option('BMX NOM 0200')
        self.page.locator('#e-ok').click()
        self.page.wait_for_function('c => document.querySelector(`[data-emplacement="${c}"]`)?.dataset.role === "communication"',
                                    arg=cle2)
        # L'emplacement de communication refuse une carte (réservé) et peut être libéré
        rack, pos = cle2.split('.')
        with self.assertRaisesRegex(RuntimeError, 'réservé'):
            self.api('/api/modules', {'action': 'ajouter', 'rack': rack, 'position': pos, 'nature': 'ET',
                                      'voies': 16, 'reference': 'BMX DDI 1602'})
        self.page.locator(f'[data-emplacement="{cle2}"]').click()
        self.page.locator('#e-liberer').click()
        self.page.wait_for_function('c => document.querySelector(`[data-emplacement="${c}"]`)?.dataset.role === "libre"', arg=cle2)

    def test_emplacements_reserves_proposent_seulement_leur_module(self):
        self.page.goto(self.url + '#/materiel', wait_until='networkidle')
        self.page.locator('.emplacement.alim[data-emplacement]').click()
        options = self.page.locator('#e-ref option').all_text_contents()
        self.assertTrue(all(o.startswith('BMX CPS') or o.startswith('—') for o in options))
        self.page.locator('#e-ref').select_option('BMX CPS 2010')
        self.page.locator('#e-ok').click()
        self.page.wait_for_function('() => document.querySelector(".emplacement.alim b")?.textContent === "BMX CPS 2010"')
        self.page.locator('.emplacement.cpu[data-emplacement]').first.click()
        options = self.page.locator('#e-ref option').all_text_contents()
        self.assertTrue(all(o.startswith('BMX P34') or o.startswith('—') for o in options))
        self.page.locator('#modale [data-fermer]').click()

    def test_source_d_acquisition_classee(self):
        self.page.goto(self.url + '#/inventaire', wait_until='networkidle')
        self.page.locator('#fiche-ouvrage > summary h2').click()
        groupes = self.page.locator('#automate optgroup').evaluate_all('g => g.map(x => x.label)')
        self.assertEqual(groupes[:3], ['Automate', 'Télégestion', 'E/S déportées'])
        self.assertEqual(self.page.locator('label[for="automate"]').inner_text(), "Source d'acquisition")
        self.assertEqual(self.page.locator('#automate').input_value(), 'Sch - M340')
