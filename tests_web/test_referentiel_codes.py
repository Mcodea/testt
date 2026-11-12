"""Lecture, édition et protection de la révision publiée via le navigateur réel."""
from pathlib import Path
import os
import unittest

from support import ServeurNavigateur


class TestReferentielCodes(ServeurNavigateur):
    def setUp(self):
        cycle = self.api('/api/referentiel/cycle')
        if cycle['brouillon']:
            self.api('/api/referentiel/cycle/action', {'action': 'abandonner'})
        self.context = self.browser.new_context(viewport={'width': 1366, 'height': 768})
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.goto(self.url + '#/referentiel', wait_until='networkidle')
        self.page.wait_for_selector('[data-ref-objet="lexique"]')

    def tearDown(self):
        self.assertEqual(self.errors, [])

    def vue(self, objet, brouillon=False):
        if brouillon:
            self.page.locator('#rf-creer').click()
            self.page.wait_for_selector('#rf-voir-pub')
        self.page.locator(f'[data-ref-objet="{objet}"]').click()
        self.page.wait_for_selector('#ref-codes-query')

    def test_consultation_clavier_sans_ecriture_et_capture(self):
        avant = self.api('/api/referentiel/cycle')['empreinte']
        for objet in ('lexique', 'dictionnaire_es', 'correspondances'):
            with self.subTest(objet=objet):
                self.vue(objet)
                self.assertTrue(self.page.locator('#ref-codes-add').is_disabled())
                ligne = self.page.locator('[data-ref-code]').first
                ligne.focus()
                ligne.press('Enter')
                self.assertTrue(self.page.locator('#ref-code-close').is_visible())
                self.assertEqual(self.page.locator('#ref-code-save').count(), 0)
                self.page.locator('#ref-code-close').press('Escape')
                self.assertEqual(self.page.locator('#ref-code-close').count(), 0)
                self.assertTrue(self.page.locator('[data-ref-code]').first.evaluate('el => el === document.activeElement'))
                self.page.locator('[data-ref-code]').first.press('Space')
                self.assertTrue(self.page.locator('#ref-code-close').is_visible())
                footer = self.page.locator('.ref-codes-table footer').bounding_box()
                self.assertLessEqual(footer['y'] + footer['height'], 768)
                captures = Path(os.environ.get('OGIAS_CAPTURE_DIR', 'artifacts/ci/captures'))
                captures.mkdir(parents=True, exist_ok=True)
                self.page.screenshot(path=str(captures / f'referentiel-{objet}-1366.png'), full_page=True)
                self.page.locator('#ref-code-close').click()
        self.assertIsNone(self.api('/api/referentiel/cycle')['brouillon'])
        self.assertEqual(self.api('/api/referentiel/cycle')['empreinte'], avant)

    def test_recherche_pagination_et_absence_de_debordement(self):
        self.vue('lexique')
        premier = self.page.locator('[data-ref-code]').first.get_attribute('data-ref-code')
        self.page.locator('#ref-codes-next').click()
        self.assertNotEqual(self.page.locator('[data-ref-code]').first.get_attribute('data-ref-code'), premier)
        self.page.locator('#ref-codes-query').fill('aucune-correspondance-fictive')
        self.assertEqual(self.page.locator('[data-ref-code]').count(), 0)
        self.page.locator('#ref-codes-query').fill('verrouill')
        self.assertEqual(self.page.locator('[data-ref-code]').count(), 2)  # verrouillage et verrouille
        for width, height in ((1366, 768), (1920, 1080), (2560, 1440)):
            with self.subTest(width=width):
                self.page.set_viewport_size({'width': width, 'height': height})
                self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))

    def test_lexique_edite_dans_le_brouillon_et_publication_protegee(self):
        avant = self.api('/api/referentiel/cycle')['empreinte']
        self.vue('lexique', brouillon=True)
        ligne = self.page.locator('[data-ref-code]').first
        cle = ligne.get_attribute('data-ref-code')
        ligne.click()
        self.page.locator('#ref-code-abreviation').fill('FICTIF')
        self.page.locator('#ref-code-save').click()
        self.page.wait_for_selector('.ref-code-detail', state='detached')
        publie = self.api('/api/referentiel/vue?source=publie')['lexique']
        brouillon = self.api('/api/referentiel/vue?source=brouillon')['lexique']
        self.assertEqual(next(r for r in brouillon if r['cle'] == cle)['abreviation'], 'FICTIF')
        self.assertNotEqual(next(r for r in publie if r['cle'] == cle)['abreviation'], 'FICTIF')
        self.assertEqual(self.api('/api/referentiel/cycle')['empreinte'], avant)

    def test_code_invalide_refuse_avant_ecriture_et_ajout_valide(self):
        self.vue('dictionnaire_es', brouillon=True)
        nombre = len(self.api('/api/referentiel/vue?source=brouillon')['dictionnaire_es'])
        self.page.locator('#ref-codes-add').click()
        self.page.locator('#ref-code-code').fill('x')
        self.page.locator('#ref-code-libelle').fill('Signal fictif')
        self.page.locator('#ref-code-save').click()
        self.assertIn('2 à 9', self.page.locator('#ref-code-error').inner_text())
        self.assertEqual(len(self.api('/api/referentiel/vue?source=brouillon')['dictionnaire_es']), nombre)
        self.page.locator('#ref-code-code').fill('FICTIF')
        self.page.locator('#ref-code-save').click()
        self.page.wait_for_selector('.ref-code-detail', state='detached')
        self.assertEqual(len(self.api('/api/referentiel/vue?source=brouillon')['dictionnaire_es']), nombre+1)
        self.assertEqual(len(self.api('/api/referentiel/vue?source=publie')['dictionnaire_es']), nombre)

    def test_suppression_annulable_et_confirmee_seulement_en_brouillon(self):
        self.vue('lexique', brouillon=True)
        ligne = self.page.locator('[data-ref-code]').first
        cle = ligne.get_attribute('data-ref-code')
        ligne.click()
        self.page.locator('#ref-code-delete').click()
        self.page.get_by_role('button', name='Annuler', exact=True).press('Escape')
        self.assertTrue(self.page.locator('#ref-code-close').is_visible())
        self.assertTrue(any(r['cle'] == cle for r in self.api('/api/referentiel/vue?source=brouillon')['lexique']))
        self.page.locator('#ref-code-delete').click()
        self.page.locator('#m-ok').click()
        self.page.wait_for_selector('.ref-code-detail', state='detached')
        self.assertFalse(any(r['cle'] == cle for r in self.api('/api/referentiel/vue?source=brouillon')['lexique']))
        self.assertTrue(any(r['cle'] == cle for r in self.api('/api/referentiel/vue?source=publie')['lexique']))

    def test_texte_saisi_echappe_dans_la_table_et_le_detail(self):
        self.vue('lexique', brouillon=True)
        texte = 'Essai fictif <img src=x onerror="window.__ogias_injected__=true">'
        self.api('/api/referentiel/cycle/action', {'action': 'editer', 'modification': 'ajouter_lexique',
                                                 'champs': {'mot': texte, 'abreviation': 'FICTIF'}})
        self.page.reload(wait_until='networkidle')
        self.page.locator('[data-ref-objet="lexique"]').click()
        self.page.locator('#ref-codes-query').fill('Essai fictif')
        self.assertEqual(self.page.locator('[data-ref-code]').count(), 1)
        self.assertIn(texte, self.page.locator('[data-ref-code]').inner_text())
        self.page.locator('[data-ref-code]').click()
        self.assertEqual(self.page.locator('#ref-code-mot').input_value(), texte)
        self.assertEqual(self.page.locator('.ref-codes-layout img').count(), 0)
        self.assertFalse(self.page.evaluate('Boolean(window.__ogias_injected__)'))

    def test_correspondance_ajout_motif_et_ambiguite_sans_publication(self):
        self.page.locator('#rf-creer').click()
        self.page.wait_for_selector('#rf-voir-pub')
        self.page.locator('[data-ref-objet="correspondances"]').click(timeout=1000)
        avant = self.api('/api/referentiel/vue?source=publie')['correspondances']
        self.page.locator('#ref-codes-add').click()
        for champ, valeur in {'type': 'GA', 'ancienne': 'TS_FICTIF', 'type_nouveau': 'GA', 'nouvelle': 'TS_INTR'}.items():
            self.page.locator('#ref-code-' + champ).fill(valeur)
        self.page.locator('#ref-code-save').click()
        self.assertEqual(self.api('/api/referentiel/vue?source=brouillon')['correspondances'], avant)
        self.page.locator('#ref-code-motif').fill('Essai fictif de remplacement')
        self.page.locator('#ref-code-save').click()
        self.page.wait_for_selector('.ref-code-detail', state='detached')
        apres = self.api('/api/referentiel/vue?source=brouillon')['correspondances']
        self.assertEqual(len(apres), len(avant) + 1)
        self.assertEqual(self.api('/api/referentiel/vue?source=publie')['correspondances'], avant)
        self.page.locator('#ref-codes-add').click()
        for champ, valeur in {'type': 'GA', 'ancienne': 'TS_FICTIF', 'type_nouveau': 'GA', 'nouvelle': 'TS_DEF', 'motif': 'Autre essai'}.items():
            self.page.locator('#ref-code-' + champ).fill(valeur)
        self.page.locator('#ref-code-save').click()
        self.page.wait_for_function("document.querySelector('#ref-code-error').textContent.includes('ambiguïté')")
        self.assertEqual(len(self.api('/api/referentiel/vue?source=brouillon')['correspondances']), len(apres))

    def test_archivage_type_en_brouillon_est_reversible(self):
        self.page.locator('#rf-creer').click()
        self.page.wait_for_selector('#rf-voir-pub')
        self.page.locator('[data-t="HV"]').click()
        self.page.locator('#rf-type-archive').click(timeout=1000)
        self.page.locator('#m-ok').click()
        self.page.wait_for_function("document.querySelector('#rf-type-archive').textContent.includes('Réactiver')")
        type_brouillon = next(t for t in self.api('/api/referentiel/vue?source=brouillon')['types'] if t['code'] == 'HV')
        type_publie = next(t for t in self.api('/api/referentiel/vue?source=publie')['types'] if t['code'] == 'HV')
        self.assertTrue(type_brouillon['archive'])
        self.assertFalse(type_publie['archive'])
        self.page.locator('#rf-type-archive').click()
        self.page.locator('#m-ok').click()
        self.page.wait_for_function("document.querySelector('#rf-type-archive').textContent.includes('Archiver')")
        self.assertFalse(next(t for t in self.api('/api/referentiel/vue?source=brouillon')['types'] if t['code'] == 'HV')['archive'])

    def test_commandes_existantes_uniques_et_accessibles(self):
        for ident in ('rf-creer', 'rf-exp', 'rf-hist'):
            self.assertEqual(self.page.locator('#' + ident).count(), 1)
            self.assertTrue(self.page.locator('#' + ident).is_visible())
        self.vue('lexique', brouillon=True)
        self.page.locator('.bandeau-ref summary').click()
        for ident in ('rf-voir-pub', 'rf-pub', 'rf-exp-b', 'rf-imp', 'rf-abandon'):
            self.assertEqual(self.page.locator('#' + ident).count(), 1)
            self.assertTrue(self.page.locator('#' + ident).is_visible())


if __name__ == '__main__':
    unittest.main()
