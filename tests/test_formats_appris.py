"""Formats d'export appris (22/11/2026), lot 1 : liste des E/S physiques, OGIAS ouvert à tout constructeur.

Exemples FICTIFS imitant la forme des exports de plusieurs outils (aucune donnée réelle, format d'aucun produit
garanti) : rack.emplacement.voie, octet.bit avec guillemets et lignes avant l'en-tête, forme d'adresse inconnue.
"""
import base64
import csv
import io
import os
import tempfile
import unittest
import zipfile

from genvar import formats_appris as fa
from sorep_web.serveur import Application, RegleMetier

EXEMPLE_RACK = ("Nom;Adresse;Type;Commentaire\r\n"
                "DI_POMPE_1;%I0.3.0;EBOOL;Marche pompe 1\r\n"
                "AI_NIVEAU;%IW0.4.0;INT;Niveau bâche\r\n").encode("cp1252")
EXEMPLE_OCTET = ('// Table des E/S\n// Projet fictif\n'
                 '"Name","Path","Data Type","Logical Address","Comment","Retain"\n'
                 '"Marche_P1","Table","Bool","%I4.0","Marche","False"\n'
                 '"Defaut_P1","Table","Bool","%I4.1","Défaut","False"\n'
                 '"Niveau","Table","Int","%IW64","Niveau","False"\n').encode("utf-8")
EXEMPLE_INCONNU = b"Tag|Canal|Texte\nP1_RUN|X1:3|Marche\nP1_DEF|X1:4|Defaut\n"


def b64(octets):
    return base64.b64encode(octets).decode()


class Base(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-formats-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        app = self.app = Application()
        app.nouveau({"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.fiche_ouvrage({"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "33", "libelle": "Essai formats appris",
            "automate": "Sch - M580", "revision": "A"}})
        for t, n in (("PM", "01"), ("LT", "02")):
            i = app.ajouter_equipement({"type": t, "numero": n, "se": "00"})["ident"]
            app.decider_proposition({"ident_eq": i, "decision": "retenir"})
        s = self.s = app.s
        s.valider_contenu_es([(p.ident_eq, p.cle) for p in s.points()])
        s.appliquer_materiel()
        s.implanter_es()
        self.points = fa.points_exportes(s)

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def apprendre(self, octets, logiciel, nom, reglages=None, fichier="exemple.csv"):
        r = self.app.formats_appris_action({"action": "enregistrer", "fichier": fichier, "contenu": b64(octets),
                                            "nature": "es_physiques", "logiciel": logiciel, "nom": nom,
                                            "reglages": reglages or {}})
        return fa.trouver(r["ident"])


class TestAnalyse(Base):
    def test_structure_rack_emplacement_voie(self):
        a = fa.analyser(EXEMPLE_RACK, "es.csv")
        self.assertEqual((a["encodage"], a["separateur"], a["fin_ligne"], a["guillemets"], a["entete_index"]),
                         ("cp1252", ";", "\r\n", False, 0))
        self.assertEqual([c["champ"] for c in a["colonnes"]], ["nom", "adresse", "type", "libelle"])
        self.assertEqual(a["adresse"]["reconnue"], "rack.emplacement.voie")
        self.assertEqual(a["types"], {"ET": "EBOOL", "ST": "EBOOL", "EA": "INT", "SA": "INT"})
        self.assertEqual(a["alertes"], [])

    def test_structure_octet_bit_guillemets_et_preambule(self):
        a = fa.analyser(EXEMPLE_OCTET, "tags.csv")
        self.assertEqual((a["separateur"], a["guillemets"], a["entete_index"], a["fin_ligne"]), (",", True, 2, "\n"))
        self.assertEqual(a["preambule"], ["// Table des E/S", "// Projet fictif"])
        self.assertEqual({c["titre"]: c["champ"] for c in a["colonnes"]},
                         {"Name": "nom", "Path": "fixe", "Data Type": "type", "Logical Address": "adresse",
                          "Comment": "libelle", "Retain": "fixe"})
        self.assertEqual(a["adresse"]["reconnue"], "octet.bit")
        self.assertEqual(a["adresse"]["gabarits"]["ET"], "%I{OCTET}.{BIT}")
        self.assertEqual(a["adresse"]["gabarits"]["EA"], "%IW{MOT}")

    def test_forme_inconnue_signalee_et_jamais_devinee(self):
        a = fa.analyser(EXEMPLE_INCONNU, "x.txt")
        self.assertEqual(a["separateur"], "|")
        self.assertEqual([c["champ"] for c in a["colonnes"]], ["nom", "voie", "libelle"])
        self.assertTrue(any("Aucune colonne d'adresse" in x for x in a["alertes"]))
        with self.assertRaises(fa.FormatRefuse):                      # une colonne d'adresse est exigée
            fa.definir(a, {})
        d = fa.definir(a, {"colonnes": ["nom", "adresse", "libelle"]})
        self.assertEqual(d["adresse"]["gabarits"]["ET"], "{ADRESSE}")  # recopie de l'adresse d'OGIAS, signalée

    def test_refus_motives(self):
        cas = {b"": "vide", b"<?xml version='1.0'?><a/>": "XML", b"une seule ligne\n": "au moins",
               b"a b c\nd e f\n": "Séparateur", b"\x00\x01binaire": "binaire"}
        for octets, attendu in cas.items():
            with self.subTest(octets=octets), self.assertRaises(fa.FormatRefuse) as ctx:
                fa.analyser(octets)
            self.assertIn(attendu, str(ctx.exception))
        a = fa.analyser(EXEMPLE_RACK)
        for reglages in ({"colonnes": ["nom", "nom", "type", "libelle"]}, {"colonnes": ["nom", "adresse", "inconnu", "libelle"]},
                         {"adresse": {"gabarits": {"ET": "%I{XYZ}", "ST": "a", "EA": "a", "SA": "a"}}},
                         {"adresse": {"gabarits": {n: "{ADRESSE}" for n in "ET ST EA SA".split()}, "taille": 0}}):
            with self.subTest(reglages=reglages), self.assertRaises(fa.FormatRefuse):
                fa.definir(a, reglages)


class TestProduction(Base):
    def test_rack_emplacement_voie_reproduit_la_forme_d_ogias(self):
        f = self.apprendre(EXEMPLE_RACK, "Control Expert", "E/S rack fictif")
        nom, octets, statut = fa.exporter(f, self.s)
        texte = octets.decode("cp1252")
        lignes = texte.split("\r\n")
        self.assertEqual(lignes[0], "Nom;Adresse;Type;Commentaire")
        self.assertEqual(len([x for x in lignes[1:] if x]), len(self.points))
        attendu = {p.nom: p.adresse for p in self.points}
        for x in lignes[1:]:
            if x:
                n, a, t, _ = x.split(";")
                self.assertEqual(a, attendu[n])
                self.assertIn(t, ("EBOOL", "INT"))
        self.assertTrue(texte.endswith("\r\n"))
        self.assertIn("NON QUALIFIÉ", statut)
        self.assertTrue(nom.endswith(".csv"))

    def test_octet_bit_conversion_guillemets_et_valeurs_fixes(self):
        f = self.apprendre(EXEMPLE_OCTET, "Sch - M580", "E/S octet fictif",
                           {"adresse": {"gabarits": {"ET": "%I{OCTET}.{BIT}", "ST": "%Q{OCTET}.{BIT}", "EA": "%IW{MOT}",
                                                     "SA": "%QW{MOT}"}, "decalage": 0, "taille": 4}})
        texte = fa.exporter(f, self.s)[1].decode("utf-8")
        lignes = texte.split("\n")
        self.assertEqual(lignes[:3], ["// Table des E/S", "// Projet fictif",
                                      '"Name","Path","Data Type","Logical Address","Comment","Retain"'])
        lues = {r[0]: r for r in csv.reader(io.StringIO("\n".join(lignes[3:])))}
        for p in self.points:
            r = lues[p.nom]
            emplacement, voie = int(p.module.split(".")[1]), int(p.voie)
            attendu = f"%I{emplacement * 4 + voie // 8}.{voie % 8}" if p.point == "ET" else f"%IW{emplacement * 4 + voie * 2}"
            self.assertEqual(r[3], attendu)
            self.assertEqual((r[1], r[5]), ("Table", "False"))          # valeurs fixes de l'exemple
            self.assertEqual(r[2], "Bool" if p.point == "ET" else "Int")  # table de types apprise
        self.assertTrue(all(x.startswith('"') for x in lignes[3:] if x))

    def test_adresses_en_double_apres_conversion_refusees(self):
        f = self.apprendre(EXEMPLE_OCTET, "Sch - M580", "E/S octet trop serré",
                           {"adresse": {"gabarits": {"ET": "%I{EMPLACEMENT}", "ST": "%Q{EMPLACEMENT}",
                                                     "EA": "%IW{EMPLACEMENT}", "SA": "%QW{EMPLACEMENT}"}}})
        with self.assertRaises(fa.FormatRefuse) as ctx:
            fa.exporter(f, self.s)
        self.assertIn("même adresse", str(ctx.exception))

    def test_valeur_contenant_le_separateur_reste_relue_exactement(self):
        f = self.apprendre(EXEMPLE_RACK, "Control Expert", "E/S rack fictif")
        p = self.points[0]
        eq = self.s.ouvrage.equipement(p.ident_eq)
        meta = dict(eq.es_meta.get(p.cle, {}))
        meta["designation"] = 'Marche; "pompe" 1'
        eq.es_meta[p.cle] = meta
        texte = fa.exporter(f, self.s)[1].decode("cp1252")
        self.assertIn('"Marche; ""pompe"" 1"', texte)
        self.assertEqual(fa.relire(f["definition"], texte, self.s), [])

    def test_relecture_detecte_un_fichier_altere(self):
        f = self.apprendre(EXEMPLE_RACK, "Control Expert", "E/S rack fictif")
        texte = fa.produire_texte(f["definition"], self.s)
        self.assertEqual(fa.relire(f["definition"], texte, self.s), [])
        self.assertTrue(fa.relire(f["definition"], texte.replace("Nom;", "Name;", 1), self.s))
        self.assertTrue(fa.relire(f["definition"], texte.replace("%I0.", "%I9.", 1), self.s))
        self.assertTrue(fa.relire(f["definition"], texte.rsplit("\r\n", 2)[0] + "\r\n", self.s))

    def test_caractere_hors_encodage_refuse(self):
        f = self.apprendre(EXEMPLE_RACK, "Control Expert", "E/S rack fictif")
        p = self.points[0]
        eq = self.s.ouvrage.equipement(p.ident_eq)
        eq.es_meta[p.cle] = {**eq.es_meta.get(p.cle, {}), "designation": "Pompe → bâche"}
        with self.assertRaises(fa.FormatRefuse) as ctx:
            fa.exporter(f, self.s)
        self.assertIn("cp1252", str(ctx.exception))


class TestQualificationEtChoix(Base):
    def test_qualification_puis_controle_automatique(self):
        f = self.apprendre(EXEMPLE_RACK, "Control Expert", "E/S rack fictif")
        self.assertFalse(fa.qualifie(f))
        for version, cr in (("", "Import réussi dans le logiciel"), ("v15", "ok")):
            with self.subTest(version=version), self.assertRaises(fa.FormatRefuse):
                fa.qualifier(f["ident"], version, cr)
        f = fa.qualifier(f["ident"], "V15.3", "Fichier importé dans le logiciel cible, 4 E/S créées sans erreur.")
        self.assertTrue(fa.qualifie(f))
        self.assertIn("Conforme au format qualifié (Control Expert V15.3)", fa.exporter(f, self.s)[2])
        f["definition"]["separateur"] = ","                     # structure différente : la qualification ne suit pas
        self.assertFalse(fa.qualifie(f))
        f = fa.retirer_qualification(f["ident"])
        self.assertIsNone(f["qualification"])

    def test_format_retenu_selon_l_automate_de_l_ouvrage(self):
        ce = self.apprendre(EXEMPLE_RACK, "control expert", "E/S Control Expert")
        tia = self.apprendre(EXEMPLE_OCTET, "TIA Portal", "E/S TIA fictif")
        self.assertEqual(fa.retenu(ce, self.s.ouvrage), (True, ""))
        ok, motif = fa.retenu(tia, self.s.ouvrage)
        self.assertFalse(ok)
        self.assertIn("Sch - M580 / Control Expert", motif)
        _, octets = self.app.exporter({"quoi": "generation_groupee", "familles": "automate"})
        z = zipfile.ZipFile(io.BytesIO(octets))
        journal = {r["Pièce"]: r for r in csv.DictReader(io.StringIO(z.read("00_journal.csv").decode("utf-8-sig")),
                                                         delimiter=";")}
        self.assertEqual(journal["Format appris « E/S Control Expert »"]["État"], "produit")
        self.assertIn("non qualifié", journal["Format appris « E/S Control Expert »"]["Motif ou remarque"])
        self.assertEqual(journal["Format appris « E/S TIA fictif »"]["État"], "non retenu")
        self.assertIn(journal["Format appris « E/S Control Expert »"]["Fichier"], z.namelist())


class TestApi(Base):
    def test_parcours_complet(self):
        a = self.app.formats_appris_action({"action": "analyser", "fichier": "tags.csv", "contenu": b64(EXEMPLE_OCTET)})
        self.assertEqual(a["analyse"]["entete_index"], 2)
        r = self.app.formats_appris_action({"action": "apercu", "fichier": "tags.csv", "contenu": b64(EXEMPLE_OCTET),
                                            "reglages": {}})
        self.assertEqual(r["apercu"][2], '"Name","Path","Data Type","Logical Address","Comment","Retain"')
        self.assertEqual((r["refus"], r["ecarts"]), ([], []))
        r = self.app.formats_appris_action({"action": "enregistrer", "fichier": "tags.csv", "contenu": b64(EXEMPLE_OCTET),
                                            "nature": "es_physiques", "logiciel": "Control Expert", "nom": "E/S essai"})
        f = next(x for x in r["formats"] if x["ident"] == r["ident"])
        self.assertTrue(f["retenu"])
        self.assertTrue(f["controle"]["pret"])
        self.assertIn("NON QUALIFIÉ", f["controle"]["statut"])
        self.assertEqual([x["export"] for x in r["livres"]], ["es_xsy", "es_txt"])
        nom, octets = self.app.exporter({"quoi": "format_appris", "ident": r["ident"]})
        self.assertTrue(octets.startswith(b"// Table des E/S"))
        with self.assertRaises(RegleMetier):                                   # nom déjà pris
            self.app.formats_appris_action({"action": "enregistrer", "fichier": "t.csv", "contenu": b64(EXEMPLE_OCTET),
                                            "nature": "es_physiques", "logiciel": "X1", "nom": "e/s ESSAI"})
        r = self.app.formats_appris_action({"action": "qualifier", "ident": f["ident"], "version": "V16",
                                            "compte_rendu": "Import réel réussi, toutes les E/S créées."})
        self.assertTrue(next(x for x in r["formats"] if x["ident"] == f["ident"])["qualifie"])
        r = self.app.formats_appris_action({"action": "supprimer", "ident": f["ident"]})
        self.assertEqual(r["formats"], [])
        with self.assertRaises(RegleMetier):
            self.app.exporter({"quoi": "format_appris", "ident": f["ident"]})

    def test_ouvrage_inchange(self):
        chemin = os.path.join(self.donnees.name, "essai.ouvrage.json")
        self.s.enregistrer(chemin)
        avant = open(chemin, "rb").read()
        f = self.apprendre(EXEMPLE_RACK, "Control Expert", "E/S rack fictif")
        self.app.formats_appris_web({})
        self.app.exporter({"quoi": "format_appris", "ident": f["ident"]})
        self.assertEqual(open(chemin, "rb").read(), avant)


if __name__ == "__main__":
    unittest.main()
