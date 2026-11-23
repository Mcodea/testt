"""Tests contrôlés de lecture documentaire PDF. Ne simulent PAS un vrai dossier PL7 complet."""
import tempfile
import unittest
from pathlib import Path
from genvar.analyse_pdf_pl7 import analyser_pdf

try:
    import fitz
except ImportError:
    fitz = None


@unittest.skipIf(fitz is None, 'PyMuPDF non installé')
class TestAnalysePDFPL7(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pdf = Path(self.tmp.name) / 'exemple_fictif_pl7.pdf'

    def creer_pdf(self):
        d = fitz.open()
        for lines in [
            ['DOSSIER D’APPLICATION PL7 - PROJET FICTIF', 'SOMMAIRE', '1 Programme', '2 Références croisées', '3 Variables'],
            ['PROGRAMME - MAST POST', '(* Exemple fictif: vanne fermée *)', 'LD  %I0.3.2', 'ST  %M120', 'LD  %M120', 'ST  %MW1200:X3'],
            ['REFERENCES CROISEES', '%I0.3.2  FC_V3_FER  MAST-PRL  R', '%M120  V3_FER  MAST-POST  W', '%MW1200:X3  TS_V3_FER  MAST-POST  W'],
            ['VARIABLES', '%I0.3.2  FC_V3_FER   Fin de course vanne fermée', '%M120  V3_FER  Mémoire de position', '%MW1200:X3  TS_V3_FER  État pour échange', '%MW100  A  Réserve', '%MW101  B  Réserve', '%MW102  C  Réserve'],
        ]:
            p = d.new_page()
            for j,line in enumerate(lines):
                p.insert_text((50, 60 + 22*j), line, fontsize=11, fontname='helv')
        d.save(self.pdf)
        d.close()

    def test_lecture_pdf_avec_indices_et_export(self):
        self.creer_pdf()
        resultat = analyser_pdf(self.pdf)
        self.assertEqual(resultat.pages,4)
        self.assertEqual(resultat.pages_texte,4)
        self.assertIn('%MW1200:X3',resultat.adresses_uniques)
        self.assertIn('%I0.3.2',resultat.adresses_uniques)
        self.assertTrue(any(o.page==3 and o.usage=='W' and o.adresse=='%M120' for o in resultat.occurrences))
        self.assertTrue(any(x['debut']=='%MW100' and x['fin']=='%MW102' for x in resultat.zones_memoires_candidates))
        self.assertEqual(resultat.pages_references_croisees,[3])
        self.assertEqual([(x.origine,x.destination) for x in resultat.liens_il_simples],
                         [('%I0.3.2','%M120'),('%M120','%MW1200:X3')])
        dossier=Path(self.tmp.name)/'rapport'
        resultat.enregistrer(dossier)
        self.assertTrue((dossier/'analyse_pdf.json').is_file())
        self.assertTrue((dossier/'occurrences_pdf.csv').is_file())
        contenu=(dossier/'bilan_pdf.txt').read_text(encoding='utf8')
        self.assertIn('AUCUNE correspondance fonctionnelle',contenu)

    def test_pdf_scanné_declenche_avertissement(self):
        d=fitz.open(); d.new_page(); d.save(self.pdf); d.close()
        res=analyser_pdf(self.pdf)
        self.assertEqual(res.occurrences,[])
        self.assertTrue(any('sans couche texte' in msg for msg in res.avertissements))

    def test_bad_pdf(self):
        self.pdf.write_bytes(b'pas un PDF')
        with self.assertRaises(Exception):
            analyser_pdf(self.pdf)


def _pages_pymupdf_reference(chemin):
    """Lecture de référence par PyMuPDF (outil de développement, AGPL-3.0, NON livré) : ancien comportement."""
    doc = fitz.open(str(chemin))
    try:
        return [doc.load_page(i).get_text('text', sort=True) for i in range(len(doc))]
    finally:
        doc.close()


@unittest.skipIf(fitz is None, 'PyMuPDF (référence de développement) non installé')
class TestEquivalenceMoteurs(unittest.TestCase):
    """23/11/2026 : pdfminer.six (MIT) remplace PyMuPDF (AGPL-3.0) dans le programme livré. L'inventaire produit
    doit rester identique à celui de l'ancien lecteur sur les PDF de référence fictifs."""

    def test_inventaires_identiques_sur_les_pdf_de_reference(self):
        from dataclasses import asdict
        racine = Path(__file__).resolve().parents[1] / 'validation' / 'pdf_pl7'
        pdfs = sorted(racine.glob('*.pdf'))
        self.assertGreaterEqual(len(pdfs), 2)
        for f in pdfs:
            with self.subTest(pdf=f.name):
                self.assertEqual(asdict(analyser_pdf(f)), asdict(analyser_pdf(f, extraire=_pages_pymupdf_reference)))


class TestAucunPyMuPDFLivre(unittest.TestCase):
    def test_programme_livre_sans_pymupdf(self):
        racine = Path(__file__).resolve().parents[1]
        for dossier in ('genvar', 'sorep_web'):
            for f in (racine / dossier).rglob('*.py'):
                texte = f.read_text(encoding='utf-8')
                with self.subTest(fichier=str(f.relative_to(racine))):
                    self.assertNotIn('import fitz', texte)
                    self.assertNotIn('import pymupdf', texte.lower())
        verrou = (racine / 'requirements-runtime.lock').read_text(encoding='utf-8').lower()
        self.assertNotIn('pymupdf==', verrou)
        self.assertIn('pdfminer.six==', verrou)


if __name__=='__main__': unittest.main()
