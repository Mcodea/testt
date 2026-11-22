"""Gammes de matériel déclarées par l'atelier (22/11/2026) : OGIAS ouvert à l'automate de chaque client.

Gamme FICTIVE « Siemens S7-1500 » (références d'essai, aucune capacité réelle garantie) : déclaration contrôlée,
reconnaissance dans la fiche de l'ouvrage, proposition de racks et de cartes, implantation, nomenclature, export au
format appris ; les gammes livrées (Schneider, SOFREL) ne changent pas.
"""
import base64
import copy
import os
import tempfile
import unittest

from genvar import gammes_materiel as gm
from genvar import materiel
from sorep_web.serveur import Application, RegleMetier

S7 = {"code": "S7-1500", "nom": "Siemens S7-1500 (fictif)", "constructeur": "Siemens", "motifs": ["S7-1500"],
      "emplacements_cpu": 1,
      "racks": [{"reference": "PROFIL-160 (fictif)", "positions": 8}, {"reference": "PROFIL-482 (fictif)", "positions": 16}],
      "cartes": [{"reference": "DI 32x24VDC (fictif)", "nature": "ET", "voies": 32, "description": "32 entrées TOR"},
                 {"reference": "DI 16x24VDC (fictif)", "nature": "ET", "voies": 16},
                 {"reference": "DQ 32x24VDC (fictif)", "nature": "ST", "voies": 32},
                 {"reference": "AI 8xU/I (fictif)", "nature": "EA", "voies": 8},
                 {"reference": "AQ 4xU/I (fictif)", "nature": "SA", "voies": 4}],
      "defaut": {"ET": "DI 32x24VDC (fictif)"},
      "processeurs": [{"reference": "CPU 1515-2 PN (fictif)", "description": "Processeur d'essai"}],
      "alimentations": [{"reference": "PM 70W (fictif)", "description": "Alimentation d'essai 70 W"}]}


class Base(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-gammes-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        materiel._CACHE.clear()

    def tearDown(self):
        materiel._CACHE.clear()
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def ouvrage(self, automate):
        app = Application()
        app.nouveau({"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        try:                                             # valeur ajoutée par « Gérer les listes »
            app.listes_ouvrage_action({"action": "ajouter", "groupe": "automates", "code": automate, "regie": "Automate"})
        except RegleMetier:                              # déjà dans la liste
            pass
        app.fiche_ouvrage({"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "36", "libelle": "Essai gamme déclarée",
            "automate": automate, "revision": "A"}})
        for t, n in (("PM", "01"), ("PM", "02"), ("LT", "03"), ("MV", "04")):
            i = app.ajouter_equipement({"type": t, "numero": n, "se": "00"})["ident"]
            if t == "MV":
                app.s.ouvrage.equipement(i).options = ["Télécommandée"]
            app.decider_proposition({"ident_eq": i, "decision": "retenir"})
        app.s.valider_contenu_es([(p.ident_eq, p.cle) for p in app.s.points()])
        return app


class TestDeclaration(Base):
    def test_controles_et_carte_par_defaut(self):
        g = gm.enregistrer(copy.deepcopy(S7))
        self.assertEqual(g["code"], "S7-1500")
        self.assertEqual(g["defaut"], {"ET": "DI 32x24VDC (fictif)", "ST": "DQ 32x24VDC (fictif)",
                                       "EA": "AI 8xU/I (fictif)", "SA": "AQ 4xU/I (fictif)"})
        self.assertEqual([r["positions"] for r in g["racks"]], [8, 16])
        cas = {
            "code livré": {"code": "M340"},
            "code mal formé": {"code": "S"},
            "motif d'une gamme livrée": {"code": "X1", "motifs": ["BMXP3420"]},
            "motif trop court": {"code": "X2", "motifs": ["S7"]},
            "motif recoupant une autre gamme": {"code": "X3", "motifs": ["S7-1500F"]},
            "code déjà pris": {"code": "S7-1500", "motifs": ["AUTRE"]},
            "carte sans voies": {"code": "X4", "motifs": ["AUTRE"], "cartes": [{"reference": "A", "nature": "ET", "voies": 0}]},
            "nature inconnue": {"code": "X5", "motifs": ["AUTRE"], "cartes": [{"reference": "A", "nature": "XX", "voies": 8}]},
            "carte en double": {"code": "X6", "motifs": ["AUTRE"], "cartes": [{"reference": "A", "nature": "ET", "voies": 8},
                                                                             {"reference": " a ", "nature": "ST", "voies": 8}]},
            "rack plus petit que le processeur": {"code": "X7", "motifs": ["AUTRE"], "racks": [{"reference": "R", "positions": 1}]},
            "défaut d'une autre nature": {"code": "X8", "motifs": ["AUTRE"], "defaut": {"ET": "DQ 32x24VDC (fictif)"}},
            "défaut à choisir": {"code": "X9", "motifs": ["AUTRE"], "defaut": {}},
        }
        for nom, modif in cas.items():
            with self.subTest(nom), self.assertRaises(gm.GammeRefusee):
                gm.enregistrer({**copy.deepcopy(S7), **modif})

    def test_reconnaissance_dans_la_fiche(self):
        gm.enregistrer(copy.deepcopy(S7))
        self.assertEqual(materiel.gamme("Sie - S7-1500 F"), "S7-1500")
        self.assertEqual(materiel.gamme("sie - s7 - 1500"), "S7-1500")       # espaces et casse ignorés
        self.assertEqual(materiel.gamme("Sch - M580"), "M580")               # gammes livrées inchangées
        self.assertIsNone(materiel.gamme("Wago 750"))

    def test_modifier_et_supprimer(self):
        g = gm.enregistrer(copy.deepcopy(S7))
        g2 = gm.enregistrer({**copy.deepcopy(S7), "nom": "Siemens S7-1500 révisée"}, g["ident"])
        self.assertEqual((g2["ident"], g2["nom"]), (g["ident"], "Siemens S7-1500 révisée"))
        self.assertEqual(len(gm.lister()), 1)
        gm.supprimer(g["ident"])
        self.assertIsNone(materiel.gamme("Sie - S7-1500"))
        with self.assertRaises(gm.GammeRefusee):
            gm.supprimer(g["ident"])


class TestCalcul(Base):
    def test_gamme_non_declaree_bloquee_avec_la_marche_a_suivre(self):
        app = self.ouvrage("Sie - S7-1500")
        with self.assertRaises(RegleMetier) as ctx:
            app.s.proposer_materiel()
        self.assertIn("Gammes de matériel", str(ctx.exception))

    def test_chaine_complete_sur_une_gamme_declaree(self):
        gm.enregistrer(copy.deepcopy(S7))
        app = self.ouvrage("Sie - S7-1500")
        s = app.s
        prop = s.proposer_materiel()
        self.assertEqual(prop.plateforme, "S7-1500")
        refs = {m["reference"] for m in prop.modules}
        self.assertTrue(refs <= {c["reference"] for c in S7["cartes"]}, refs)
        self.assertTrue(all("BMX" not in r and "BME" not in r for r in refs))        # jamais une carte Schneider
        self.assertEqual(prop.racks[0]["cpu"], [0])
        self.assertTrue(any("déclarée par l'atelier" in r for r in prop.remarques))
        self.assertTrue(any("outil Siemens" in r for r in prop.remarques))
        s.appliquer_materiel()
        n, manquantes, _ = s.implanter_es()
        self.assertEqual((manquantes, s.erreurs_materiel()), ({}, []))
        self.assertTrue(all(p.adresse for p in s.points() if p.raccordement != "Communication"))
        nomen = {x["reference"]: x for x in s.nomenclature_materiel()}
        self.assertEqual(nomen["DI 32x24VDC (fictif)"]["designation"], "32 entrées TOR")
        vue = app.materiel({})
        self.assertEqual(vue["plateforme"], "S7-1500")
        self.assertIn("déclarée par l'atelier", vue["statut_catalogue"])
        self.assertEqual({c["reference"] for c in vue["cartes_catalogue"]}, {c["reference"] for c in S7["cartes"]})
        s.definir_config_materiel(processeur="CPU 1515-2 PN (fictif)", alimentation="PM 70W (fictif)")
        with self.assertRaises(RegleMetier):                 # carte de la gamme : nature et voies imposées
            s.ajouter_module(1, 3, "ET", 16, "DI 32x24VDC (fictif)")
        # export de la liste des E/S au format appris du constructeur
        exemple = b'"Name","Data Type","Logical Address"\n"M","Bool","%I4.0"\n"N","Int","%IW64"\n'
        r = app.formats_appris_action({"action": "enregistrer", "fichier": "tia.csv", "contenu": base64.b64encode(exemple).decode(),
                                       "nature": "es_physiques", "logiciel": "Sie - S7-1500", "nom": "E/S S7 fictif"})
        texte = app.exporter({"quoi": "format_appris", "ident": r["ident"]})[1].decode()
        self.assertTrue(texte.startswith('"Name","Data Type","Logical Address"'))
        self.assertEqual(texte.count("\n") - 1, len([p for p in s.points() if p.raccordement != "Communication"]))

    def test_nature_sans_carte_declaree_refusee(self):
        partielle = {**copy.deepcopy(S7), "cartes": [c for c in S7["cartes"] if c["nature"] != "EA"]}
        gm.enregistrer(partielle)
        app = self.ouvrage("Sie - S7-1500")
        with self.assertRaises(RegleMetier) as ctx:
            app.s.proposer_materiel()
        self.assertIn("aucune carte EA", str(ctx.exception))

    def test_gammes_livrees_inchangees(self):
        gm.enregistrer(copy.deepcopy(S7))
        app = self.ouvrage("Sch - M580")
        prop = app.s.proposer_materiel()
        self.assertEqual(prop.plateforme, "M580")
        self.assertTrue(all(m["reference"].startswith("BM") for m in prop.modules))


class TestApi(Base):
    def test_api(self):
        app = Application()
        r = app.gammes_materiel_action({"action": "enregistrer", "gamme": copy.deepcopy(S7)})
        self.assertEqual(r["gammes"][0]["cartes_par_nature"], {"ET": 2, "ST": 1, "EA": 1, "SA": 1})
        self.assertIn("SOFREL S4W", r["livrees"])
        with self.assertRaises(RegleMetier):
            app.gammes_materiel_action({"action": "enregistrer", "gamme": {**copy.deepcopy(S7), "nom": ""}})
        r = app.gammes_materiel_action({"action": "supprimer", "ident": r["ident"]})
        self.assertEqual(r["gammes"], [])


if __name__ == "__main__":
    unittest.main()
