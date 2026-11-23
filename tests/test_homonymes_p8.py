"""Décision P8 / R9 : homonymes entre ouvrages d'un même programme automate (lieu hors du nom).

Deux variables (ou E/S) de même nom dans deux ouvrages enregistrés qui déclarent le même projet Control Expert
sont une erreur qui demande un arbitrage. Rien n'est renommé ; les fichiers ne sont jamais modifiés.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.homonymes import homonymes
from genvar.modele import Equipement
from genvar.session import Session


def _session(cat, lieu, projet, lieu_dans_le_nom=False, numero="01"):
    s = Session(cat)
    s.nouveau(lieu_dans_le_nom)
    s.definir("lieu", lieu); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = numero
    s.ouvrage.nom_projet = projet
    s.ajouter_sous_ensemble("00")
    eq = s.ajouter_equipement(Equipement("00", "MV", "01"))
    eq.options = ["Télécommandée"]
    s.decider_propositions(eq.ident, "retenir")
    return s


class TestHomonymes(unittest.TestCase):
    def setUp(self):
        self.cat = Catalogue.charger(chemins.fichier_catalogue_origine())

    def _autre(self, s):
        return [("XTSBRV01", s.ouvrage, s.catalogue)]

    def test_meme_programme_lieu_hors_du_nom_erreur_d_arbitrage(self):
        a, b = _session(self.cat, "XTST", "PRG_COMMUN"), _session(self.cat, "XTSB", " prg_commun ")
        anomalies = homonymes(a.ouvrage, a.catalogue, self._autre(b))
        self.assertTrue(anomalies)
        self.assertTrue(all(x.niveau == "Erreur" and x.etape == "Variables" for x in anomalies))
        messages = " ".join(x.message for x in anomalies)
        self.assertIn("TS_RV01MV01_OUV", messages)
        self.assertIn("ET_RV01MV01_OUV", messages)                  # E/S physiques comprises
        self.assertIn("XTSBRV01", messages)
        self.assertIn("Arbitrage nécessaire", messages)
        self.assertEqual(len(anomalies), 1)                         # une anomalie par équipement en collision
        self.assertEqual(anomalies[0].ident_eq, a.ouvrage.equipements[0].ident)
        self.assertEqual(anomalies[0].repere, "XTSTRV01MV01")

    def test_programmes_differents_aucune_anomalie(self):
        a = _session(self.cat, "XTST", "PRG_A")
        self.assertEqual(homonymes(a.ouvrage, a.catalogue, self._autre(_session(self.cat, "XTSB", "PRG_B"))), [])

    def test_sans_programme_declare_alerte_et_non_erreur(self):
        vide = _session(self.cat, "XTST", "")
        anomalies = homonymes(vide.ouvrage, vide.catalogue, self._autre(_session(self.cat, "XTSB", "  ")))
        self.assertEqual(len(anomalies), 1)
        self.assertEqual((anomalies[0].niveau, anomalies[0].etape, anomalies[0].code),
                         ("Alerte", "Variables", "R-NOM-05"))
        self.assertIn("TS_RV01MV01_OUV", anomalies[0].message)
        self.assertIn("déclarez le nom du programme automate", anomalies[0].message)
        self.assertEqual(anomalies[0].ident_eq, vide.ouvrage.equipements[0].ident)

    def test_sans_programme_d_un_seul_cote_aucune_anomalie(self):
        vide = _session(self.cat, "XTST", "")
        self.assertEqual(homonymes(vide.ouvrage, vide.catalogue, self._autre(_session(self.cat, "XTSB", "PRG"))), [])
        prg = _session(self.cat, "XTST", "PRG")
        self.assertEqual(homonymes(prg.ouvrage, prg.catalogue, self._autre(_session(self.cat, "XTSB", ""))), [])

    def test_sans_programme_lieu_dans_le_nom_aucune_alerte(self):
        a = _session(self.cat, "XTST", "", lieu_dans_le_nom=True)
        b = _session(self.cat, "XTSB", "")
        self.assertEqual(homonymes(a.ouvrage, a.catalogue, self._autre(b)), [])
        c = _session(self.cat, "XTST", "")
        d = _session(self.cat, "XTSB", "", lieu_dans_le_nom=True)
        self.assertEqual(homonymes(c.ouvrage, c.catalogue, self._autre(d)), [])

    def test_lieu_dans_le_nom_pas_de_collision(self):
        a = _session(self.cat, "XTST", "PRG", lieu_dans_le_nom=True)
        b = _session(self.cat, "XTSB", "PRG", lieu_dans_le_nom=True)
        self.assertEqual(homonymes(a.ouvrage, a.catalogue, self._autre(b)), [])

    def test_le_meme_ouvrage_n_est_pas_son_propre_homonyme(self):
        a = _session(self.cat, "XTST", "PRG")
        self.assertEqual(homonymes(a.ouvrage, a.catalogue, [("XTSTRV01", a.ouvrage, a.catalogue)]), [])


class TestSessionHomonymes(unittest.TestCase):
    def setUp(self):
        self.env = os.environ.get("SOREP_DATA_DIR")
        self.dossier = tempfile.mkdtemp()
        os.environ["SOREP_DATA_DIR"] = self.dossier
        self.cat = Catalogue.charger(chemins.fichier_catalogue_origine())

    def tearDown(self):
        if self.env is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.env
        shutil.rmtree(self.dossier, ignore_errors=True)

    def test_ouvrages_enregistres_lus_sans_modification(self):
        projets = Path(chemins.dossier_projets())
        projets.mkdir(parents=True, exist_ok=True)
        b = _session(self.cat, "XTSB", "PRG")
        chemin_b = projets / "XTSBRV01.ouvrage.json"
        b.enregistrer(str(chemin_b))
        octets = chemin_b.read_bytes()
        a = _session(self.cat, "XTST", "PRG")
        chemin_a = projets / "XTSTRV01.ouvrage.json"
        a.enregistrer(str(chemin_a))
        anomalies = a.anomalies_homonymes()
        self.assertTrue(anomalies)
        self.assertTrue(any("XTSBRV01" in x.message for x in anomalies))
        self.assertFalse(any("XTSTRV01 " in x.message for x in anomalies))   # pas contre lui-même
        self.assertEqual(chemin_b.read_bytes(), octets)
        (projets / "illisible.ouvrage.json").write_text("{", encoding="utf-8")
        self.assertEqual(len(a.anomalies_homonymes()), len(anomalies))      # fichier illisible ignoré

    def test_sans_programme_alerte_au_parcours_a_verifier(self):
        projets = Path(chemins.dossier_projets())
        projets.mkdir(parents=True, exist_ok=True)
        _session(self.cat, "XTSB", "").enregistrer(str(projets / "XTSBRV01.ouvrage.json"))
        a = _session(self.cat, "XTST", "")
        a.enregistrer(str(projets / "XTSTRV01.ouvrage.json"))
        anomalies = a.anomalies_homonymes()
        self.assertEqual([x.niveau for x in anomalies], ["Alerte"])
        etape = next(e for e in a.parcours() if e["vue"] == "variables")
        points = [p for p in etape["bloquants"] + etape["a_verifier"] if p["code"] == "homonyme"]
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0]["gravite"], "à vérifier")
        self.assertTrue(points[0]["message"].startswith("XTSTRV01MV01 : "))
        self.assertEqual(points[0]["ident_eq"], a.ouvrage.equipements[0].ident)

    def test_recette_web_signale_l_homonyme(self):
        from sorep_web.serveur import Application
        projets = Path(chemins.dossier_projets())
        projets.mkdir(parents=True, exist_ok=True)
        _session(self.cat, "XTSB", "PRG").enregistrer(str(projets / "XTSBRV01.ouvrage.json"))
        app = Application()
        app.s = _session(self.cat, "XTST", "PRG")
        app.ouvert = True
        controles = [c for c in app.recette_web({})["controles"] if "même programme automate" in c["message"]]
        self.assertEqual(len(controles), 1)
        self.assertEqual((controles[0]["niveau"], controles[0]["etape"]), ("Erreur", "Variables"))


if __name__ == "__main__":
    unittest.main()
