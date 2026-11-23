"""Règles de cohérence nommées (orientation du 18/11/2026) : catalogue complet, chaque contrôle porte sa règle,
contrôles transversaux de la chaîne de l'information. Ouvrages entièrement fictifs (lieu XTST)."""
from pathlib import Path
import re
from types import SimpleNamespace
import unittest

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.coherence import REGLES, controler_chaine, decrire
from genvar.modele import Equipement
from genvar.session import Session

RACINE = Path(__file__).resolve().parents[1]
RE_CODE = re.compile(r"R-[A-Z]{2,3}-\d{2}")


def nouvelle(automate="M340"):
    s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
    s.nouveau(lieu_dans_le_nom=False)
    s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
    s.definir("automate", automate)
    s.ajouter_sous_ensemble("00")
    return s


def var(nom, famille="TS", code="A", ident="e1", nom_es="", libelle="", adresse="%MW1000.0"):
    return SimpleNamespace(nom=nom, famille=famille, code=code, ident_eq=ident, repere="XTSTRV01PM01", nom_es=nom_es,
                           libelle_topkapi=libelle, adresse=adresse)


def point(nom, variable=""):
    return SimpleNamespace(nom=nom, variable=variable, repere="XTSTRV01PM01", ident_eq="e1")


class TestCatalogue(unittest.TestCase):
    def test_chaque_regle_est_complete(self):
        for code, r in REGLES.items():
            with self.subTest(code=code):
                self.assertRegex(code, RE_CODE)
                self.assertIn(r.gravite, ("Erreur", "Alerte"))
                for champ in (r.titre, r.etape, r.pourquoi, r.corriger):
                    self.assertGreater(len(champ), 5)
                self.assertEqual(decrire(code)["code"], code)
        self.assertEqual(decrire("R-XXX-99"), {})

    def test_codes_cites_et_catalogue_concordent(self):
        """Tout code employé par le moteur ou le serveur existe ; toute règle du catalogue est employée."""
        sources = "".join(p.read_text(encoding="utf-8") for p in [*(RACINE / "genvar").glob("*.py"), RACINE / "sorep_web" / "serveur.py"]
                          if p.name != "coherence.py")
        sources += (RACINE / "genvar" / "coherence.py").read_text(encoding="utf-8").split("def controler_chaine", 1)[1]
        cites = set(RE_CODE.findall(sources))
        self.assertEqual(cites - set(REGLES), set(), "code cité absent du catalogue")
        self.assertEqual(set(REGLES) - cites, set(), "règle du catalogue jamais employée")


class TestChaqueControlePorteSaRegle(unittest.TestCase):
    def test_anomalies_d_un_ouvrage_neuf(self):
        s = nouvelle()
        for t, n in (("PM", "01"), ("HV", "02"), ("MV", "03")):
            e = s.ajouter_equipement(Equipement("00", t, n))
            s.decider_propositions(e.ident, "retenir")
        s.ouvrage.lieu = "xt"                                        # lieu mal formé : R-OUV-02 (essai, non enregistré)
        anomalies = s.anomalies()
        self.assertTrue(anomalies)
        sans_code = [a.message for a in anomalies if a.code not in REGLES]
        self.assertEqual(sans_code, [], "anomalie sans règle nommée")
        self.assertIn("R-OUV-02", {a.code for a in anomalies})
        # Ouvrage généré par OGIAS : la chaîne E/S ↔ variables est cohérente par construction (aucun faux positif)
        self.assertFalse({a.code for a in anomalies} & {"R-CHA-01", "R-CHA-02"})


class TestControlesTransversaux(unittest.TestCase):
    def ouvrage(self, decalage=0):
        return SimpleNamespace(decalage_modbus=decalage, mode="Neuf")

    def codes(self, variables, points, decalage=0):
        return [a.code for a in controler_chaine(self.ouvrage(decalage), variables, points)]

    def test_chaine_coherente_sans_ecart(self):
        variables = [var("TS_A", nom_es="ET_A", libelle="Marche"), var("TR_C", "TR", "C", libelle="Consigne"),
                     var("RTR_C", "RTR", "C", libelle="Retour consigne")]
        self.assertEqual(self.codes(variables, [point("ET_A", "TS_A")]), [])

    def test_variable_vers_es_introuvable(self):
        self.assertEqual(self.codes([var("TS_A", nom_es="ET_ABSENTE")], []), ["R-CHA-01"])

    def test_es_vers_variable_introuvable(self):
        self.assertEqual(self.codes([], [point("ET_A", "TS_ABSENTE")]), ["R-CHA-02"])

    def test_es_locale_sans_variable_n_est_pas_un_ecart(self):
        self.assertEqual(self.codes([], [point("ET_LOCALE", "")]), [])

    def test_teleréglage_sans_retour(self):
        self.assertEqual(self.codes([var("TR_C", "TR", "C")], []), ["R-TEL-01"])
        self.assertEqual(self.codes([var("TR_C", "TR", "C"), var("RTR_C", "RTR", "C", ident="e2")], []), ["R-TEL-01"])

    def test_libelles_topkapi_identiques_sur_un_equipement(self):
        variables = [var("TS_A", libelle="Défaut"), var("TS_B", code="B", libelle="défaut ")]
        self.assertEqual(self.codes(variables, []), ["R-TEL-03"])
        autre = [var("TS_A", libelle="Défaut"), var("TS_B", code="B", ident="e2", libelle="Défaut")]
        self.assertEqual(self.codes(autre, []), [])

    def test_decalage_qui_rend_une_adresse_negative(self):
        variables = [var("TS_A", adresse="%MW10.0")]
        self.assertEqual(self.codes(variables, [], decalage=-5), [])
        self.assertEqual(self.codes(variables, [], decalage=-11), ["R-TEL-02"])

    def test_recette_expose_la_regle_et_son_explication(self):
        from sorep_web.serveur import Application                     # noqa: F401  (importable)
        s = nouvelle()
        e = s.ajouter_equipement(Equipement("00", "PM", "01"))
        s.decider_propositions(e.ident, "retenir")
        for a in s.anomalies():
            d = decrire(a.code)
            self.assertTrue(d["pourquoi"] and d["corriger"], a.code)


if __name__ == "__main__":
    unittest.main()


def test_api_regles_lecture_seule():
    from sorep_web.serveur import Application
    app = Application.__new__(Application)
    r = Application.regles_web(app, {})
    assert len(r["regles"]) == len(REGLES) and all(x["pourquoi"] for x in r["regles"])
