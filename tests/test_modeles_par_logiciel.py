"""Lot 8 (suite du principe « typicals » du 19/11/2026) : modèles de livrables rangés par logiciel cible.

Un modèle peut déclarer sa destination (automate, supervision, IHM) et son logiciel. L'ouvrage ne retient que les
modèles de SES logiciels ; un type d'équipement sans brique pour le logiciel de l'ouvrage est signalé « manquant »,
jamais comblé par la brique d'un autre logiciel. Données fictives (lieu XTST), modèles neutres.
"""
import csv
import io
import os
import tempfile
import unittest
import zipfile

from genvar import modeles_livrables as ml
from sorep_web.serveur import Application, RegleMetier

POMPES = b"<#DEBUT_EQUIPEMENTS_PM#><#REPERE#>;pompe\r\n<#FIN_EQUIPEMENTS_PM#>"
VANNES = b"<#DEBUT_EQUIPEMENTS_HV#><#REPERE#>;vanne\r\n<#FIN_EQUIPEMENTS_HV#>"
TOUS = b"<#DEBUT_VARIABLES#><#NOM#>\r\n<#FIN_VARIABLES#>"


class Base(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-logiciel-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        app = self.app = Application()
        app.nouveau({"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.fiche_ouvrage({"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "32", "libelle": "Essai logiciels cibles",
            "automate": "Sch - M580", "revision": "A"}})
        for t, n in (("PM", "01"), ("PM", "02"), ("HV", "03")):
            i = app.ajouter_equipement({"type": t, "numero": n, "se": "00"})["ident"]
            app.decider_proposition({"ident_eq": i, "decision": "retenir"})
        app.s.ouvrage.supervision = "TOPKAPI"

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def _journal(self):
        _, octets = self.app.exporter({"quoi": "generation_groupee", "familles": "modeles"})
        z = zipfile.ZipFile(io.BytesIO(octets))
        return z, list(csv.DictReader(io.StringIO(z.read("00_journal.csv").decode("utf-8-sig")), delimiter=";"))


class TestCibleDuModele(Base):
    def test_cible_controlee_et_modifiable_sans_toucher_au_fichier(self):
        m = ml.importer("Pompes TOPKAPI", "p.csv", POMPES, destination="supervision", logiciel="  TOPKAPI ")
        self.assertEqual((m["destination"], m["logiciel"]), ("supervision", "TOPKAPI"))
        octets = open(ml._fichier(m["ident"]), "rb").read()
        ml.definir_cible(m["ident"], "supervision", "PcVue")
        self.assertEqual(ml.trouver(m["ident"])["logiciel"], "PcVue")
        self.assertEqual(open(ml._fichier(m["ident"]), "rb").read(), octets)
        for destination, logiciel in (("supervision", ""), ("", "PcVue"), ("electrique", "EPLAN"), ("ihm", "x" * 41)):
            with self.subTest(destination=destination, logiciel=logiciel), self.assertRaises(ml.ModeleRefuse):
                ml.definir_cible(m["ident"], destination, logiciel)
        ml.definir_cible(m["ident"], "", "")
        self.assertEqual(ml.resume(ml.trouver(m["ident"]))["destination"], "")

    def test_ancien_modele_sans_cible_sert_a_tout_ouvrage(self):
        m = ml.importer("Ancien", "a.csv", TOUS)
        index = ml.lister()
        for x in index:                                      # index écrit avant le lot 8 : pas de champ cible
            x.pop("destination", None)
            x.pop("logiciel", None)
        ml._ecrire_index(index)
        r = ml.resume(ml.trouver(m["ident"]))
        self.assertEqual((r["destination"], r["logiciel"], r["types"]), ("", "", ["*"]))
        self.assertEqual(ml.retenu(r, self.app.s.ouvrage), (True, ""))

    def test_types_couverts(self):
        cas = {POMPES: ["PM"], POMPES + VANNES: ["HV", "PM"], TOUS: ["*"], POMPES + TOUS: ["*"],
               b"<#OUVRAGE#>": ["*"], b"<#DEBUT_EQUIPEMENTS#><#REPERE#><#FIN_EQUIPEMENTS#>": ["*"]}
        for texte, attendu in cas.items():
            with self.subTest(texte=texte):
                self.assertEqual(ml.types_couverts(ml.analyser(texte.decode())[0]), attendu)


class TestSelectionPourOuvrage(Base):
    def test_seuls_les_logiciels_de_l_ouvrage_sont_retenus(self):
        top = ml.importer("Pompes TOPKAPI", "p.csv", POMPES, destination="supervision", logiciel="topkapi")
        pcv = ml.importer("Pompes PcVue", "p.csv", POMPES, destination="supervision", logiciel="PcVue")
        ce = ml.importer("Blocs Control Expert", "b.txt", TOUS, destination="automate", logiciel="Control Expert")
        tia = ml.importer("Blocs TIA", "b.txt", TOUS, destination="automate", logiciel="TIA Portal")
        ihm = ml.importer("Écrans Vijeo", "v.txt", TOUS, destination="ihm", logiciel="Vijeo Designer")
        libre = ml.importer("Liste libre", "l.csv", TOUS)
        choix = {c["ident"]: c for c in ml.pour_ouvrage(self.app.s)["choix"]}
        self.assertTrue(choix[top["ident"]]["retenu"])                     # casse ignorée
        self.assertTrue(choix[ce["ident"]]["retenu"])                      # M580 → Control Expert
        self.assertTrue(choix[libre["ident"]]["retenu"])
        self.assertIn("l'ouvrage utilise TOPKAPI", choix[pcv["ident"]]["motif"])
        self.assertIn("Sch - M580 / Control Expert", choix[tia["ident"]]["motif"])
        self.assertEqual(choix[ihm["ident"]]["motif"],
                         "Modèle d'IHM Vijeo Designer : l'ouvrage ne déclare aucun logiciel d'IHM.")
        self.assertFalse(any(choix[x["ident"]]["retenu"] for x in (pcv, tia, ihm)))

    def test_brique_manquante_signalee_jamais_comblee_par_un_autre_logiciel(self):
        ml.importer("Pompes TOPKAPI", "p.csv", POMPES, destination="supervision", logiciel="TOPKAPI")
        ml.importer("Vannes PcVue", "v.csv", VANNES, destination="supervision", logiciel="PcVue")
        manques = ml.pour_ouvrage(self.app.s)["manques"]
        self.assertEqual([(x["destination"], x["logiciel"], x["type"], x["equipements"]) for x in manques],
                         [("supervision", "TOPKAPI", "HV", 1)])
        z, journal = self._journal()
        etats = {j["Pièce"]: (j["État"], j["Motif ou remarque"]) for j in journal}
        self.assertEqual(etats["Modèle « Pompes TOPKAPI »"][0], "produit")
        self.assertEqual(etats["Modèle « Vannes PcVue »"][0], "non retenu")
        self.assertIn("TOPKAPI", etats["Modèle « Vannes PcVue »"][1])
        self.assertEqual(etats["Brique TOPKAPI du type HV"][0], "manquant")
        self.assertIn("Rien n'est produit à sa place", etats["Brique TOPKAPI du type HV"][1])
        produits = [n for n in z.namelist() if n.startswith("06_Modeles_client/")]
        self.assertEqual(len(produits), 1)
        contenu = z.read(produits[0]).decode()
        self.assertEqual(contenu.count(";pompe"), 2)
        self.assertNotIn("vanne", contenu)

    def test_modele_en_erreur_ne_couvre_rien(self):
        ml.importer("Pompes TOPKAPI", "p.csv", POMPES, destination="supervision", logiciel="TOPKAPI")
        ml.importer("Vannes cassées", "v.csv", b"<#DEBUT_EQUIPEMENTS_HV#><#INCONNUE#>\r\n<#FIN_EQUIPEMENTS_HV#>",
                    destination="supervision", logiciel="TOPKAPI")
        self.assertEqual([x["type"] for x in ml.pour_ouvrage(self.app.s)["manques"]], ["HV"])
        couverture = ml.couverture()
        self.assertEqual([(g["logiciel"], g["types"], g["modeles"], g["en_erreur"]) for g in couverture],
                         [("TOPKAPI", ["PM"], 2, 1)])

    def test_rien_d_attendu_sans_modele_pour_le_logiciel_de_l_ouvrage(self):
        ml.importer("Pompes PcVue", "p.csv", POMPES, destination="supervision", logiciel="PcVue")
        ml.importer("Liste libre", "l.csv", POMPES)                      # sans cible : ne crée aucune attente
        self.assertEqual(ml.pour_ouvrage(self.app.s)["manques"], [])

    def test_modele_tous_types_couvre_tout(self):
        ml.importer("Tout TOPKAPI", "t.csv", TOUS, destination="supervision", logiciel="TOPKAPI")
        self.assertEqual(ml.pour_ouvrage(self.app.s)["manques"], [])


class TestApi(Base):
    def test_ecran_et_action_cible(self):
        r = self.app.modeles_livrables_action({"action": "importer", "nom": "Pompes TOPKAPI", "fichier": "p.csv",
                                               "contenu": __import__("base64").b64encode(POMPES).decode(),
                                               "destination": "supervision", "logiciel": "TOPKAPI"})
        m = next(x for x in r["modeles"] if x["ident"] == r["ident"])
        self.assertEqual((m["destination"], m["logiciel"], m["types"], m["retenu"]), ("supervision", "TOPKAPI", ["PM"], True))
        self.assertEqual(r["logiciels_ouvrage"]["supervision"], ["TOPKAPI"])
        self.assertEqual([x["type"] for x in r["manques"]], ["HV"])
        self.assertEqual(r["couverture"][0]["types"], ["PM"])
        self.assertIn("ihm", r["destinations"])
        r = self.app.modeles_livrables_action({"action": "cible", "ident": m["ident"], "destination": "supervision",
                                               "logiciel": "PcVue"})
        m = next(x for x in r["modeles"] if x["ident"] == m["ident"])
        self.assertFalse(m["retenu"])
        self.assertIn("TOPKAPI", m["motif_non_retenu"])
        self.assertEqual(r["manques"], [])
        with self.assertRaises(RegleMetier):
            self.app.modeles_livrables_action({"action": "cible", "ident": m["ident"], "destination": "supervision",
                                               "logiciel": ""})


if __name__ == "__main__":
    unittest.main()
