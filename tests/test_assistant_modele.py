"""Lot 7 (19/11/2026) : assistant « créer un modèle de livrable depuis un export » (données fictives XTST).

Les exports simulés ici sont des fichiers FICTIFS écrits pour l'essai (aucun format d'outil réel n'est reproduit) :
ils servent à vérifier la reconnaissance des valeurs et la reproduction exacte, pas une compatibilité.
"""
import base64
import os
import tempfile
import unittest

from genvar import assistant_modele as am
from genvar import modeles_livrables as ml
from genvar.session import RegleMetier
from sorep_web.serveur import Application


class TestAssistantModele(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-assistant-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        app = self.app = Application()
        app.nouveau({"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.fiche_ouvrage({"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "31", "libelle": "Essai assistant",
            "automate": "Sch - M340", "revision": "A"}})
        self.ids = [app.ajouter_equipement({"type": t, "numero": n, "se": "00"})["ident"]
                    for t, n in (("PM", "01"), ("PM", "02"), ("HV", "01"))]
        self.s = app.s
        self.pm01 = self.s.ouvrage.equipement(self.ids[0])
        self.vars = sorted((v for v in self.s.variables() if v.ident_eq == self.ids[0]), key=lambda v: v.nom)

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def _export_csv(self, variables=None):
        rep = self.s.ouvrage.repere(self.pm01)
        lignes = "".join(f"{v.nom};{v.libelle_topkapi};{v.type_logique};{rep}\r\n" for v in (variables or self.vars))
        return f"Tag;Description;Type;Groupe\r\n{lignes}Fin de liste\r\n"

    def test_reproduction_identique_et_generalisation(self):
        r = am.construire(self._export_csv(), self.s, self.ids[0])
        self.assertEqual(r["verification"]["etat"], "identique", r["verification"])
        g = r["gabarit"]
        self.assertTrue(g.startswith("Tag;Description;Type;Groupe\r\n<#DEBUT_EQUIPEMENTS_PM#>\r\n"))
        self.assertIn("<#NOM#>;<#LIBELLE#>;<#TYPE#>;<#REPERE#>", g)
        self.assertTrue(g.endswith("<#FIN_EQUIPEMENTS_PM#>\r\nFin de liste\r\n"))
        self.assertNotIn("PM01", g)                       # plus rien de propre à l'équipement de référence
        self.assertTrue(any("Aucune adresse" in a for a in r["alertes"]))   # colonne d'adresses impossible à reconnaître
        rempli = ml.remplir(g, self.s)
        pm02 = self.s.ouvrage.repere(self.s.ouvrage.equipement(self.ids[1]))
        self.assertIn(pm02, rempli)                        # se répète pour l'autre pompe…
        self.assertNotIn(self.s.ouvrage.repere(self.s.ouvrage.equipement(self.ids[2])), rempli)   # …pas pour la vanne
        vars_pm02 = [v.nom for v in self.s.variables() if v.ident_eq == self.ids[1]]
        self.assertTrue(all(n in rempli for n in vars_pm02))

    def test_refus_d_une_substitution(self):
        r = am.construire(self._export_csv(), self.s, self.ids[0], refus=["TYPE"])
        self.assertIn("<#NOM#>;<#LIBELLE#>;BOOL;<#REPERE#>", r["gabarit"])
        self.assertTrue(any(p["variable"] == "TYPE" and p.get("refusee") for p in r["propositions"]))
        self.assertFalse(any(p["variable"] == "TYPE" and not p.get("refusee") for p in r["propositions"]))

    def test_export_partiel_et_familles(self):
        ts = [v for v in self.vars if v.famille == "TS"][:2]
        autres = [v for v in self.vars if v.famille != "TS"][:1]
        self.assertTrue(ts and autres)
        rep = self.s.ouvrage.repere(self.pm01)
        texte = ("".join(f"BIT;{v.nom};{rep}\n" for v in ts) + "".join(f"MOT;{v.nom};{v.unite or '-'};{rep}\n" for v in autres))
        r = am.construire(texte, self.s, self.ids[0])
        self.assertIn(f"VARIABLES_{autres[0].famille}", r["blocs"])
        self.assertIn("VARIABLES_TS", r["blocs"])
        # le bloc génère toutes les variables TS de l'équipement, pas seulement les 2 de l'export
        self.assertEqual(r["verification"]["etat"], "complete", r["verification"])

    def test_xml_echappement_detecte(self):
        v = self.vars[0]
        rep = self.s.ouvrage.repere(self.pm01)
        texte = (f'<?xml version="1.0"?>\n<objets>\n<objet nom="{rep}">\n'
                 + "".join(f'<var nom="{x.nom}" texte="{x.libelle_topkapi.replace("—", "&#8212;")}"/>\n' for x in [v])
                 + "</objet>\n</objets>\n")
        r = am.construire(texte, self.s, self.ids[0])
        self.assertEqual(r["echappement"], "xml")
        self.assertIn('<objet nom="<#REPERE#>">', r["gabarit"])
        self.assertIn('<var nom="<#NOM#>"', r["gabarit"])

    def test_refus_motives(self):
        with self.assertRaisesRegex(am.AssistantRefuse, "Aucune valeur"):
            am.construire("a;b;c\n1;2;3\n", self.s, self.ids[0])
        with self.assertRaisesRegex(am.AssistantRefuse, "déjà des variables"):
            am.construire("<#REPERE#>\n", self.s, self.ids[0])
        with self.assertRaisesRegex(am.AssistantRefuse, "équipement de référence"):
            am.construire(self._export_csv(), self.s, "inconnu")

    def test_ligne_ambigue_signalee(self):
        a, b = self.vars[0], self.vars[1]
        texte = f"{a.nom};{a.type_logique}\n{a.nom}+{b.nom}\n"
        r = am.construire(texte, self.s, self.ids[0])
        self.assertEqual(r["non_generalisees"], 1)
        self.assertTrue(any("plusieurs variables" in x for x in r["alertes"]))

    def test_serveur_analyse_puis_enregistre(self):
        contenu = base64.b64encode(self._export_csv().encode("cp1252")).decode()
        corps = {"action": "assistant", "fichier": "pompe.csv", "contenu": contenu, "ident_eq": self.ids[0]}
        r = self.app.modeles_livrables_action(corps)
        self.assertEqual((r["verification"]["etat"], r["encodage"]), ("identique", "cp1252"))
        self.assertEqual(ml.lister(), [])                  # l'analyse n'enregistre rien
        r = self.app.modeles_livrables_action({**corps, "action": "assistant_enregistrer", "nom": "Pompe - export fictif"})
        self.assertEqual(r["modele"]["erreurs"], [])
        m = ml.lister()[0]
        self.assertEqual((m["encodage"], m["extension"]), ("cp1252", "csv"))
        self.assertIn("équipement de référence", m["description"])
        nom, octets = ml.generer(m["ident"], self.s)
        self.assertTrue(nom.endswith(".csv"))
        self.assertIn("—".encode("cp1252"), octets)
        with self.assertRaisesRegex(RegleMetier, "existe|porte déjà"):
            self.app.modeles_livrables_action({**corps, "action": "assistant_enregistrer", "nom": "Pompe - export fictif"})

    def test_filtre_type_dans_le_moteur(self):
        arbre, erreurs, _ = ml.analyser("<#DEBUT_EQUIPEMENTS_HV#><#REPERE#>\n<#FIN_EQUIPEMENTS_HV#>")
        self.assertEqual(erreurs, [])
        texte = ml.remplir("<#DEBUT_EQUIPEMENTS_HV#><#REPERE#>\n<#FIN_EQUIPEMENTS_HV#>", self.s)
        self.assertEqual(texte, self.s.ouvrage.repere(self.s.ouvrage.equipement(self.ids[2])) + "\n")
        _, erreurs, _ = ml.analyser("<#DEBUT_EQUIPEMENTS_PMXYZ#><#FIN_EQUIPEMENTS_PMXYZ#>")
        self.assertTrue(erreurs)


if __name__ == "__main__":
    unittest.main()
