"""Référentiel des modèles (extrait d'une base de supervision) et import d'inventaire.

Jeu d'essai synthétique écrit par le test : aucune donnée de projet réel n'est nécessaire.
"""
import csv
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from genvar import modeles, tableur
from genvar.modele import Equipement
from genvar.session import Session, RegleMetier

ENTETES = ["", "COD_LIEU", "COD_UF", "LIB_UF", "Repère équipement\nCOD_EQPT", "COD_TYP_MAT", "LIB_EQPT",
           "NO_SIGNIF", "LIB_SIGNIF", "COD_MET", "COD_T_ARCH", "COD_ROLE", "TYP_VAR", "MNEMO_VAR", "NOM_TABLE",
           "ADR1", "NOM_OBJET", "NOM_STR", "NO_ELEM", "NO_BIT", "NOM_ELEM", "NOM_MODELE"]
LIGNES = [
    # repère, type, libellé, n° signif, lib signif, métier, arch, rôle, format, mnémo, table, adr, objet, str, elem, bit, nom, modèle
    ("X999ZZ00SY01", "SY--", "SYNTHESE FICTIVE", "", "", "", "", "SYN_DEF", "L", "", "", "", "X999ZZ00SY01", "SYNTHESE", 1, 0, "REGROUPE_DEFAUT", "!_SYNTHESE"),
    ("X999ZZ11HV01", "HV--", "VANNE FICTIVE 1", "10", "TS OUVERTE", "EXPL", "BE", "TS", "L", "TS_ZZ11HV01_OUV", "TS_TM1", "3,1", "X999ZZ11HV01", "VANNEHV", 10, 1, "ETAT", "!_VANNE_HV"),
    ("X999ZZ11HV01", "HV--", "VANNE FICTIVE 1", "11", "DEF POSITION", "EXPL", "BE", "DEF", "L", "DEF_ZZ11HV01_POS", "TS_TM1", "3,2", "X999ZZ11HV01", "VANNEHV", 11, 1, "DEF_POS", "!_VANNE_HV"),
    ("X999ZZ11HV02", "HV--", "VANNE FICTIVE 2", "10", "TS OUVERTE", "EXPL", "BE", "TS", "L", "TS_ZZ11HV02_OUV", "", "", "X999ZZ11HV02", "VANNEHV", 10, 1, "ETAT", "!_VANNE_HV"),
    ("X999ZZE0A01P", "A--P", "ARMOIRE FICTIVE", "20", "DEF 24V", "ELEC", "BE", "DEF", "L", "DEF_ZZE0A01P_24V", "", "", "X999ZZE0A01PDF", "ARMOIRE", 11, 1, "DEF_24V", "!_ARMOIRE_PROCESS"),
    ("X999ZZ12PM01", "PM--", "POMPE FICTIVE", "30", "TS EN MARCHE", "EXPL", "BE", "TS", "L", "TS_ZZ12PM01_MA", "", "", "X999ZZ12PM01", "GROUPEP", 10, 1, "ETAT", "!_GROUPE_POMPAGE_X999ZZ"),
    ("Y111AA11HV01", "HV--", "AUTRE OUVRAGE", "10", "TS OUVERTE", "EXPL", "BE", "TS", "L", "", "", "", "Y111AA11HV01", "VANNEHV", 10, 1, "ETAT", "!_VANNE_HV"),
]


class TestModelesInventaire(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.dossier = tempfile.mkdtemp()
        os.environ["SOREP_DATA_DIR"] = self.dossier
        self.base = os.path.join(self.dossier, "base.csv")
        with open(self.base, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(ENTETES)
            for x in LIGNES:
                rep, typ, lib, sig, lsig, met, arch, role, fmt, mn, tab, adr, obj, st, el, bit, nom, mod = x
                w.writerow(["", rep[:4], rep[4:6], "OUVRAGE FICTIF", rep, typ, lib, sig, lsig, met, arch, role, fmt,
                            mn, tab, adr, obj, st, el, bit, nom, mod])

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def test_import_volontaire_reduit_au_format_sorep(self):
        ref = modeles.extraire(tableur.lire_classeur(self.base), "essai")
        self.assertEqual(set(ref["types"]), {"HV", "A--P", "PM"})          # SY : lignes d'identité seulement
        hv = ref["modeles"]["!_VANNE_HV"]["lignes"]
        self.assertEqual([(l["role"], l["libelle"], l["suffixe"]) for l in hv], [("TS", "Ouverte", "OUV"), ("DEF", "Position", "POS")])
        texte = repr(ref)
        for donnee in ("X999ZZ11HV01", "VANNE FICTIVE", "3,1", "TS_TM1", "TS_ZZ11HV01_OUV", "'10'", "signification"):
            self.assertNotIn(donnee, texte)                              # ni ouvrage, ni n° de signification

    def test_motif_f6(self):
        self.assertEqual(modeles.repere_fin("PM", "03"), "PM03")
        self.assertEqual(modeles.repere_fin("A--P", "01"), "A01P")
        self.assertEqual(modeles.code_type("PM--"), "PM")
        self.assertEqual(modeles.code_type("A--P"), "A--P")

    def test_referentiel_vide_et_construit_dans_l_outil(self):
        s = Session()
        s.nouveau(False)
        self.assertTrue(s.modeles["modeles"])                             # modèles de départ livrés (noms SOREP)
        self.assertTrue(all(m["statut"] == "à valider" and not n.startswith("!_") for n, m in s.modeles["modeles"].items()))
        s.modeles = modeles.vide()                                         # essai sur un référentiel vierge
        s.creer_type("HV")
        s.creer_type("A--P", "Armoire process", "Électricité")
        with self.assertRaises(RegleMetier):
            s.creer_type("ABC")
        s.creer_modele("HV", "Vanne manuelle 2 FDC", depuis_catalogue=True)   # pré-rempli depuis les signaux SOREP
        lignes = s.modeles["modeles"]["Vanne manuelle 2 FDC"]["lignes"]
        self.assertTrue(lignes)
        s.creer_modele("A--P", "Armoire")
        s.ajouter_ligne_modele("Armoire", {"role": "DEF", "libelle": "Défaut 24 V", "suffixe": "DEF_24V", "format": "BOOL"})
        with self.assertRaises(RegleMetier):                              # doublon rôle + suffixe
            s.ajouter_ligne_modele("Armoire", {"role": "DEF", "libelle": "x", "suffixe": "DEF_24V"})
        with self.assertRaises(RegleMetier):
            s.ajouter_ligne_modele("Armoire", {"role": "XX", "libelle": "x", "suffixe": "A"})
        # équipement : lignes du modèle + adaptations propres
        s.definir("lieu", "X999"); s.definir("code_ouvrage", "ZZ"); s.ajouter_sous_ensemble("E0")
        a = s.ajouter_equipement(Equipement("E0", "A--P", "01", modele="Armoire"))
        self.assertEqual(s.ouvrage.repere(a), "X999ZZE0A01P")
        infos = s.informations(a)
        self.assertEqual([(i["mnemonique"], i["origine"]) for i in infos], [("DEF_ZZE0A01P_DEF_24V", "modèle")])
        s.modifier_ligne_eq(a.ident, infos[0]["id"], {"role": "DEF", "libelle": "Défaut alim 24 V", "suffixe": "DEF_24V"})
        s.ajouter_ligne_eq(a.ident, {"role": "TS", "libelle": "Porte ouverte", "suffixe": "PORTE"})
        with self.assertRaises(RegleMetier):
            s.ajouter_ligne_eq(a.ident, {"role": "TS", "libelle": "doublon", "suffixe": "PORTE"})
        infos = s.informations(a)
        self.assertEqual([i["origine"] for i in infos], ["modifiée", "ajoutée"])
        s.supprimer_lignes_eq(a.ident, [infos[0]["id"]])
        self.assertEqual([i["suffixe"] for i in s.informations(a)], ["PORTE"])
        self.assertEqual(len(s.modeles["modeles"]["Armoire"]["lignes"]), 1)  # le modèle n'est pas touché
        # le modèle évolue : l'équipement garde sa copie jusqu'à actualisation
        s.ajouter_ligne_modele("Armoire", {"role": "TS", "libelle": "Ventilation", "suffixe": "VENT"})
        self.assertNotIn("VENT", [i["suffixe"] for i in s.informations(a)])
        s.retablir_lignes_eq(a.ident)
        s.actualiser_modele_eq(a.ident)
        self.assertEqual([i["suffixe"] for i in s.informations(a)], ["DEF_24V", "VENT"])
        # persistance
        chemin = os.path.join(self.dossier, "x.ouvrage.json")
        s.enregistrer(chemin)
        s2 = Session()
        s2.ouvrir(chemin)
        a2 = s2.ouvrage.equipements[0]
        self.assertEqual(len(s2.informations(a2)), 2)
        self.assertEqual(set(Session().modeles["modeles"]), {"Vanne manuelle 2 FDC", "Armoire"})   # référentiel enregistré
        # validation : un modèle validé repasse « à valider » s'il est modifié ; idem pour un équipement
        s.valider_modele("Armoire")
        self.assertEqual(s.modeles["modeles"]["Armoire"]["statut"], "validé")
        s.ajouter_ligne_modele("Armoire", {"role": "TS", "libelle": "Porte", "suffixe": "PORTE"})
        self.assertEqual(s.modeles["modeles"]["Armoire"]["statut"], "à valider")
        self.assertEqual(s.valider_equipements([a.ident]), 1)
        self.assertTrue(a.valide)
        s.ajouter_ligne_eq(a.ident, {"role": "ALA", "libelle": "Température", "suffixe": "TEMP"})
        self.assertFalse(a.valide)

    def test_inventaire_avec_referentiel_vide(self):
        s = Session()
        s.nouveau(False)
        s.ouvrage.format_repere = ""          # base historique : repère avec sous-ensemble (préfixe à 6)
        s.modeles = modeles.vide()
        lignes = {l.repere: l for l in s.apercu_inventaire(self.base)}
        self.assertEqual(lignes["Y111AA11HV01"].etat, "refusé")
        self.assertEqual(lignes["X999ZZ11HV01"].etat, "à créer")           # HV connu du catalogue SOREP
        self.assertEqual(lignes["X999ZZ11HV01"].modele, "")                  # modèle du fichier jamais repris d'office
        self.assertIn("absent du référentiel", lignes["X999ZZ11HV01"].motif)
        self.assertEqual(lignes["X999ZZE0A01P"].etat, "à coder")           # type A--P à créer dans le référentiel
        s.creer_type("A--P", "Armoire process", "Électricité")
        lignes = {l.repere: l for l in s.apercu_inventaire(self.base)}
        self.assertEqual(lignes["X999ZZE0A01P"].etat, "à créer")
        n = s.appliquer_inventaire(list(lignes.values()))
        self.assertEqual(s.ouvrage.prefixe(), "X999ZZ")
        self.assertIn("X999ZZE0A01P", [s.ouvrage.repere(e) for e in s.ouvrage.equipements])
        self.assertTrue(all(l.etat in ("déjà présent", "refusé", "à coder") for l in s.apercu_inventaire(self.base)))
        self.assertGreaterEqual(n, 4)

if __name__ == "__main__":
    unittest.main()
