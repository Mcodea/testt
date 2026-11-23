"""Données séparées du programme et mise à jour sans perte depuis un ouvrage des versions antérieures (cahier V1-9-04).

L'ouvrage « ancien » est fabriqué en retirant d'un ouvrage fictif tout ce que les versions 0.30 / 0.31 ne
connaissaient pas (indices, ordre d'export, zones de fin, référentiel figé…) : il doit s'ouvrir, garder ses adresses
validées et ses noms, et ne jamais être réécrit par la seule ouverture. Ouvrage fictif (XTST)."""
import hashlib
import json
import os
import tempfile
import unittest

from genvar import adressage
from genvar.modele import Ouvrage
from sorep_web.serveur import Application

NOUVEAUTES_OUVRAGE = ("indices", "zones_fin", "catalogue_snapshot", "modeles_snapshot", "deja_valide", "deja_exporte",
                      "standard", "essais", "groupes_secours", "groupes_secours_refuses", "journal_referentiel")
NOUVEAUTES_EQUIPEMENT = ("ordre_export", "attributs", "lignes_ajoutees", "lignes_modifiees", "lignes_retirees")


class TestMiseAJourDepuisAnciennesVersions(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-maj-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        app = self.app = Application()
        app.appeler("nouveau", {"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.appeler("fiche_ouvrage", {"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "48", "libelle": "Essai mise à jour",
            "automate": "Sch - M580", "revision": "A"}})
        for t, n in (("PM", "01"), ("HV", "02")):
            i = app.appeler("ajouter_equipement", {"type": t, "numero": n, "se": "00"})["ident"]
            app.appeler("decider_proposition", {"ident_eq": i, "decision": "retenir"})
        s = app.s
        s.appliquer_adressage(adressage.calculer(s).empreinte, ("automate",))
        s.valider_affectations("automate", [(v.ident_eq, v.cle) for v in s.variables() if v.adresse])
        app._sauver()
        self.chemin = s.chemin
        self.adresses = {v.nom: (v.adresse, v.adresse_validee) for v in s.variables()}
        self.assertTrue(all(a for a, _ in self.adresses.values()))

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def fichier_ancien(self):
        with open(self.chemin, encoding="utf-8") as f:
            contenu = json.load(f)
        o = contenu["ouvrage"]
        for cle in NOUVEAUTES_OUVRAGE:
            o.pop(cle, None)
        for eq in o["equipements"]:
            for cle in NOUVEAUTES_EQUIPEMENT:
                eq.pop(cle, None)
        o["zones"] = {"TS": 100, "TC": 400, "TM": 600, "TR": 900, "RTR": 1100, "CP": 1300}      # forme 0.3 : début seul
        chemin = self.chemin + ".v030"
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump(contenu, f, ensure_ascii=False)
        return chemin

    def test_ancien_ouvrage_s_ouvre_et_garde_noms_et_adresses_validees(self):
        o = Ouvrage.ouvrir(self.fichier_ancien())
        self.assertEqual(o.revision, "A")
        self.assertEqual(o.indices, [])
        self.assertTrue(all(e.ordre_export == [] for e in o.equipements))
        self.assertEqual(set(o.zones_fin), set(o.zones))
        for e in o.equipements:
            self.assertIn(e.type, ("PM", "HV"))
        # les adresses d'origine sont inchangées
        adresses = {a: v for e in o.equipements for a, v in e.adresses.items()}
        original = Ouvrage.ouvrir(self.chemin)
        attendu = {a: v for e in original.equipements for a, v in e.adresses.items()}
        self.assertEqual(adresses, attendu)
        self.assertTrue(adresses)

    def test_ouvrir_ne_reecrit_jamais_le_fichier(self):
        ancien = self.fichier_ancien()
        avant = hashlib.sha256(open(ancien, "rb").read()).hexdigest()
        Ouvrage.ouvrir(ancien)
        self.assertEqual(hashlib.sha256(open(ancien, "rb").read()).hexdigest(), avant)

    def test_ouverture_par_l_application_puis_enregistrement_garde_les_adresses(self):
        ancien = self.fichier_ancien()
        app = Application()
        app.appeler("ouvrir", {"chemin": ancien})
        reprises = {v.nom: (v.adresse, v.adresse_validee) for v in app.s.variables()}
        self.assertEqual(reprises, self.adresses)
        app.s.enregistrer(app.s.chemin)
        o = Ouvrage.ouvrir(ancien)
        self.assertTrue(o.equipements)
        app.appeler("fermer", {})

    def test_donnees_separees_du_programme(self):
        from genvar import chemins
        racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dossier = os.path.abspath(chemins.dossier_donnees())
        self.assertEqual(dossier, os.path.abspath(self.donnees.name))
        self.assertFalse(any(dossier.startswith(os.path.join(racine, d)) for d in ("genvar", "sorep_web")))   # hors du programme
        self.assertTrue(os.path.abspath(self.chemin).startswith(dossier))        # les ouvrages vivent dans le dossier de données


if __name__ == "__main__":
    unittest.main()
