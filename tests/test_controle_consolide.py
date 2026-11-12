"""Sécurité du parcours de reprise et de validation — jeux de données fictifs."""
import tempfile
import unittest
from pathlib import Path
from genvar import chemins, existant, import_sources
from genvar.catalogue import Catalogue
from genvar.modele import Equipement, SousEnsemble, Ouvrage, VariableExistante
from genvar.qualification import qualifications
from genvar.session import Session, RegleMetier


class ControleConsolide(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat=Catalogue.charger(chemins.fichier_catalogue_origine())

    def projet(self,mode='Existant',typ='MV'):
        o=Ouvrage(lieu='F999',code_ouvrage='RV',mode=mode,automate='TSX57' if mode=='Existant' else 'M580')
        o.sous_ensembles=[SousEnsemble('11')]
        eq=Equipement('11',typ,'03')
        o.equipements=[eq]
        return o,eq

    def test_analogique_int_vers_real_refuse_en_correspondance(self):
        o,eq=self.projet(typ='FT')
        v=VariableExistante('TM_F999RV11FT03_DEB','INT','%MW200',ident_eq=eq.ident,
                            cle='TM_DEB',identification='Confirmée')
        o.existantes=[v]
        q=qualifications(o,self.cat)[id(v)]
        self.assertEqual(q.niveau,'Incohérence')
        self.assertIn('INT',q.motif)
        self.assertIn('REAL',q.motif)

    def test_bool_et_ebool_sont_compatibles(self):
        o,eq=self.projet()
        v=VariableExistante('TS_F999RV11MV03_FER','EBOOL','%M120',ident_eq=eq.ident,
                            cle='TS_FER',identification='Confirmée')
        o.existantes=[v]
        self.assertEqual(qualifications(o,self.cat)[id(v)].niveau,'Validée')

    def test_opc_non_localise_n_est_pas_certifie_par_correspondance(self):
        o,eq=self.projet()
        v=VariableExistante('TS_F999RV11MV03_FER','BOOL','Station1.V3_FER',ident_eq=eq.ident,
                            cle='TS_FER',identification='Confirmée')
        o.existantes=[v]
        self.assertEqual(qualifications(o,self.cat)[id(v)].niveau,'À confirmer')

    def test_changement_champ_invalide_statut(self):
        o,eq=self.projet(mode='Neuf')
        o.statut='Validé'
        s=Session(self.cat,o)
        s.definir('libelle','Réservoir de test')
        self.assertEqual(o.statut,'À contrôler')
        self.assertTrue(s.modifie)

    def test_choix_explicite_statut_valide_reste_possible(self):
        o,_=self.projet(mode='Neuf')
        s=Session(self.cat,o)
        with self.assertRaises(RegleMetier):      # règle durcie : refus dès la demande s'il reste des erreurs
            s.definir('statut','Validé')
        self.assertNotEqual(o.statut,'Validé')

    def test_changer_mode_apres_adressage_refuse_et_ne_change_rien(self):
        o,eq=self.projet(mode='Neuf')
        eq.adresses['TS_DEF']='%MW1000.0'
        s=Session(self.cat,o)
        with self.assertRaises(RegleMetier):
            s.definir('mode','Existant')
        self.assertEqual(o.mode,'Neuf')

    def test_reimport_commentaire_annule_validation_et_statut(self):
        o,eq=self.projet()
        v=VariableExistante('TS_F999RV11MV03_FER','BOOL','%M120','Retour fermée',
                            ident_eq=eq.ident,cle='TS_FER',identification='Confirmée')
        o.existantes=[v]
        o.statut='Validé'
        existant.importer_lignes(o,[(v.nom,'BOOL','%M120','NOUVEAU commentaire')])
        self.assertEqual(o.statut,'À contrôler')
        self.assertEqual(v.identification,'À identifier')
        self.assertEqual(v.adresse,'%M120')

    def test_reimport_identique_ne_devalide_pas(self):
        o,eq=self.projet()
        v=VariableExistante('TS_F999RV11MV03_FER','BOOL','%M120','Retour fermé',
                            ident_eq=eq.ident,cle='TS_FER',identification='Confirmée')
        o.existantes=[v];o.statut='Validé'
        existant.importer_lignes(o,[(v.nom,'BOOL','%M120','Retour fermé')])
        self.assertEqual(o.statut,'Validé')
        self.assertEqual(v.identification,'Confirmée')

    def test_nouveau_signal_dans_projet_valide_declasse(self):
        o,_=self.projet()
        o.statut='Validé'
        existant.importer_lignes(o,[('TS_F999RV11MV03_OUV','BOOL','%M121','Retour ouvert')])
        self.assertEqual(o.statut,'À contrôler')

    def test_lignes_non_mappees_non_ignorees(self):
        headers=['Nom','Adresse','Informations']
        rows=[['TS_A','%M120',''],['','','DONNÉE NON MAPPÉE']]
        with self.assertRaisesRegex(ValueError,'nom manquant'):
            import_sources.preparer_lignes(headers,rows,{'nom':0,'adresse':1})

    def test_colonnes_source_conflit_mapping_refuse(self):
        with self.assertRaisesRegex(ValueError,'même colonne'):
            import_sources.preparer_lignes(['Nom','Adresse'],[['TS_A','%M10']],
                                           {'nom':0,'adresse':1,'type':1})

    def test_scy_en_tete_avec_adresse_invalide_ne_passe_pas(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'export.scy'
            path.write_text('Adresse;Nom\n%M120;TS_A\nadresse_inconnue;TS_B\n',encoding='utf8')
            with self.assertRaisesRegex(ValueError,'Aucun import partiel'):
                import_sources.charger_table(path)

    def test_scy_sans_en_tete_ligne_non_lue_bloque(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'export.scy'
            path.write_text('%M120;TS_A;Marche\nLIGNE INDÉCODABLE\n%M130;TS_B;Défaut\n',encoding='utf8')
            with self.assertRaisesRegex(ValueError,'Aucun import partiel'):
                import_sources.charger_table(path)

    def test_reimport_absentes_non_supprimees(self):
        o,_=self.projet()
        existant.importer_lignes(o,[('TS_A','BOOL','%M120',''),('TS_B','BOOL','%M121','')])
        nouveau=[('TS_A','BOOL','%M120','')]
        self.assertEqual(existant.absentes_reimport(o,nouveau),['TS_B'])
        existant.importer_lignes(o,nouveau)
        self.assertEqual(len(o.existantes),2)
        self.assertEqual(o.existantes[1].adresse,'%M121')


if __name__ == '__main__':
    unittest.main()

class ControleMiroirTRRTR(unittest.TestCase):
    def setUp(self):
        self.cat=Catalogue.charger(chemins.fichier_catalogue_origine())
        self.o=Ouvrage(mode='Neuf',lieu='F999',code_ouvrage='RV',automate='M580')
        self.o.sous_ensembles=[SousEnsemble('11')]
        self.eq=Equipement('11','LT','01',options=['Seuils réglables'])
        self.o.equipements=[self.eq]
        self.s=Session(self.cat,self.o)

    def test_miroir_tr_rtr_genere(self):
        propos,erreurs=self.s.plan()
        self.assertFalse(erreurs)
        self.s.appliquer(propos)
        vars_={v.cle:v for v in self.s.variables()}
        self.assertEqual(int(vars_['RTR_SH'].adresse[3:])-4000,
                         int(vars_['TR_SH'].adresse[3:])-100)

    def test_miroir_manuel_incoherent_refuse(self):
        props,erreurs=self.s.plan();self.assertFalse(erreurs)
        self.s.appliquer(props)
        vars_={v.cle:v for v in self.s.variables()}
        tr=vars_['TR_SH']
        original=tr.adresse
        with self.assertRaisesRegex(RegleMetier,'TR/RTR'):
            self.s.definir_adresses(tr.ident_eq,tr.cle,adresse='%MW150')
        self.assertEqual({v.cle:v.adresse for v in self.s.variables()}['TR_SH'],original)

    def test_miroir_deja_incoherent_bloque_plan(self):
        props,erreurs=self.s.plan();self.assertFalse(erreurs)
        self.s.appliquer(props)
        self.eq.adresses['RTR_SH']='%MW4050'
        props,erreurs=self.s.plan()
        self.assertEqual(props,[])
        self.assertTrue(any('non alignée' in e for e in erreurs), erreurs)
        self.assertTrue(any('miroir' in a.message for a in self.s.anomalies()))

