"""Tests des trois couleurs métier, de l'import sans effet de bord et du retour d'adresse."""
import unittest
from genvar.modele import Ouvrage, Equipement, SousEnsemble, VariableExistante
from genvar.catalogue import Catalogue
from genvar import chemins, existant
from genvar.qualification import qualifications


class TestQualification(unittest.TestCase):
    def setUp(self):
        self.cat = Catalogue.charger(chemins.fichier_catalogue_origine())
        self.o = Ouvrage(mode='Existant', lieu='XT25', code_ouvrage='RV', automate='TSX57')
        self.o.sous_ensembles = [SousEnsemble('11')]
        self.eq = Equipement('11','MV','03')
        self.o.equipements = [self.eq]
        self.v = VariableExistante('TS_XT25RV11MV03_FER', 'BOOL', '%M120', 'Fermée', ident_eq=self.eq.ident,
                                  cle='TS_FER', identification='Exacte')
        self.o.existantes = [self.v]

    def test_exacte_reste_orange_avant_validation(self):
        self.assertEqual(qualifications(self.o, self.cat)[id(self.v)].niveau, 'À confirmer')
        existant.confirmer([self.v])
        self.assertEqual(qualifications(self.o, self.cat)[id(self.v)].niveau, 'Validée')

    def test_doublon_rouge_meme_si_confirme(self):
        self.v.identification = 'Confirmée'
        w = VariableExistante('TS_2', 'BOOL', '%M121', '', ident_eq=self.eq.ident,
                              cle='TS_FER', identification='Confirmée')
        self.o.existantes.append(w)
        self.assertEqual(qualifications(self.o, self.cat)[id(self.v)].niveau, 'Incohérence')
        self.assertEqual(qualifications(self.o, self.cat)[id(w)].niveau, 'Incohérence')

    def test_type_incompatible_rouge(self):
        self.v.identification = 'Confirmée'
        self.v.type_logique = 'REAL'
        self.assertEqual(qualifications(self.o, self.cat)[id(self.v)].niveau, 'Incohérence')

    def test_hors_supervision_ne_devient_pas_rouge(self):
        self.v.retenue = False
        self.assertEqual(qualifications(self.o, self.cat)[id(self.v)].niveau, 'Hors supervision')

    def test_reimport_changement_adresse_demande_validation(self):
        self.v.identification = 'Confirmée'
        avant = existant.differences_reimport(self.o, [('TS_XT25RV11MV03_FER','BOOL','%M200','Fermée')])
        self.assertEqual(self.v.adresse,'%M120')
        self.assertTrue(any(x[1] == 'Adresse' for x in avant))
        existant.importer_lignes(self.o, [('TS_XT25RV11MV03_FER','BOOL','%M200','Fermée')])
        self.assertEqual(self.v.adresse,'%M200')
        self.assertNotEqual(self.v.identification,'Confirmée')

    def test_txs_sans_faux_controle_alignement_m580(self):
        self.o.automate='TSX57'; self.v.type_logique='REAL'; self.v.adresse='%MW101'
        erreurs=existant.controler_existant(self.o, self.cat)
        self.assertFalse(any('impaire' in a.message for a in erreurs))

if __name__ == '__main__': unittest.main()
