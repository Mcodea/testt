"""Essais sur mise en forme PL7 inspirée des dossiers imprimés publics.

Ce fichier n'est pas le PDF HABILIS original ; aucun essai original n'est revendiqué.
"""
import tempfile
from pathlib import Path
import unittest
from genvar.analyse_pdf_pl7 import (
    _rubrique, RE_ADDR, analyser_pdf, tracer_origines, affectations_depuis_texte,
)
try:
    import fitz
except ImportError:
    fitz=None


class TestAnalysePL7Texte(unittest.TestCase):
    def test_folio_et_sommaire(self):
        self.assertEqual(_rubrique('SOMMAIRE\n5 Références croisées........7p\n6 Variables........7p'), 'Sommaire')
        self.assertEqual(_rubrique('TABLEAU DES ADRESSES\nAuteur : X\nFolio : 5 - 1'), 'Références croisées (indice de rubrique)')
        self.assertEqual(_rubrique('SYMBOLES\nAuteur : X\nFolio : 6 - 1'), 'Variables (indice de rubrique)')
        self.assertEqual(_rubrique('MAST-POST\nFolio : 4.2.3 - 2'), 'Programme (indice de rubrique)')

    def test_variantes_adresses(self):
        texte='%IW0.2 %QW0.10 %X13.T %MW100:X3 %TM0.Q %MN6.R %DR3'
        self.assertEqual([m.group() for m in RE_ADDR.finditer(texte)], texte.split())

    def test_operate_expressions(self):
        texte=('MAST-POST\nOPERATE\n%MW5:=%IW0.2/10\n'
               'OPERATE\n%MW4:=%MW2-(%X13.T/600)\n'
               'OPERATE\n%MW104:=%MW99\n'
               'OPERATE\n%MW104:=%MW99  | Liste de Variables utilisées dans le rung :\n')
        a=affectations_depuis_texte(texte,43,'Programme (indice de rubrique)','MAST-POST')
        self.assertEqual(len(a),3)  # doublon de texte imprimé exclu
        self.assertEqual(a[0].destination,'%MW5')
        self.assertEqual(a[0].dependances,['%IW0.2'])
        self.assertEqual(a[1].dependances,['%MW2','%X13.T'])
        self.assertEqual(a[2].dependances,['%MW99'])
        self.assertEqual(affectations_depuis_texte(texte,2,'Références croisées (indice de rubrique)'),[])


@unittest.skipIf(fitz is None,'PyMuPDF non installé')
class TestAnalysePL7Document(unittest.TestCase):
    def test_document_pages_et_traces(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/'controle_style_pl7.pdf'
            d=fitz.open()
            pages=[
                ['SOMMAIRE','5 Références croisées................7p','6 Variables................7p'],
                ['MAST-PRL','OPERATE','%MW5:=%IW0.2/10','OPERATE','%MW104:=%MW99','Folio : 4.2.1 - 1'],
                ['MAST-POST','OPERATE','%MW99:=%I1.2','Folio : 4.2.3 - 1'],
                ['SYMBOLE REPERE COMMENTAIRE','%MW99 Buffer_xbt buffer opérateur','Folio : 6 - 1'],
                ['REFERENCES CROISEES','%MW99 MAST-POST R','Folio : 5 - 1'],
            ]
            for lines in pages:
                page=d.new_page()
                for j,line in enumerate(lines):
                    page.insert_text((40,55+25*j),line,fontsize=11)
            d.save(f);d.close()
            r=analyser_pdf(f)
            self.assertEqual(len(r.affectations_documentaires),3)
            self.assertEqual(r.pages_references_croisees,[5])
            self.assertIn('%IW0.2',r.adresses_uniques)
            trace=tracer_origines(r,'%MW104')
            self.assertEqual(len(trace),1)
            self.assertEqual(trace[0]['chaine'],['%MW104','%MW99','%I1.2'])
            self.assertEqual([p['page'] for p in trace[0]['preuves']],[2,3])
            dossier=Path(t)/'rapport';r.enregistrer(dossier)
            self.assertTrue((dossier/'affectations_pdf.csv').is_file())
            self.assertIn('OPERATE',(dossier/'bilan_pdf.txt').read_text(encoding='utf8'))


if __name__=='__main__':
    unittest.main()

class TestSymbolesImprimes(unittest.TestCase):
    def test_tableau_par_cellules_et_variables_sans_symbole(self):
        from genvar.analyse_pdf_pl7 import symboles_depuis_texte
        texte = '''MAST-PRL
        Liste de Variables utilisées dans le rung :
        REPERE
        SYMBOLE
        COMMENTAIRE
        %I1.3
        Maint_op
        partie opérative en position maintenance
        %MW107:X4
        %I1.8
        Celllule
        détecteur niveau
        Auteur : PhB
        Folio : 4.2.1 - 1'''
        obs = symboles_depuis_texte(texte,2,'Programme (indice de rubrique)')
        self.assertEqual([(x.adresse,x.symbole) for x in obs],
                         [('%I1.3','Maint_op'),('%I1.8','Celllule')])
        self.assertEqual(obs[0].commentaire,'partie opérative en position maintenance')
        self.assertEqual(symboles_depuis_texte(texte,2,'Sommaire'),[])

class TestSymbolesInline(unittest.TestCase):
    def test_tableau_variable_meme_ligne(self):
        from genvar.analyse_pdf_pl7 import symboles_depuis_texte
        texte = 'VARIABLES\n%MW10 TEMP_C Valeur calculee\n%MW11 TEMP_CX100 Valeur mise a echelle'
        s = symboles_depuis_texte(texte, 5, 'Variables (indice de rubrique)')
        self.assertEqual([(v.adresse,v.symbole) for v in s],
                         [('%MW10','TEMP_C'),('%MW11','TEMP_CX100')])
