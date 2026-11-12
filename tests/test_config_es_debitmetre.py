"""Tests indépendants du paramétrage métier E/S d'un débitmètre fictif.

Aucun ouvrage réel ni connexion automate. Tests d'acceptation du parcours neuf.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from genvar.modele import Equipement
from genvar.session import Session, RegleMetier
from genvar.catalogue import Catalogue
from genvar import chemins
from sorep_web.serveur import Application

class TestConfigurationDebitmetre(unittest.TestCase):
    def setUp(self):
        self.precedent = os.environ.get('SOREP_DATA_DIR')
        self.donnees = tempfile.TemporaryDirectory()
        os.environ['SOREP_DATA_DIR'] = self.donnees.name
        self.session = Session(catalogue=Catalogue.charger(chemins.fichier_catalogue_origine()))
        self.session.nouveau(False)
        self.session.definir('lieu','X999')
        self.session.definir('code_ouvrage','RV')
        self.session.ajouter_sous_ensemble('11','Mesures')
        self.eq = self.session.ajouter_equipement(Equipement('11','FT','01','Débitmètre fictif'))
    def tearDown(self):
        if self.precedent is None: os.environ.pop('SOREP_DATA_DIR',None)
        else: os.environ['SOREP_DATA_DIR']=self.precedent
        self.donnees.cleanup()
    def test_options_physiques_disponibles_sans_imposition(self):
        pts={p.cle:p for p in self.session.points()}
        self.assertEqual([p.point for p in pts.values()], ['EA'])
        for option in ('Sortie impulsions câblée','Contact défaut TOR','Sens d’écoulement TOR'):
            self.assertIn(option,self.session.catalogue.options_du_type('FT'))
        self.session.choisir_option_es(self.eq.ident,'Sortie impulsions câblée', True)
        self.session.choisir_option_es(self.eq.ident,'Contact défaut TOR', True)
        self.session.choisir_option_es(self.eq.ident,'Sens d’écoulement TOR', True)
        pts={p.cle:p for p in self.session.points()}
        self.assertEqual({k:pts[k].point for k in ('ES_DEB','ES_IMP','ES_DEF_EXT','ES_SENS')},
                         {'ES_DEB':'EA','ES_IMP':'ET','ES_DEF_EXT':'ET','ES_SENS':'ET'})
        self.assertFalse(self.eq.valide)
        self.session.choisir_option_es(self.eq.ident,'Sens d’écoulement TOR',False)
        self.assertNotIn('ES_SENS',{p.cle for p in self.session.points()})
    def test_validation_exige_echelle_puis_impulsions(self):
        with self.assertRaisesRegex(RegleMetier,'échelle analogique'):
            self.session.valider_equipements([self.eq.ident])
        self.session.definir_analogique(self.eq.ident,'ES_DEB',{'signal_min':4,'signal_max':20,
          'phys_min':0,'phys_max':300,'unite':'m³/h'})
        with self.assertRaisesRegex(RegleMetier,'à décider'):       # CP_VOL proposé (FT-04) : décision exigée
            self.session.valider_equipements([self.eq.ident])
        self.session.decider_propositions(self.eq.ident,'retenir')
        self.assertEqual(self.session.valider_equipements([self.eq.ident]),1)
        self.session.choisir_option_es(self.eq.ident,'Sortie impulsions câblée',True)
        with self.assertRaisesRegex(RegleMetier,'poids d.impulsion'):
            self.session.valider_equipements([self.eq.ident])
        self.session.definir_impulsion(self.eq.ident,'ES_IMP',{'poids':'0.5','front':'Montant','unite':'m³'})
        self.session.decider_propositions(self.eq.ident,'ecarter','pas de surveillance des impulsions prévue')
        self.assertEqual(self.session.valider_equipements([self.eq.ident]),1)
    def test_echelle_rejet_sans_modification(self):
        bad=[{'signal_min':20,'signal_max':4,'phys_min':0,'phys_max':100,'unite':'m³/h'},
             {'signal_min':4,'signal_max':20,'phys_min':'abc','phys_max':100,'unite':'m³/h'},
             {'signal_min':4,'signal_max':20,'phys_min':0,'phys_max':0,'unite':'m³/h'},
             {'signal_min':4,'signal_max':20,'phys_min':0,'phys_max':100,'unite':'m³/h','brut_min':0},
             {'signal_min':4,'signal_max':20,'phys_min':0,'phys_max':100,'unite':'m³/h','brut_min':0,'brut_max':0}]
        for x in bad:
            with self.assertRaises(RegleMetier):self.session.definir_analogique(self.eq.ident,'ES_DEB',x)
            self.assertNotIn('analogique',self.eq.es_meta.get('ES_DEB',{}))
        ok={'signal_min':4,'signal_max':20,'phys_min':0,'phys_max':300,'unite':'m³/h','brut_min':0,'brut_max':27648}
        self.session.definir_analogique(self.eq.ident,'ES_DEB',ok)
        self.session.decider_propositions(self.eq.ident,'retenir')
        self.session.valider_equipements([self.eq.ident])
        self.session.definir_analogique(self.eq.ident,'ES_DEB',{**ok,'phys_max':450})
        self.assertFalse(self.eq.valide)
        self.assertFalse(self.eq.es_meta['ES_DEB']['validee'])
    def test_retention_ajout_perso_et_export_excel(self):
        self.session.definir_analogique(self.eq.ident,'ES_DEB',{'signal_min':4,'signal_max':20,'phys_min':0,'phys_max':300,'unite':'m³/h'})
        self.session.ajouter_es(self.eq.ident,'ET','BON','État de disponibilité')
        self.assertIn('ES_BON',[p.cle for p in self.session.points()])
        chemin=os.path.join(self.donnees.name,'essai.ouvrage.json')
        self.session.enregistrer(chemin)
        s2=Session();s2.ouvrir(chemin)
        self.assertEqual(s2.ouvrage.equipements[0].es_meta['ES_DEB']['analogique']['phys_max'],300.0)
        self.assertIn('ES_BON',[p.cle for p in s2.points()])
        dest=os.path.join(self.donnees.name,'liste.xlsx')
        s2.exporter_liste_es(dest)
        from genvar.catalogue_excel import lire_xlsx
        feuilles=lire_xlsx(dest)
        self.assertIn('Échelle analogique',feuilles['Liste des E/S'][0])
        self.assertTrue(any('300' in str(col) and 'm³/h' in str(col) for r in feuilles['Liste des E/S'][1:] for col in r))
    def test_export_html_inclut_echelle_analogique(self):
        from genvar.export_liste_es import html_liste_es
        self.session.definir_analogique(self.eq.ident,'ES_DEB',
            {'signal_min':4,'signal_max':20,'phys_min':0,'phys_max':800,'unite':'m³/h'})
        html=html_liste_es(self.session.ouvrage,self.session.liste_es())
        self.assertIn('Configuration analogique / impulsions',html)
        self.assertIn('0–800 m³/h',html)

    def test_referentiel_affiche_es_et_lignes_supervision(self):
        app=Application();app.s=self.session;app.ouvert=True
        # Modèle éventuellement absent : en créer un depuis le catalogue sans modifier la référence utilisateur.
        noms=[m for m,v in self.session.modeles['modeles'].items() if v.get('type')=='FT']
        if not noms:
            nom=self.session.creer_modele('FT','MODELE_DEBITMETRE_TEST',True)
        else:
            nom=noms[0]
        detail=app.modele({'nom':nom})
        self.assertIn('lignes',detail)
        self.assertIn('es_type',detail)
        self.assertIn('ES_DEB',{'ES_'+x['code'] for x in detail['es_type']})
        self.assertTrue(any(x['presence']=='Option' for x in detail['es_type']))
        self.assertFalse(any('adresse' in x for x in detail['es_type']))

    def test_ancien_ouvrage_echelle_manquante_redevient_a_valider_sans_ecriture(self):
        # Migration prudente des anciens ouvrages déclarés validés avant la nouvelle règle.
        self.eq.valide=True
        chemin=os.path.join(self.donnees.name,'ancien_ouvrage.json')
        self.session.enregistrer(chemin)
        avant=Path(chemin).read_bytes()
        s2=Session();s2.ouvrir(chemin)
        self.assertFalse(s2.ouvrage.equipements[0].valide)
        self.assertIn('échelle analogique',s2.avertissement_ouverture)
        self.assertEqual(Path(chemin).read_bytes(),avant)

    def test_api_bloque_et_permet_apres_validation(self):
        app=Application();app.s=self.session;app.ouvert=True
        with self.assertRaisesRegex(RegleMetier, 'Validez d.abord'):
            app.es({})
        self.assertEqual(app.equipement({'ident': self.eq.ident})['signaux_es'][0]['point'],'EA')
        self.session.definir_analogique(self.eq.ident,'ES_DEB',{'signal_min':4,'signal_max':20,'phys_min':0,'phys_max':450,'unite':'m³/h'})
        app.decider_proposition({'ident_eq':self.eq.ident,'decision':'retenir'})
        app.valider_equipements({'idents':[self.eq.ident]})
        es=app.es({})
        self.assertEqual(es['points'][0]['analogique']['phys_max'],450)

if __name__=='__main__':unittest.main()
