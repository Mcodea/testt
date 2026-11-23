"""Échelle analogique : choix du type de signal, courant (4-20 mA) ou tension (0-10 V), dans le panneau de la liste des E/S."""
from support import ServeurNavigateur


class TestSignalTensionUI(ServeurNavigateur):
    numero = 0

    def setUp(self):
        type(self).numero += 1
        self.api('/api/nouveau', {'mode': 'Neuf'})
        if not any(x['code'] == 'XTST' for x in self.api('/api/listes-ouvrage')['lieux']):
            self.api('/api/listes-ouvrage/action', {'action': 'ajouter', 'groupe': 'lieux', 'code': 'XTST', 'libelle': 'Lieu fictif'})
        self.api('/api/fiche-ouvrage', {'action': 'creer', 'identification': {
            'lieu': 'XTST', 'code_ouvrage': 'RV', 'numero_ouvrage': f'{60 + self.numero:02d}',
            'libelle': 'Essai tension', 'automate': 'Sch - M340', 'revision': 'A'}})
        i = self.api('/api/equipement/ajouter', {'type': 'TT', 'numero': '01', 'se': '00'})['ident']
        self.api('/api/equipement/proposition', {'ident_eq': i, 'decision': 'retenir'})
        self.api('/api/equipement/configurer', {'action': 'analogique', 'ident_eq': i, 'cle': 'ES_TMP', 'params': {
            'signal_min': 4, 'signal_max': 20, 'phys_min': 0, 'phys_max': 50, 'unite': '°C'}})
        self.api('/api/equipement/valider', {'idents': [i], 'valide': True})
        self.context = self.browser.new_context(viewport={'width': 1366, 'height': 768})
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.erreurs = []
        self.page.on('pageerror', lambda e: self.erreurs.append(str(e)))

    def tearDown(self):
        self.assertEqual(self.erreurs, [])

    def test_type_de_signal_courant_ou_tension(self):
        self.page.goto(self.url + '#/es', wait_until='networkidle')
        self.page.locator('tr.es-ligne:has(.tag.p-EA)').first.click()
        type_signal = self.page.locator('#es-signal-type')
        type_signal.wait_for()
        self.assertEqual(type_signal.input_value(), 'courant')
        self.assertEqual(self.page.locator('#es-signal-min').get_attribute('placeholder'), '4')
        type_signal.select_option('tension')
        self.assertEqual(self.page.locator('#es-signal-min').get_attribute('placeholder'), '0')
        self.assertEqual(self.page.locator('#es-signal-max').get_attribute('placeholder'), '10')
        self.assertEqual(self.page.locator('.es-unite-signal').first.inner_text(), 'V')
        for champ, valeur in (('#es-signal-min', '0'), ('#es-signal-max', '10'), ('#es-phys-min', '0'),
                              ('#es-phys-max', '50'), ('#es-unite', '°C')):
            self.page.locator(champ).fill(valeur)
        self.page.locator('#es-enregistrer').click()
        self.page.wait_for_function("document.querySelector('#es-erreur') && document.querySelector('#es-erreur').textContent === ''")
        points = [p for p in self.api('/api/es')['points'] if p['point'] == 'EA']
        self.assertEqual(points[0]['analogique']['signal_type'], 'tension')
        self.assertEqual((points[0]['analogique']['signal_min'], points[0]['analogique']['signal_max']), (0.0, 10.0))
