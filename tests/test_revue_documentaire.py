"""Tests de tri documentaire sans connaissance de la destination TOPKAPI."""
import tempfile
import unittest
from pathlib import Path
from genvar.analyse_pdf_pl7 import InventairePDF, Occurrence, IndiceSymbole, AffectationDocumentaire, LienDocumentaire
from genvar.revue_documentaire import preparer_revue


def jeu():
    b=InventairePDF('doc_fictif.pdf','test',3,3)
    b.occurrences=[Occurrence(a,2,'échantillon','Programme (indice de rubrique)')
                   for a in ['%IW0.2','%MW5','%MW10','%MW99','%QW0.10','%MW500']]
    b.indices_symboles=[
        IndiceSymbole('%IW0.2','Pt100','Sonde température',2),
        IndiceSymbole('%MW5','Temp','Température calculée',2),
        IndiceSymbole('%MW99','Buffer_xbt','Table de gestion XBT',3),
    ]
    b.affectations_documentaires=[
        AffectationDocumentaire('%MW5',['%IW0.2'],'%MW5:=%IW0.2/10',2),
        AffectationDocumentaire('%MW10',['%MW5'],'%MW10:=%MW5',3),
        AffectationDocumentaire('%MW99',[],'%MW99:=4',3),
        AffectationDocumentaire('%MW500',['%MW99'],'%MW500:=%MW99',3),
    ]
    return b

class TestRevueDocumentaire(unittest.TestCase):
    def test_chainage_borne_et_preuve(self):
        r={x.adresse:x for x in preparer_revue(jeu())}
        self.assertEqual(r['%MW10'].origine_potentielle,'%IW0.2')
        self.assertEqual(r['%MW10'].preuves_pages,'2 | 3')
        self.assertIn('E/S',r['%MW10'].categorie)
        self.assertEqual(r['%MW10'].adresse_acquisition_topkapi,'')
        self.assertEqual(r['%MW10'].statut,'À examiner — non validé')

    def test_pupitre_pas_supervision_et_variables_inconnues_conservees(self):
        r={x.adresse:x for x in preparer_revue(jeu())}
        self.assertIn('pas une preuve TOPKAPI',r['%MW99'].categorie)
        self.assertIn('rôle à qualifier',r['%MW500'].categorie)
        self.assertEqual(len(r),6)
        self.assertIn('physique',r['%QW0.10'].categorie)

    def test_symboles_contradictoires_non_masques(self):
        b=jeu()
        b.indices_symboles.append(IndiceSymbole('%MW99','Autre_symbole','',3))
        x=next(x for x in preparer_revue(b) if x.adresse=='%MW99')
        self.assertIn('Buffer_xbt',x.symbole)
        self.assertIn('Autre_symbole',x.symbole)

    def test_boucle_ne_gele_pas(self):
        b=jeu()
        b.affectations_documentaires.append(AffectationDocumentaire('%MW5',['%MW10'],'%MW5:=%MW10',2))
        r={x.adresse:x for x in preparer_revue(b)}
        self.assertEqual(r['%MW10'].origine_potentielle,'%IW0.2')

    def test_liens_il_rattaches_mais_jamais_valides(self):
        b=InventairePDF('test_texte.pdf','xyz',2,2)
        b.occurrences=[Occurrence(a,1,a,'Programme (indice de rubrique)')
                       for a in ['%I0.3.2','%M120','%MW1200:X3']]
        b.liens_il_simples=[LienDocumentaire('%I0.3.2','%M120',1),
                            LienDocumentaire('%M120','%MW1200:X3',2)]
        r={x.adresse:x for x in preparer_revue(b)}
        self.assertEqual(r['%MW1200:X3'].origine_potentielle,'%I0.3.2')
        self.assertEqual(r['%MW1200:X3'].statut,'À examiner — non validé')
        self.assertEqual(r['%MW1200:X3'].adresse_acquisition_topkapi,'')

    def test_symbole_xbt_avec_underscore(self):
        b=jeu()
        b.indices_symboles=[IndiceSymbole('%MW99','Buffer_xbt','',3)]
        x=next(x for x in preparer_revue(b) if x.adresse=='%MW99')
        self.assertIn('pas une preuve TOPKAPI',x.categorie)

    def test_csv_ne_execute_pas_formule_issue_de_commentaire(self):
        b=jeu()
        b.indices_symboles=[IndiceSymbole('%MW99','A','=HYPERLINK("http://exemple.invalid")',3)]
        with tempfile.TemporaryDirectory() as t:
            b.enregistrer(t)
            texte=(Path(t)/'revue_variables_pdf.csv').read_text(encoding='utf-8-sig')
            self.assertIn("'=HYPERLINK",texte)
            brute=(Path(t)/'revue_variables_pdf.json').read_text(encoding='utf-8')
            self.assertIn('=HYPERLINK',brute)

    def test_sortie_csv_complet(self):
        b=jeu()
        with tempfile.TemporaryDirectory() as p:
            b.enregistrer(p)
            f=Path(p)/'revue_variables_pdf.csv'
            self.assertTrue(f.exists())
            s=f.read_text(encoding='utf-8-sig')
            self.assertIn('adresse_acquisition_topkapi',s)
            self.assertIn('Buffer_xbt',s)
            self.assertTrue((Path(p)/'revue_variables_pdf.json').exists())

if __name__=='__main__':unittest.main()
