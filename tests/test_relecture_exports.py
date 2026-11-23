"""Relecture indépendante des exports (12/11/2026) : défauts constatés, démontrés puis corrigés.

Données entièrement synthétiques (lieu XTST). Ces tests ne qualifient aucun export : ils vérifient la robustesse
des fichiers produits (XML bien formé, colonnes intactes, octets reproductibles, pièces signalées).
"""
import hashlib
import os
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET
import zipfile

from genvar import chemins
from genvar import formats_control_expert as ce
from genvar import formats_topkapi as ft
from genvar.catalogue import Catalogue
from genvar.export_xlsx import ecrire_xlsx
from genvar.modele import Equipement
from genvar.session import RegleMetier, Session


def _session(mode="Neuf"):
    s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
    s.nouveau(False)
    if mode != "Neuf":
        s.definir("mode", mode)
    s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
    s.definir("automate", "M340"); s.ajouter_sous_ensemble("00")
    return s


def _neuf_adresse():
    s = _session()
    e = s.ajouter_equipement(Equipement("00", "PM", "01"))
    s.decider_propositions(e.ident, "retenir")
    p = s.plan_adressage(); s.appliquer_adressage(p.empreinte)
    return s, e


class Base(unittest.TestCase):
    def setUp(self):
        self.env = os.environ.get("SOREP_DATA_DIR")
        os.environ["SOREP_DATA_DIR"] = tempfile.mkdtemp()
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        if self.env is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.env


class TestControlExpert(Base):
    def test_caractere_de_controle_refuse_au_lieu_d_un_xsy_mal_forme(self):
        with self.assertRaises(ce.FormatInvalide):
            ce.xsy([ce.VariableCE("A", "%MW1", "INT", "fin\x01")], "P")
        with self.assertRaises(ce.FormatInvalide):
            ce.xsy([ce.VariableCE("A", "%MW1", "INT", "x")], "P", commentaire="ouvrage\x0b")
        s, e = _neuf_adresse()
        s.definir_textes(e.ident, s.variables()[0].cle, commentaire="Pompe\x01")
        chemin = os.path.join(self.d, "v.xsy")
        with self.assertRaises(RegleMetier):
            s.exporter_xsy(chemin)

    def test_xsy_echappe_les_caracteres_speciaux_et_se_relit(self):
        v = [ce.VariableCE("ET_A", "%I0.1.0", "EBOOL", 'Vanne & <ouverte> "x" ; été\tà')]
        texte = ce.xsy(v, 'P&<"', commentaire="Réservoir & <bâche>")
        racine = ET.fromstring(texte.encode("utf-8"))
        self.assertEqual(racine.find("contentHeader").get("name"), 'P&<"')
        self.assertEqual(racine.find("dataBlock/variables/comment").text, v[0].commentaire)

    def test_txt_refuse_tabulation_et_retour_ligne_qui_decaleraient_les_colonnes(self):
        for commentaire in ("a\tb", "a\nb", "a\rb"):
            with self.assertRaises(ce.FormatInvalide):
                ce.txt([ce.VariableCE("A", "%MW1", "INT", commentaire)])

    def test_txt_se_relit_a_l_identique_avec_point_virgule_et_accents(self):
        v = [ce.VariableCE("A", "%MW1", "INT", "Débit ; total & <x>")]
        chemin = os.path.join(self.d, "v.txt")
        with open(chemin, "w", encoding="utf-8", newline="") as f:
            f.write(ce.txt(v))
        self.assertEqual(ce.lire_txt(chemin), v)

    def test_nom_avec_signe_multiplication_ou_division_refuse(self):
        for nom in ("A×B", "A÷B"):
            with self.assertRaises(ce.FormatInvalide):
                ce.xsy([ce.VariableCE(nom, "%MW1", "INT", "")], "P")
        ce.xsy([ce.VariableCE("Débit", "%MW1", "INT", "")], "P")          # lettres accentuées : inchangé

    def test_xsy_deterministe_a_date_fixe(self):
        import datetime
        s, _ = _neuf_adresse()
        t = datetime.datetime(2026, 11, 12, 8, 5, 3)
        from genvar.export_xsy import contenu_xsy
        a = contenu_xsy(s.ouvrage, s.variables(), s.points(), maintenant=t)
        b = contenu_xsy(s.ouvrage, s.variables(), s.points(), maintenant=t)
        self.assertEqual(a, b)


class TestTopkapi(Base):
    def test_libelle_non_representable_refuse_proprement_sans_zip_vide(self):
        s, e = _neuf_adresse()
        s.declarer_protocole(True, 0)
        v = s.variables()[0]
        s.definir_textes(e.ident, v.cle, libelle="Niveau → haut")
        z = os.path.join(self.d, "t.zip")
        with self.assertRaises(RegleMetier) as ctx:
            s.exporter_topkapi(z)
        self.assertIn(v.nom, str(ctx.exception))
        self.assertFalse(os.path.exists(z))                   # aucun fichier partiel laissé

    def test_libelle_sur_deux_lignes_refuse_proprement(self):
        s, e = _neuf_adresse()
        s.declarer_protocole(True, 0)
        s.definir_textes(e.ident, s.variables()[0].cle, libelle="ligne1\nligne2")
        z = os.path.join(self.d, "t.zip")
        with self.assertRaises(RegleMetier):
            s.exporter_topkapi(z)
        self.assertFalse(os.path.exists(z))

    def test_erreur_d_encodage_nomme_le_point(self):
        with self.assertRaises(ft.FormatTopkapiInvalide) as ctx:
            ft.ecrire_octets([ft.PointTopkapi("XTST_A", "1", "2", "ok"), ft.PointTopkapi("XTST_B", "2", "2", "≥")])
        self.assertIn("XTST_B", str(ctx.exception))

    def test_archive_reproductible_octet_pour_octet(self):
        s, _ = _neuf_adresse()
        s.declarer_protocole(True, 1)
        a, b = os.path.join(self.d, "a.zip"), os.path.join(self.d, "b.zip")
        s.exporter_topkapi(a)
        time.sleep(2.1)                                       # résolution des dates zip : 2 s
        s.exporter_topkapi(b)
        with open(a, "rb") as fa, open(b, "rb") as fb:
            self.assertEqual(fa.read(), fb.read())

    def test_coherence_adresses_xsy_excel_topkapi(self):
        s, _ = _neuf_adresse()
        s.declarer_protocole(True, 1)
        z, x = os.path.join(self.d, "t.zip"), os.path.join(self.d, "v.xsy")
        s.exporter_topkapi(z)
        s.exporter_xsy(x)
        xsy = {v.nom: v.adresse for v in ce.lire(x) if v.nom}
        with zipfile.ZipFile(z) as f:
            pts = ft.lire_octets(f.read(next(n for n in f.namelist() if n.endswith(".$$t"))))
        self.assertTrue(pts)
        for p in pts:
            mot, bit = p.mot_bit
            self.assertEqual(xsy[p.mnemo], f"%MW{mot - 1}" + (f".{bit}" if bit is not None else ""))


class TestExcel(Base):
    def _xml_valides(self, chemin):
        with zipfile.ZipFile(chemin) as z:
            for nom in z.namelist():
                if nom.endswith(".xml") or nom.endswith(".rels"):
                    ET.fromstring(z.read(nom))                 # lève ParseError si mal formé

    def test_caractere_de_controle_ne_corrompt_pas_le_classeur(self):
        chemin = os.path.join(self.d, "c.xlsx")
        ecrire_xlsx(chemin, [("Feuille", ["A"], [["fin\x01 \x1f ok"], ["tab\tet\nligne"]], [10])])
        self._xml_valides(chemin)
        with zipfile.ZipFile(chemin) as z:
            texte = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        self.assertIn("ok", texte)
        self.assertIn("tab\tet", texte)                       # tabulation et retour ligne conservés

    def test_export_variables_avec_commentaire_saisi_reste_lisible(self):
        s, e = _neuf_adresse()
        s.definir_textes(e.ident, s.variables()[0].cle, commentaire="Pompe\x01 & <A>")
        chemin = os.path.join(self.d, "v.xlsx")
        s.exporter_excel(chemin)
        self._xml_valides(chemin)

    def test_nom_de_feuille_avec_apostrophe_dans_la_zone_de_filtre(self):
        chemin = os.path.join(self.d, "c.xlsx")
        ecrire_xlsx(chemin, [("Vue d'ensemble", ["A"], [["x"]], [10])])
        with zipfile.ZipFile(chemin) as z:
            classeur = z.read("xl/workbook.xml").decode("utf-8")
        self.assertIn("'Vue d''ensemble'!$A$1:$A$2", classeur)

    def test_classeur_reproductible_octet_pour_octet(self):
        s, _ = _neuf_adresse()
        a, b = os.path.join(self.d, "a.xlsx"), os.path.join(self.d, "b.xlsx")
        s.exporter_excel(a)
        time.sleep(2.1)
        s.exporter_excel(b)
        with open(a, "rb") as fa, open(b, "rb") as fb:
            self.assertEqual(hashlib.sha256(fa.read()).digest(), hashlib.sha256(fb.read()).digest())


class TestDossierRecette(Base):
    def test_pieces_omises_signalees_avec_motif_projet_neuf_sans_materiel(self):
        s, _ = _neuf_adresse()
        m = s.dossier_recette(os.path.join(self.d, "r.zip"))
        absentes = {p["fichier"]: p["motif"] for p in m["non_produites"]}
        self.assertIn("03_cartes_es.xlsx", absentes)
        self.assertTrue(absentes["03_cartes_es.xlsx"])

    def test_pieces_omises_signalees_avec_motif_projet_existant(self):
        s = _session("Existant")
        s.ajouter_equipement(Equipement("00", "MV", "01"))
        z = os.path.join(self.d, "r.zip")
        m = s.dossier_recette(z)
        absentes = {p["fichier"]: p["motif"] for p in m["non_produites"]}
        self.assertIn("05_variables_control_expert.xsy", absentes)
        self.assertIn("existant", absentes["05_variables_control_expert.xsy"].lower())
        with zipfile.ZipFile(z) as f:
            noms = set(f.namelist())
            sommaire = f.read("00_sommaire.html").decode("utf-8")
            for p in m["pieces"]:
                self.assertEqual(hashlib.sha256(f.read(p["fichier"])).hexdigest(), p["sha256"])
        self.assertNotIn("05_variables_control_expert.xsy", noms)
        self.assertIn("05_variables_control_expert.xsy", sommaire)
        self.assertEqual(noms, {"00_sommaire.html"} | {p["fichier"] for p in m["pieces"]})

    def test_export_topkapi_partiel_signale_dans_le_sommaire(self):
        s = _session()
        e = s.ajouter_equipement(Equipement("00", "FT", "01"))           # débit REAL : exclu du .$$t
        s.decider_propositions(e.ident, "retenir")
        p = s.plan_adressage(); s.appliquer_adressage(p.empreinte)
        s.declarer_protocole(True, 0)
        z = os.path.join(self.d, "r.zip")
        m = s.dossier_recette(z)
        tk = next(p for p in m["pieces"] if p["fichier"] == "06_topkapi.zip")
        self.assertIn("exclu", tk["remarque"])
        with zipfile.ZipFile(z) as f:
            self.assertIn(tk["remarque"], f.read("00_sommaire.html").decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
