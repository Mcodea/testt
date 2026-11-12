"""Non-régression des anomalies A01-A03 de l'audit V0.8."""
import tempfile
import unittest
from pathlib import Path
from genvar import chemins, existant, import_sources
from genvar.catalogue import Catalogue
from genvar.modele import Ouvrage, SousEnsemble, Equipement, VariableExistante
from genvar.session import Session, RegleMetier
from genvar.qualification import qualifications

class AuditCorrectifs(unittest.TestCase):
    def setUp(self):
        self.catalogue = Catalogue.charger(chemins.fichier_catalogue_origine())
        self.o = Ouvrage(mode='Existant', lieu='XT25', code_ouvrage='RV', automate='TSX57')
        self.o.sous_ensembles.append(SousEnsemble('11'))
        self.eq = Equipement('11','MV','03')
        self.o.equipements.append(self.eq)

    def enregistrer_valide(self):
        self.o.statut = 'Validé'
        with tempfile.TemporaryDirectory() as d:
            self.session.enregistrer(str(Path(d)/'essai.ouvrage.json'))

    def test_a01_exacte_non_confirmee_interdite(self):
        v = VariableExistante('TS_TEMP', 'BOOL', '%M1', identification='Exacte')
        self.o.existantes.append(v)
        self.session = Session(self.catalogue, self.o)
        self.assertEqual(qualifications(self.o, self.catalogue)[id(v)].niveau,'À confirmer')
        with self.assertRaises(RegleMetier):          # refus : à confirmer, et table TT absente
            self.enregistrer_valide()

    def test_a03_type_absent_ne_devient_pas_vert(self):
        v = VariableExistante('TS_XT25RV11MV03_FER','', '%M120', ident_eq=self.eq.ident,
                              cle='TS_FER', identification='Confirmée')
        self.o.existantes.append(v)
        self.session = Session(self.catalogue,self.o)
        q = qualifications(self.o,self.catalogue)[id(v)]
        self.assertEqual(q.niveau,'À confirmer')
        self.assertIn('Type',q.motif)
        with self.assertRaises(RegleMetier): self.enregistrer_valide()

    def test_valide_apres_confirmation_avec_type(self):
        self.o.existantes.append(VariableExistante('TS_XT25RV11MV03_FER','BOOL','%M120',
             ident_eq=self.eq.ident,cle='TS_FER',identification='Confirmée'))
        self.session=Session(self.catalogue,self.o)
        # Règle durcie (version ChatGPT) : « Validé » exige aussi une table de télétransmission complète.
        with self.assertRaisesRegex(RegleMetier, 'télétransmission'):
            self.enregistrer_valide()

    def test_a02_conflit_import_atomique(self):
        original = VariableExistante('TS_A','BOOL','%M5')
        self.o.existantes=[original]
        lignes=[('TS_A','BOOL','%M11',''),('TS_A','BOOL','%M12','')]
        with self.assertRaisesRegex(ValueError,'conflit'):
            existant.importer_lignes(self.o,lignes)
        self.assertEqual(original.adresse,'%M5')
        self.assertEqual(len(self.o.existantes),1)

    def test_identiques_dedoubles_trace(self):
        lignes,w=import_sources.verifier_lignes_import([('A','BOOL','%M1','X'),('A','BOOL','%M1','X')])
        self.assertEqual(len(lignes),1)
        self.assertEqual(len(w),1)
        rapport=import_sources.rapport_import(2,lignes,w)
        self.assertIn('2',rapport)
        self.assertIn('Doublons strictement identiques : 1',rapport)

    def test_nom_invalide_non_ignore(self):
        with self.assertRaises(ValueError):
            import_sources.verifier_lignes_import([('A','BOOL','%M1',''),('','BOOL','%M2','')])

    def test_adresse_absente_et_type_absent_reste_en_attente(self):
        lignes,w=import_sources.verifier_lignes_import([('A','','','')])
        self.assertEqual(len(lignes),1)
        self.assertEqual(len(w),2)

if __name__ == '__main__': unittest.main()
