import unittest
from genvar.modele import Ouvrage, SousEnsemble, Equipement, plan_adresses
from genvar.catalogue import Catalogue
from genvar import chemins

class TestPlanV08(unittest.TestCase):
    def setUp(self):
        self.cat = Catalogue.charger(chemins.fichier_catalogue_origine())
        self.o = Ouvrage(lieu='XT25', code_ouvrage='RV')
        self.o.sous_ensembles=[SousEnsemble('11')]
        self.eq=Equipement('11','PM','01', options=['Variateur'])
        self.o.equipements=[self.eq]
    def test_chevauchement_plages_refuse(self):
        self.o.zones['TC']=1000
        p,e=plan_adresses(self.o,self.cat)
        self.assertEqual(p,[])
        self.assertTrue(any('chevauchantes' in x for x in e))
        self.assertFalse(self.eq.adresses)
    def test_collision_existante_bloque_toute_attribution(self):
        self.eq.adresses['TS_MA']='%MW1000.0'
        self.eq.adresses['TS_DEF']='%MW1000.0'
        p,e=plan_adresses(self.o,self.cat)
        self.assertEqual(p,[])
        self.assertTrue(any('Chevauchement existant' in x for x in e))
        self.assertEqual(self.eq.adresses['TS_MA'],'%MW1000.0')
    def test_mauvaise_adresse_existante_bloque(self):
        self.eq.adresses['TR_FREQ']='%MW101'
        p,e=plan_adresses(self.o,self.cat)
        self.assertEqual(p,[])
        self.assertTrue(any('impaire' in x for x in e))

if __name__=='__main__': unittest.main()
