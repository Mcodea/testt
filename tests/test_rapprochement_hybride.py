"""Tests moteur et reprise non destructive, sans dépendance Qt."""
import tempfile
import unittest
from pathlib import Path

from genvar.catalogue import Catalogue
from genvar import chemins
from genvar.liste_es import charger_liste_es
from genvar.modele import Ouvrage, Equipement, SousEnsemble, VariableExistante
from genvar.qualification import qualifications
from genvar.rapprochement import proposer, appliquer_choix


class RapprochementHybride(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = Catalogue.charger(chemins.fichier_catalogue_origine())

    def exemple(self):
        o = Ouvrage(mode='Existant', code_ouvrage='RV', automate='TSX57')
        o.sous_ensembles = [SousEnsemble('11')]
        eq = Equipement('11', 'MV', '03')
        o.equipements = [eq]
        return o, eq

    def test_propositions_n_modifient_jamais_le_referentiel(self):
        o, e = self.exemple()
        v = VariableExistante('TS_RV11MV03_FER', 'BOOL', '%M120', 'Retour fermée')
        o.existantes.append(v)
        avant = o.vers_dict()
        p = proposer(o, self.cat, 'hybride')
        self.assertTrue(p[(e.ident,'TS_FER')])
        self.assertEqual(o.vers_dict(), avant)

    def test_source_et_adresse_conservees_a_confirmation(self):
        o, e = self.exemple()
        v = VariableExistante('INCONNUE_14', 'BOOL', '%M120', 'Retour vanne')
        o.existantes.append(v)
        appliquer_choix(o, self.cat, 'INCONNUE_14', e.ident, 'TS_FER')
        self.assertEqual((v.nom,v.adresse,v.type_logique),('INCONNUE_14','%M120','BOOL'))
        self.assertEqual(v.identification,'Confirmée')
        self.assertEqual(qualifications(o,self.cat)[id(v)].niveau,'Validée')

    def test_type_incompatible_refuse_meme_selection_manuel(self):
        o, e = self.exemple()
        o.existantes=[VariableExistante('V3_FER','REAL','%MF120')]
        with self.assertRaisesRegex(ValueError, 'Types incompatibles'):
            appliquer_choix(o,self.cat,'V3_FER',e.ident,'TS_FER')

    def test_doublon_de_signal_refuse(self):
        o, e = self.exemple()
        o.existantes=[VariableExistante('A','BOOL','%M1',ident_eq=e.ident,cle='TS_FER'),
                     VariableExistante('B','BOOL','%M2')]
        with self.assertRaisesRegex(ValueError,'déjà'):
            appliquer_choix(o,self.cat,'B',e.ident,'TS_FER')

    def test_es_physique_n_est_pas_proposee_comme_ts(self):
        o,e=self.exemple()
        o.existantes=[VariableExistante('TS_RV11MV03_FER','BOOL','%I0.3.2','Vanne fermée')]
        self.assertEqual(proposer(o,self.cat,'hybride')[(e.ident,'TS_FER')],[])

    def test_es_physique_associee_manuellement_ne_devient_pas_verte_sans_verification(self):
        o,e=self.exemple()
        v=VariableExistante('V3_FER','BOOL','%I0.3.2',ident_eq=e.ident,cle='TS_FER',identification='Confirmée')
        o.existantes=[v]
        self.assertEqual(qualifications(o,self.cat)[id(v)].niveau,'À confirmer')

    def test_liste_es_est_enregistree_et_relue(self):
        o,e=self.exemple()
        o.entrees_physiques_importees=[{'nom':'I_15','adresse':'%I0.3.1','equipement':'MV03',
                                         'fonction':'Fermée','commentaire':'','variable_liee':''}]
        with tempfile.TemporaryDirectory() as d:
            chemin=str(Path(d)/'site.ouvrage.json')
            o.enregistrer(chemin)
            restored=Ouvrage.ouvrir(chemin)
            self.assertEqual(restored.entrees_physiques_importees,o.entrees_physiques_importees)

    def test_import_es_n_accepte_pas_les_doublons(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.csv'
            p.write_text('Nom;Equipement;Fonction\nI_15;MV03;Fermée\nI_15;MV03;Ouverte\n',encoding='utf8')
            with self.assertRaisesRegex(ValueError,'double'):
                charger_liste_es(p)

    def test_import_es_rejette_les_colonnes_insuffisantes(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.csv'
            p.write_text('Nom;Adresse\nI_15;%I0.3.1\n',encoding='utf8')
            with self.assertRaisesRegex(ValueError,'obligatoires'):
                charger_liste_es(p)

    def test_source_es_renforce_sans_creation_de_variable(self):
        o,e=self.exemple()
        o.existantes=[VariableExistante('MEM_32','BOOL','%M501','Traitement I_15')]
        o.entrees_physiques_importees=[{'nom':'I_15','adresse':'%I0.3.1','equipement':'MV03',
                                       'fonction':'Fin course fermée','commentaire':'','variable_liee':''}]
        self.assertEqual(proposer(o,self.cat,'catalogue')[(e.ident,'TS_FER')],[])
        p=proposer(o,self.cat,'hybride')[(e.ident,'TS_FER')]
        self.assertEqual(p[0].variable_nom,'MEM_32')
        self.assertEqual(o.existantes[0].identification,'À identifier')

    def test_sans_type_les_propositions_sont_refusees(self):
        o,e=self.exemple()
        o.existantes=[VariableExistante('TS_RV11MV03_FER','','%M100')]
        self.assertFalse(proposer(o,self.cat,'programme')[(e.ident,'TS_FER')])

    def test_benchmarks_deux_scenarios(self):
        from validation.hybride.evaluer import evaluer, BASE
        for jeu in (BASE, BASE/'jeu_difficile'):
            r=evaluer(jeu)
            self.assertEqual(r['jeu']['liens_attendus'],18)
            self.assertGreaterEqual(r['methodes']['hybride']['corrects'],r['methodes']['catalogue']['corrects'])
            self.assertGreaterEqual(r['methodes']['catalogue']['corrects'],r['methodes']['programme']['corrects'])
            for m in r['methodes'].values():
                self.assertEqual(m['corrects']+m['faux']+m['non_proposes'],18)


if __name__=='__main__':unittest.main()
