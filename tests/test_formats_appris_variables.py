"""Formats d'export appris (22/11/2026), lot 2 : télétransmission (chaque supervision) et IHM.

Les deux natures exportent les variables d'échange de l'ouvrage. Exemples FICTIFS (format d'aucun produit garanti) :
adresses %MW mot.bit, registre numérique avec décalage Modbus, valeurs d'alarme et d'accès apprises.
"""
import base64
import csv
import io
import os
import tempfile
import unittest
import zipfile

from genvar import adressage
from genvar import formats_appris as fa
from sorep_web.serveur import Application, RegleMetier

SUPERVISION_MW = ("Tag;Address;DataType;Description;Alarm;Access\r\n"
                  "P1_RUN;%MW100.0;BOOL;Pompe 1 en marche;0;R\r\n"
                  "P1_FAULT;%MW100.1;BOOL;Pompe 1 défaut;1;R\r\n"
                  "V1_OPEN_CMD;%MW200.0;BOOL;Vanne 1 ouvrir;0;W\r\n"
                  "LEVEL;%MW300;REAL;Niveau;0;R\r\n").encode("cp1252")
IHM_REGISTRE = ("Name,Register,Type,Text,Unit\n"
                "RUN,100.0,Bit,Marche,\n"
                "LEVEL,300,Float,Niveau,m\n").encode("utf-8")


def b64(octets):
    return base64.b64encode(octets).decode()


class Base(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-formats-var-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        app = self.app = Application()
        app.nouveau({"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.fiche_ouvrage({"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "34", "libelle": "Essai télétransmission",
            "automate": "Sch - M580", "revision": "A"}})
        for t, n in (("PM", "01"), ("LT", "02"), ("MV", "03")):
            i = app.ajouter_equipement({"type": t, "numero": n, "se": "00"})["ident"]
            if t == "MV":
                app.s.ouvrage.equipement(i).options = ["Télécommandée"]
            app.decider_proposition({"ident_eq": i, "decision": "retenir"})
        self.s = app.s
        self.s.ouvrage.supervision = "TOPKAPI"

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def adresser(self):
        self.s.appliquer_adressage(adressage.calculer(self.s).empreinte, ("automate",))

    def apprendre(self, octets, nature, logiciel, nom, reglages=None):
        r = self.app.formats_appris_action({"action": "enregistrer", "fichier": "exemple.csv", "contenu": b64(octets),
                                            "nature": nature, "logiciel": logiciel, "nom": nom,
                                            "reglages": reglages or {}})
        return fa.trouver(r["ident"])


class TestAnalyseVariables(Base):
    def test_supervision_mw_colonnes_tables_et_alarme(self):
        a = fa.analyser(SUPERVISION_MW, "tags.csv", nature="teletransmission")
        self.assertEqual([c["champ"] for c in a["colonnes"]], ["nom", "adresse", "type", "libelle", "alarme", "sens"])
        self.assertEqual(a["adresse"]["reconnue"], "%MW mot.bit")
        self.assertEqual(a["adresse"]["gabarits"]["TS"], "%MW{MOT}.{BIT}")
        self.assertEqual(a["adresse"]["gabarits"]["TM"], "%MW{MOT}")
        self.assertEqual((a["types"]["TS"], a["types"]["TM"], a["types"]["CP"]), ("BOOL", "REAL", ""))
        self.assertEqual((a["sens"]["TS"], a["sens"]["TC"], a["sens"]["TR"]), ("R", "W", "W"))
        self.assertEqual(a["alarme"], {"oui": "1", "non": "0"})

    def test_ihm_registre(self):
        a = fa.analyser(IHM_REGISTRE, "ihm.csv", nature="ihm")
        self.assertEqual([c["champ"] for c in a["colonnes"]], ["nom", "adresse", "type", "libelle", "unite"])
        self.assertEqual(a["adresse"]["reconnue"], "registre")
        self.assertEqual((a["adresse"]["gabarits"]["TC"], a["adresse"]["gabarits"]["CP"]), ("{REGISTRE}.{BIT}", "{REGISTRE}"))
        self.assertEqual((a["types"]["TS"], a["types"]["TM"]), ("Bit", "Float"))

    def test_jetons_controles_par_nature(self):
        a = fa.analyser(SUPERVISION_MW, nature="teletransmission")
        cles = fa.CLES["teletransmission"]
        with self.assertRaises(fa.FormatRefuse):                    # {VOIE} n'existe pas pour une variable
            fa.definir(a, {"adresse": {"gabarits": {c: "{VOIE}" for c in cles}}})
        with self.assertRaises(fa.FormatRefuse):                    # contenu propre aux E/S
            fa.definir(a, {"colonnes": ["nom", "adresse", "type", "libelle", "module", "sens"]})
        with self.assertRaises(fa.FormatRefuse):                    # nature de l'enregistrement différente
            fa.enregistrer("Essai", "es_physiques", "TOPKAPI", fa.definir(a, {}))


class TestProductionVariables(Base):
    def test_variables_sans_adresse_refusees(self):
        f = self.apprendre(SUPERVISION_MW, "teletransmission", "TOPKAPI", "Supervision fictive")
        with self.assertRaises(fa.FormatRefuse) as ctx:
            fa.exporter(f, self.s)
        self.assertIn("sans adresse", str(ctx.exception))

    def test_supervision_mw_production_et_relecture(self):
        self.adresser()
        f = self.apprendre(SUPERVISION_MW, "teletransmission", "TOPKAPI", "Supervision fictive")
        nom, octets, statut = fa.exporter(f, self.s)
        lignes = octets.decode("cp1252").split("\r\n")
        self.assertEqual(lignes[0], "Tag;Address;DataType;Description;Alarm;Access")
        lues = {r[0]: r for r in csv.reader(io.StringIO("\n".join(lignes[1:])), delimiter=";") if r}
        variables = self.s.variables()
        self.assertEqual(len(lues), len(variables))
        for v in variables:
            r = lues[v.nom]
            self.assertEqual(r[1], v.adresse)                                   # %MW mot.bit reproduit
            self.assertEqual(r[2], {"TS": "BOOL", "TC": "BOOL", "TM": "REAL"}.get(v.famille, v.type_logique))
            self.assertEqual(r[3], v.libelle_topkapi)
            self.assertEqual(r[4], "1" if v.alarme else "0")
            self.assertEqual(r[5], "W" if v.famille in ("TC", "TR") else "R")
        self.assertIn("NON QUALIFIÉ", statut)

    def test_registre_avec_decalage_modbus(self):
        self.adresser()
        self.s.ouvrage.decalage_modbus = 1
        self.s.ouvrage.ihm = "Vijeo Designer"
        f = self.apprendre(IHM_REGISTRE, "ihm", "Vijeo Designer", "IHM fictive")
        texte = fa.exporter(f, self.s)[1].decode("utf-8")
        lues = {r[0]: r for r in csv.reader(io.StringIO(texte.split("\n", 1)[1])) if r}
        for v in self.s.variables():
            mot, _, bit = v.adresse[3:].partition(".")
            self.assertEqual(lues[v.nom][1], f"{int(mot) + 1}" + (f".{bit}" if bit else ""))
            self.assertEqual(lues[v.nom][4], v.unite)

    def test_bit_exige_sur_une_variable_mot_refuse(self):
        self.adresser()
        cles = fa.CLES["teletransmission"]
        f = self.apprendre(SUPERVISION_MW, "teletransmission", "TOPKAPI", "Règle bit partout",
                           {"adresse": {"gabarits": {c: "%MW{MOT}.{BIT}" for c in cles}}})
        with self.assertRaises(fa.FormatRefuse) as ctx:
            fa.exporter(f, self.s)
        self.assertIn("BIT sans valeur", str(ctx.exception))

    def test_adresses_en_double_apres_conversion_refusees(self):
        self.adresser()
        cles = fa.CLES["teletransmission"]
        f = self.apprendre(SUPERVISION_MW, "teletransmission", "TOPKAPI", "Règle mot seul",
                           {"adresse": {"gabarits": {c: "%MW{MOT}" for c in cles}}})
        with self.assertRaises(fa.FormatRefuse) as ctx:
            fa.exporter(f, self.s)
        self.assertIn("même adresse", str(ctx.exception))


class TestChoixEtGenerationGroupee(Base):
    def test_retenu_selon_supervision_et_ihm_de_l_ouvrage(self):
        self.adresser()
        top = self.apprendre(SUPERVISION_MW, "teletransmission", "topkapi", "Supervision TOPKAPI fictive")
        pcv = self.apprendre(SUPERVISION_MW, "teletransmission", "PcVue", "Supervision PcVue fictive")
        ihm = self.apprendre(IHM_REGISTRE, "ihm", "Vijeo Designer", "IHM fictive")
        self.assertEqual(fa.retenu(top, self.s.ouvrage), (True, ""))
        self.assertIn("l'ouvrage utilise TOPKAPI", fa.retenu(pcv, self.s.ouvrage)[1])
        self.assertIn("aucun logiciel d'IHM", fa.retenu(ihm, self.s.ouvrage)[1])
        _, octets = self.app.exporter({"quoi": "generation_groupee", "familles": "supervision"})
        z = zipfile.ZipFile(io.BytesIO(octets))
        journal = {r["Pièce"]: r for r in csv.DictReader(io.StringIO(z.read("00_journal.csv").decode("utf-8-sig")),
                                                         delimiter=";")}
        self.assertEqual(journal["Format appris « Supervision TOPKAPI fictive »"]["État"], "produit")
        self.assertTrue(journal["Format appris « Supervision TOPKAPI fictive »"]["Fichier"].startswith("03_Supervision/"))
        self.assertEqual(journal["Format appris « Supervision PcVue fictive »"]["État"], "non retenu")
        self.assertEqual(journal["Format appris « IHM fictive »"]["État"], "non retenu")

    def test_api_specification_et_export_unitaire(self):
        r = self.app.formats_appris_web({})
        self.assertEqual(r["specs"]["teletransmission"]["cles"], ["TS", "TC", "TM", "TR", "RTR", "CP"])
        self.assertIn("REGISTRE", r["specs"]["ihm"]["jetons"])
        self.assertEqual(r["logiciels_ouvrage"]["supervision"], ["TOPKAPI"])
        f = self.apprendre(SUPERVISION_MW, "teletransmission", "TOPKAPI", "Supervision fictive")
        etat = next(x for x in self.app.formats_appris_web({})["formats"] if x["ident"] == f["ident"])
        self.assertFalse(etat["controle"]["pret"])                     # variables pas encore adressées
        self.adresser()
        etat = next(x for x in self.app.formats_appris_web({})["formats"] if x["ident"] == f["ident"])
        self.assertTrue(etat["controle"]["pret"], etat["controle"])
        nom, octets = self.app.exporter({"quoi": "format_appris", "ident": f["ident"]})
        self.assertTrue(octets.startswith(b"Tag;Address"))
        r = self.app.formats_appris_action({"action": "apercu", "fichier": "t.csv", "contenu": b64(SUPERVISION_MW),
                                            "nature": "teletransmission", "reglages": {}})
        self.assertEqual((r["refus"], r["ecarts"]), ([], []))
        with self.assertRaises(RegleMetier):
            self.app.formats_appris_action({"action": "analyser", "fichier": "t.csv", "contenu": b64(SUPERVISION_MW),
                                            "nature": "inconnue"})


if __name__ == "__main__":
    unittest.main()
