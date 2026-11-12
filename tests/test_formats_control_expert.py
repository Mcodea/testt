"""Formats Control Expert (XSY, TXT, SCY) : structure reprise des exports réels V14.1 du 9 novembre 2026.

Les échantillons ci-dessous sont synthétiques (aucune donnée de client) mais reproduisent exactement la
mise en forme constatée : tabulations, CRLF, ordre des attributs, voies de réserve sans nom.
"""
import os
import tempfile
import unittest

from genvar import chemins
from genvar import formats_control_expert as f
from genvar.catalogue import Catalogue
from genvar.modele import Equipement
from genvar.session import Session

TXT = ('ET_RV01HV01_FDC_OUV\t%I0.1.0\tEBOOL\t"VANNE ENTREE OUVERTE"\t\r\n'
       '\t%I0.1.1\tEBOOL\t" RESERVE "\t\r\n'
       'Sn_niv_bas\t%KW10\tINT\t"Seuil niveau bas"\t(140)\r\n'
       'Ts_rv01lt01_def\t%MW14.3\tBOOL\t"NIVEAU DEFAUT"\t\r\n')
SCY = ("[HEADER]\nSENDER = 'Schneider Automation Control Expert V14.1'\nVAR_GLOBAL\n"
       "ET_RV01HV01_FDC_OUV AT %I0.1.0 : EBOOL (*VANNE ENTREE OUVERTE*);\n"
       "AT %I0.1.1 : EBOOL (* RESERVE *);\n"
       "Sn_niv_bas AT %KW10 : INT (*Seuil niveau bas*) := (140);\n"
       "Ts_rv01lt01_def AT %MW14.3 : BOOL (*NIVEAU DEFAUT*);\nEND_VAR\n")


class TestFormats(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def ecrire(self, nom, texte):
        chemin = os.path.join(self.d, nom)
        with open(chemin, "w", encoding="utf-8", newline="") as h:
            h.write(texte)
        return chemin

    def test_txt_lecture_et_reecriture_identique(self):
        v = f.lire(self.ecrire("v.txt", TXT))
        self.assertEqual([(x.nom, x.adresse, x.type, x.valeur_init) for x in v][1:3],
                         [("", "%I0.1.1", "EBOOL", ""), ("Sn_niv_bas", "%KW10", "INT", "140")])
        self.assertEqual(f.txt(v), TXT)

    def test_scy_et_xsy_coherents(self):
        scy = f.lire(self.ecrire("v.scy", SCY))
        x = f.xsy(scy, "ATMSRV01", commentaire="Réservoir d'essai")
        xsy = f.lire(self.ecrire("v.xsy", x))
        cle = lambda v: (v.nom, v.adresse, v.type, v.commentaire, v.valeur_init)
        self.assertEqual([cle(a) for a in scy], [cle(b) for b in xsy])
        self.assertEqual(scy[3].adresse, "%MW14.3")

    def test_mise_en_forme_xsy(self):
        x = f.xsy([f.VariableCE("ET_A", "%I0.1.0", "EBOOL", "A"), f.reserve("%I0.1.1", "EBOOL")], "P")
        lignes = x.split("\r\n")
        self.assertNotIn("\n", x.replace("\r\n", ""))                            # CRLF uniquement
        self.assertIn('content="Fichier source variables" DTDVersion="41"', lignes[2])
        self.assertEqual(lignes[6], '\t\t<variables name="ET_A" typeName="EBOOL" topologicalAddress="%I0.1.0">')
        self.assertEqual(lignes[9], '\t\t<variables topologicalAddress="%I0.1.1" typeName="EBOOL">')

    def test_refus_propres(self):
        with self.assertRaises(f.FormatInvalide):
            f.lire(self.ecrire("v.xvm", "<XVMExchangeFile><crypted/>"))           # chiffré
        with self.assertRaises(f.FormatInvalide):
            f.lire(self.ecrire("v.xsy", "<pas_du_xsy/>"))
        with self.assertRaises(f.FormatInvalide):
            f.xsy([f.VariableCE("NOM AVEC ESPACE", "%I0.1.0", "EBOOL", "")], "P")
        with self.assertRaises(f.FormatInvalide):
            f.xsy([f.VariableCE("A", "%I0.1.0", "EBOOL", ""), f.VariableCE("a", "%I0.1.1", "EBOOL", "")], "P")
        with self.assertRaises(f.FormatInvalide):
            f.lire(self.ecrire("v.txt", "une seule colonne\r\n"))


class TestExportOuvrage(unittest.TestCase):
    def test_es_et_reserves_par_carte(self):
        os.environ["SOREP_DATA_DIR"] = tempfile.mkdtemp()
        s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s.nouveau(False)
        s.definir("lieu", "ATMS"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
        s.definir("automate", "M340"); s.ajouter_sous_ensemble("00")
        s.ajouter_equipement(Equipement("00", "OD", "01"))
        s.valider_contenu_es([(p.ident_eq, p.cle) for p in s.points()])
        s.appliquer_materiel("16_4")
        s.implanter_es()
        chemin = os.path.join(os.environ["SOREP_DATA_DIR"], "es.xsy")
        n = s.exporter_xsy_es(chemin)
        v = f.lire(chemin)
        et = [x for x in v if x.adresse.startswith("%I0.1.")]
        self.assertEqual(len(et), 16)                                   # toutes les voies de la carte
        self.assertEqual(sum(1 for x in et if x.nom), n)
        self.assertEqual([x.adresse for x in et], [f"%I0.1.{i}" for i in range(16)])
        self.assertTrue(all(x.commentaire == " RESERVE " for x in et if not x.nom))
        t = os.path.join(os.environ["SOREP_DATA_DIR"], "es.txt")
        s.exporter_txt_es(t)
        self.assertEqual([(x.nom, x.adresse) for x in f.lire(t)], [(x.nom, x.adresse) for x in v])


if __name__ == "__main__":
    unittest.main()
