"""Parcours PDF -> revue : exemple DE CONTRÔLE, PAS le document HABILIS original.

Mise en page inspirée des imprimés PL7 accessibles publiquement, données
strictement fictives. Le test ne mesure pas la qualité sur un vrai programme.
"""
import tempfile
import unittest
from pathlib import Path
from genvar.analyse_pdf_pl7 import analyser_pdf
from genvar.revue_documentaire import preparer_revue
try:
    import fitz
except ImportError:
    fitz = None

@unittest.skipIf(fitz is None, 'PyMuPDF non installé')
class TestPDFVersRevue(unittest.TestCase):
    def test_programme_et_pupitre_local_vers_revue(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/'controle_pupitre_fictif.pdf'
            d=fitz.open()
            pages = [
                ['MAST-POST', 'OPERATE', '%MW5:=%IW0.2/10',
                 'Liste de Variables utilisées dans le rung :', 'REPERE','SYMBOLE','COMMENTAIRE',
                 '%IW0.2','SONDE1','Mesure capteur', '%MW5','TEMP','Temperature calculee',
                 'Folio : 4.2.3 - 1'],
                ['MAST-POST', 'OPERATE','%MW99:=4',
                 'Liste de Variables utilisées dans le rung :', 'REPERE','SYMBOLE','COMMENTAIRE',
                 '%MW99','Buffer_xbt','Table gestion XBT', 'Folio : 4.2.3 - 2'],
            ]
            for lines in pages:
                page=d.new_page()
                for i,line in enumerate(lines):
                    page.insert_text((45,70+i*21),line,fontsize=11)
            d.save(f);d.close()
            r=analyser_pdf(f)
            r.enregistrer(Path(t)/'sortie')
            lignes={x.adresse:x for x in preparer_revue(r)}
            self.assertIn('%IW0.2',lignes['%MW5'].origine_potentielle)
            self.assertIn('pupitre/IHM',lignes['%MW99'].categorie)
            self.assertEqual(lignes['%MW99'].adresse_acquisition_topkapi,'')
            self.assertTrue((Path(t)/'sortie'/'revue_variables_pdf.csv').exists())
            self.assertIn('non validé',lignes['%MW5'].statut)

if __name__ == '__main__': unittest.main()
