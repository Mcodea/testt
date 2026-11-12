"""Recette V0.29 de l'étape 2 : édition de contenu sans affecter de voies.

Données entièrement fictives ; aucune qualification Control Expert ou SOFREL.
"""
from pathlib import Path
import os
import tempfile
import unittest

from genvar.catalogue import Catalogue
from genvar import chemins
from genvar.modele import Equipement
from genvar.session import Session, RegleMetier
from sorep_web.serveur import Application

ROOT = Path(__file__).resolve().parents[1]


class TestVueESV029(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get('SOREP_DATA_DIR')
        self.tmp = tempfile.TemporaryDirectory()
        os.environ['SOREP_DATA_DIR'] = self.tmp.name
        self.app = Application()
        self.app.s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        self.app.s.nouveau(False)
        self.app.s.definir('lieu', 'XTST')
        self.app.s.definir('code_ouvrage', 'RV')
        self.app.s.definir('numero_ouvrage', '01')
        self.app.s.ajouter_sous_ensemble('11', 'Hydraulique')
        self.app.s.ajouter_uf('UF01', 'Mesure')
        self.ft = self.app.s.ajouter_equipement(Equipement('11', 'FT', '01', 'Débit fictif', uf='UF01'))
        self.app.s.definir_analogique(self.ft.ident, 'ES_DEB', {
            'signal_min': 4, 'signal_max': 20, 'phys_min': 0, 'phys_max': 300, 'unite': 'm³/h'})
        self.app.s.decider_propositions(self.ft.ident, 'retenir')
        self.app.s.valider_equipements([self.ft.ident])

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop('SOREP_DATA_DIR', None)
        else:
            os.environ['SOREP_DATA_DIR'] = self.ancien
        self.tmp.cleanup()

    def test_interface_principes_et_routes_conservees(self):
        js = (ROOT / 'sorep_web/static/app.js').read_text(encoding='utf-8')
        css = (ROOT / 'sorep_web/static/app.css').read_text(encoding='utf-8')
        for token in ('function vueES()', 'function brancherListeES(', '/api/es', '/api/es/definir',
                      '/api/es/valider', 'data-uf', 'x-equip', 'es-panneau', 'es-pc', 'x-val-tout',
                      'x-val', 'es-voie', 'es-code', 'aria-label', 'tabindex="0"'):
            self.assertIn(token, js)
        for token in ('.es-ruban', '.es-panneau', '.es-table', '@media'):
            self.assertIn(token, css)

    def test_composants_api_pcf_nom_cle_et_statuts(self):
        payload = self.app.es({})
        self.assertEqual(len(payload['points']), 1)
        p = payload['points'][0]
        self.assertEqual((p['pcf'], p['nom'], p['cle'], p['point']),
                         ('XTSTRV01FT01', 'EA_RV01FT01_DEB', 'ES_DEB', 'EA'))
        self.assertFalse(p['contenu_valide'])
        self.assertEqual(p['note'], '')

    def test_panneau_edition_et_validation_nature_et_echelle(self):
        self.app.es_definir({'ident_eq': self.ft.ident, 'cle': 'ES_DEB', 'designation': 'Débit aval',
                             'note': 'Mesure au départ', 'raccordement': 'Câblé',
                             'analogique': {'signal_min': 4, 'signal_max': 20, 'phys_min': 0,
                                           'phys_max': 450, 'unite': 'm³/h'}, 'valider_contenu': True})
        p = self.app.es({})['points'][0]
        self.assertEqual((p['designation'], p['note']), ('Débit aval', 'Mesure au départ'))
        self.assertEqual(p['analogique']['phys_max'], 450)
        self.assertTrue(p['contenu_valide'])
        self.assertEqual((p['module'], p['voie'], p['adresse']), ('', '', ''))
        self.assertTrue(self.app.s.ouvrage.equipement(self.ft.ident).valide)

    def test_modification_decale_validation_et_pas_le_materiel(self):
        self.app.es_valider({'niveau': 'contenu', 'valide': True,
                            'paires': [{'ident_eq': self.ft.ident, 'cle': 'ES_DEB'}]})
        self.app.es_definir({'ident_eq': self.ft.ident, 'cle': 'ES_DEB', 'note': 'Note modifiée'})
        self.assertFalse(self.app.es({})['points'][0]['contenu_valide'])
        self.assertEqual(self.app.es({})['bilan']['contenu_non_valide'], 1)
        with self.assertRaises(RegleMetier):
            self.app.s.proposer_materiel()

    def test_erreur_echelle_aucune_edition_partielle(self):
        before = self.app.es({})['points'][0]
        with self.assertRaises(RegleMetier):
            self.app.es_definir({'ident_eq': self.ft.ident, 'cle': 'ES_DEB',
                                 'designation': 'NE DOIT PAS RESTER',
                                 'note': 'NE DOIT PAS RESTER',
                                 'analogique': {'signal_min': 20, 'signal_max': 4, 'phys_min': 0,
                                               'phys_max': 99, 'unite': 'm³/h'},
                                 'valider_contenu': True})
        after = self.app.es({})['points'][0]
        self.assertEqual((before['designation'], before['note'], before['analogique']),
                         (after['designation'], after['note'], after['analogique']))
        self.assertFalse(after['contenu_valide'])

    def test_commentaire_conserve_dans_le_livrable(self):
        from genvar.export_liste_es import lignes, ENTETES
        self.app.es_definir({'ident_eq': self.ft.ident, 'cle': 'ES_DEB',
                             'note': 'Étalonnage prévu après montage'})
        self.assertEqual(ENTETES[-1], 'Commentaire')
        self.assertEqual(lignes(self.app.s.ouvrage, self.app.s.points())[0][-1],
                         'Étalonnage prévu après montage')

    def test_filtres_grand_inventaire_cinquante_equipements(self):
        for n in range(1, 56):
            eq = self.app.s.ajouter_equipement(Equipement('11', 'HV', f'{n:02d}', 'Vanne fictive', uf='UF01'))
            self.app.s.decider_propositions(eq.ident, 'retenir')
            self.app.s.valider_equipements([eq.ident])
        payload = self.app.es({})
        self.assertGreaterEqual(len({p['pcf'] for p in payload['points']}), 56)
        self.assertEqual(len({p['pcf'] for p in payload['points']}), 56)
        self.assertTrue(all(p['uf'] == 'UF01' for p in payload['points']))

    def test_api_http_panneau_et_routes_historiques(self):
        """Le nouveau panneau appelle les API historiques sans contournement des validations."""
        import json
        import threading
        import urllib.request
        import urllib.error
        from http.server import ThreadingHTTPServer
        from sorep_web.serveur import fabriquer_gestionnaire
        serveur = ThreadingHTTPServer(('127.0.0.1', 0), fabriquer_gestionnaire(self.app))
        self.app.ouvert = True
        self.app.s.chemin = str(Path(self.tmp.name) / 'ouvrage_fictif.ouvrage.json')
        thread = threading.Thread(target=serveur.serve_forever, daemon=True)
        thread.start()
        racine = f'http://127.0.0.1:{serveur.server_address[1]}'

        def appel(chemin, donnees=None):
            req = urllib.request.Request(racine + chemin, data=None if donnees is None else
                json.dumps(donnees).encode('utf8'), headers={'Content-Type': 'application/json'})
            try:
                with urllib.request.urlopen(req, timeout=5) as rep:
                    return rep.status, json.loads(rep.read())
            except urllib.error.HTTPError as rep:
                return rep.code, json.loads(rep.read())

        try:
            self.assertEqual(appel('/api/es')[0], 200)
            self.assertEqual(appel('/api/es/definir', {'ident_eq': self.ft.ident, 'cle': 'ES_DEB',
                'note': 'Vérifier le coefficient du capteur', 'valider_contenu': True})[0], 200)
            self.assertEqual(appel('/api/es')[1]['points'][0]['note'], 'Vérifier le coefficient du capteur')
            self.assertTrue(appel('/api/es')[1]['points'][0]['contenu_valide'])
            self.assertEqual(appel('/api/es/valider', {'niveau': 'contenu', 'valide': False,
                'paires': [{'ident_eq': self.ft.ident, 'cle': 'ES_DEB'}]})[0], 200)
            self.assertFalse(appel('/api/es')[1]['points'][0]['contenu_valide'])
        finally:
            serveur.shutdown()
            serveur.server_close()

    def test_validation_groupee_api_originale_reste_disponible(self):
        pair = [{'ident_eq': self.ft.ident, 'cle': 'ES_DEB'}]
        self.assertEqual(self.app.es_valider({'niveau': 'contenu', 'paires': pair, 'valide': True})['n'], 1)
        self.assertTrue(self.app.es({})['points'][0]['contenu_valide'])
        self.assertEqual(self.app.es_valider({'niveau': 'contenu', 'paires': pair, 'valide': False})['n'], 1)
        self.assertFalse(self.app.es({})['points'][0]['contenu_valide'])


if __name__ == '__main__':
    unittest.main()
