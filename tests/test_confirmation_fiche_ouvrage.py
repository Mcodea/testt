"""Recette indépendante : un formulaire ne doit jamais créer un fichier implicitement."""
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from genvar import projets
from genvar.session import RegleMetier
from sorep_web.serveur import Application


def donnees(lieu="MRGS", code="RV", libelle="Ouvrage de recette fictif", **kw):
    d = {"lieu": lieu, "code_ouvrage": code, "numero_ouvrage": "01", "libelle": libelle,
         "automate": "M580", "localisation": "", "communication": "Modbus TCP",
         "revision": "A"}
    d.update(kw)
    return d


class TestConfirmationFicheOuvrage(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SOREP_DATA_DIR": self.temp.name})
        self.env.start()
        self.app = Application()
        self.app.nouveau({"mode": "Neuf"})

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def save(self, action="creer", **kw):
        return self.app.fiche_ouvrage({"action": action, "identification": donnees(**kw)})

    def test_creation_non_implicite(self):
        self.app.identifier_selection({"champ": "lieu", "valeur": "MRGS"})
        self.app.identifier_type({"code": "RV"})
        self.app.definir({"champ": "libelle", "valeur": "Test non confirmé"})
        self.assertTrue(self.app.ouvrage({})["creation_en_attente"])
        self.assertEqual(projets.lister(), [])
        self.assertFalse(self.app.s.chemin)

    def test_annulation_n_enregistre_rien(self):
        self.app.identifier_selection({"champ": "lieu", "valeur": "MRGS"})
        self.app.identifier_type({"code": "RV"})
        self.app.fermer({})
        self.assertEqual(projets.lister(), [])
        self.assertFalse(self.app.ouvert)

    def test_creation_refuse_une_fiche_incomplete(self):
        with self.assertRaisesRegex(RegleMetier, "libellé"):
            self.save(libelle="")
        self.assertEqual(projets.lister(), [])
        self.assertTrue(self.app.ouvrage({})["creation_en_attente"])

    def test_enregistrer_brouillon_incomplet(self):
        r = self.save("brouillon", lieu="", code="", libelle="")
        self.assertEqual(r["statut"], "Brouillon")
        self.assertTrue(Path(r["chemin"]).is_file())
        self.assertEqual(len(projets.lister()), 1)
        self.assertFalse(self.app.ouvrage({})["creation_en_attente"])
        self.assertTrue(self.app.ouvrage({})["en_conception"])

    def test_brouillon_reouvrable_et_confirmation(self):
        premier = self.save("brouillon", lieu="", code="", libelle="Esquisse")
        self.app.fermer({})
        self.app.ouvrir({"chemin": premier["chemin"]})
        self.assertEqual(self.app.ouvrage({})["identification"]["statut"], "Brouillon")
        fin = self.save("creer")
        self.assertEqual(fin["statut"], "En cours")
        self.assertFalse(self.app.ouvrage({})["en_conception"])
        self.assertNotEqual(fin["chemin"], premier["chemin"])
        self.assertEqual(len(projets.lister()), 1)
        self.assertEqual(len(projets.lister_corbeille()), 1)  # brouillon récupérable

    def test_creer_ouvrage_explicite(self):
        fin = self.save("creer")
        self.assertEqual(fin["statut"], "En cours")
        self.assertEqual(self.app.ouvrage({})["prefixe"], "MRGSRV01")
        self.assertTrue(Path(fin["chemin"]).is_file())
        self.assertFalse(self.app.ouvrage({})["creation_en_attente"])
        self.assertEqual(len(projets.lister()), 1)

    def test_double_creation_et_modification_interdites(self):
        self.save("creer")
        with self.assertRaisesRegex(RegleMetier, "existe déjà"):
            self.save("creer")
        self.assertEqual(len(projets.lister()), 1)

    def test_code_reutilise_refuse_sans_suffixe_invente(self):
        self.save("creer")
        app2 = Application()
        app2.nouveau({"mode": "Neuf"})
        with self.assertRaisesRegex(RegleMetier, "utilise déjà"):
            app2.fiche_ouvrage({"action": "creer", "identification": donnees(libelle="Second réservoir fictif")})
        self.assertEqual(len(projets.lister()), 1)
        self.assertTrue(app2.ouvrage({})["creation_en_attente"])

    def test_mise_a_jour_apres_validation_explicite_seulement(self):
        fin = self.save("creer")
        app2 = Application()
        app2.ouvrir({"chemin": fin["chemin"]})
        self.assertEqual(app2.ouvrage({})["identification"]["libelle"], donnees()["libelle"])
        # La simple consultation ne modifie pas le fichier.
        contenu = Path(fin["chemin"]).read_bytes()
        app2.ouvrage({})
        self.assertEqual(contenu, Path(fin["chemin"]).read_bytes())
        app2.fiche_ouvrage({"action": "modifier", "identification": donnees(libelle="Libellé corrigé")})
        self.assertEqual(app2.ouvrage({})["identification"]["libelle"], "Libellé corrigé")
        self.assertEqual(len(projets.lister()), 1)

    def test_rejet_n_ecrase_pas_ouvrage_existant(self):
        fin = self.save("creer")
        avant = Path(fin["chemin"]).read_bytes()
        with self.assertRaisesRegex(RegleMetier, "Révision invalide"):
            self.app.fiche_ouvrage({"action": "modifier", "identification": donnees(revision="INVALID")})
        self.assertEqual(avant, Path(fin["chemin"]).read_bytes())
        self.assertEqual(self.app.ouvrage({})["identification"]["revision"], "A")

    def test_codes_alternatifs_et_protocoles_controles(self):
        with self.assertRaisesRegex(RegleMetier, "protocole"):
            self.save(communication="FTP inconnu")
        with self.assertRaisesRegex(RegleMetier, "Lieu absent"):
            self.save(lieu="XXXX")
        with self.assertRaisesRegex(RegleMetier, "Code ouvrage"):
            self.save(code="ZZ")
        self.assertEqual(projets.lister(), [])

    def test_brouillon_et_ouvrage_existants_ne_sont_pas_valides_techniquement(self):
        self.assertEqual(self.save("brouillon")["statut"], "Brouillon")
        self.assertEqual(self.save("creer")["statut"], "En cours")
        self.assertNotEqual(self.app.ouvrage({})["identification"]["statut"], "Validé")


if __name__ == "__main__":
    unittest.main()
