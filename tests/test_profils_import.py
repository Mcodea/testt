"""Profils d'import réutilisables (cahier V1-5-04). Ouvrage fictif (XTST), fichiers fictifs."""
import base64
import os
import tempfile
import unittest

from genvar import profils_import
from sorep_web.serveur import Application, RegleMetier

FICHIER = ("Poste;Désignation ouvrage;Nature\r\n"
           "XTSTRV47PM01;Pompe de relevage;PM\r\n").encode("utf-8")


class TestProfilsImport(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-profils-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        app = self.app = Application()
        app.appeler("nouveau", {"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.appeler("fiche_ouvrage", {"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "47", "libelle": "Essai profils",
            "automate": "Sch - M580", "revision": "A"}})

    def tearDown(self):
        self.app._clear_inbound()
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def apercu(self, **extra):
        return self.app.inbound_preview({"nature": "inventaire", "nom": "client.csv", "contenu": base64.b64encode(FICHIER).decode(), **extra})

    def profil(self):
        r = self.app.profils_import_action({"action": "enregistrer", "nom": "Fichier du client", "nature": "inventaire",
                                            "correspondances": {"repere": "Poste", "libelle": "Désignation ouvrage", "type": "Nature"}})
        return r["ident"]

    def test_fichier_inconnu_refuse_puis_reconnu_avec_le_profil(self):
        with self.assertRaisesRegex(Exception, "colonnes"):
            self.apercu()
        ident = self.profil()
        r = self.apercu(profil=ident)
        self.assertEqual(r["statistiques"]["erreurs"], 0)
        self.assertEqual(r["statistiques"]["a_creer"], 1)           # l'aperçu reste obligatoire : rien n'est écrit
        self.assertEqual(self.app.s.ouvrage.equipements, [])

    def test_le_profil_est_conserve_d_une_session_a_l_autre(self):
        ident = self.profil()
        self.assertEqual([p["ident"] for p in profils_import.lister("inventaire")], [ident])
        self.assertEqual(profils_import.lister("variables_existantes"), [])
        self.assertEqual(self.app.profils_import_web({})["profils"][0]["correspondances"]["repere"], "Poste")

    def test_refus_motives(self):
        cas = [({"nom": "x", "nature": "inventaire", "correspondances": {"repere": "A"}}, "3 à 60"),
               ({"nom": "Profil", "nature": "inconnue", "correspondances": {}}, "Nature"),
               ({"nom": "Profil", "nature": "inventaire", "correspondances": {"repere": "A", "pirate": "B"}}, "Champ inconnu"),
               ({"nom": "Profil", "nature": "inventaire", "correspondances": {"type": "A"}}, "obligatoires"),
               ({"nom": "Profil", "nature": "inventaire", "correspondances": {"repere": "A", "type": "a"}}, "deux champs"),
               ({"nom": "Profil", "nature": "inventaire", "correspondances": {"repere": "A" * 200}}, "trop long")]
        for corps, motif in cas:
            with self.subTest(motif=motif), self.assertRaisesRegex(RegleMetier, motif):
                self.app.profils_import_action({"action": "enregistrer", **corps})
        self.assertEqual(profils_import.lister(), [])

    def test_doublon_suppression_et_profil_d_une_autre_nature(self):
        ident = self.profil()
        with self.assertRaisesRegex(RegleMetier, "existe déjà"):
            self.profil()
        with self.assertRaisesRegex(RegleMetier, "introuvable pour cette nature"):
            self.app.inbound_preview({"nature": "variables_existantes", "nom": "client.csv",
                                      "contenu": base64.b64encode(FICHIER).decode(), "profil": ident})
        for faux in ("../x", "zzzzzzzzzzzz", 5):
            with self.subTest(profil=faux), self.assertRaises(RegleMetier):
                self.apercu(profil=faux)
        self.app.profils_import_action({"action": "supprimer", "ident": ident})
        self.assertEqual(profils_import.lister(), [])
        with self.assertRaisesRegex(RegleMetier, "introuvable"):
            self.app.profils_import_action({"action": "supprimer", "ident": ident})

    def test_entetes_candidats_pour_decrire_les_colonnes(self):
        r = self.app.profils_import_action({"action": "entetes", "nom": "client.csv", "contenu": base64.b64encode(FICHIER).decode()})
        ligne = r["feuilles"][0]["lignes"][0]
        self.assertEqual(ligne["cellules"], ["Poste", "Désignation ouvrage", "Nature"])
        with self.assertRaisesRegex(RegleMetier, "invalide"):
            self.app.profils_import_action({"action": "entetes", "nom": "client.csv", "contenu": "pas du base64 !"})
        with self.assertRaisesRegex(RegleMetier, "Format accepté"):
            self.app.profils_import_action({"action": "entetes", "nom": "client.exe", "contenu": ""})

    def test_index_corrompu_jamais_ecrase(self):
        os.makedirs(profils_import.dossier(), exist_ok=True)
        with open(os.path.join(profils_import.dossier(), "index.json"), "w", encoding="utf-8") as f:
            f.write('{"profils": 5}')
        with self.assertRaises(RegleMetier):
            self.profil()


if __name__ == "__main__":
    unittest.main()
