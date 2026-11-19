"""Standards d'ingénierie (19/11/2026) : un standard est un assemblage de briques, copié dans l'ouvrage à sa création ;
un ouvrage existant n'est jamais modifié quand le standard évolue, OGIAS signale l'écart. Ouvrages fictifs (XTST)."""
from dataclasses import asdict
import json
import re
import os
import tempfile
import unittest
from unittest import mock

from genvar import charte, standards
from genvar.session import RegleMetier
from genvar.modele import ORDRE_ZONES, PLAN_DEFAUT, Ouvrage, zone
from tests.test_coherence import nouvelle


class AvecDossier(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.addCleanup(self.dossier.cleanup)
        patch = mock.patch.dict(os.environ, {"SOREP_DATA_DIR": self.dossier.name})
        patch.start()
        self.addCleanup(patch.stop)


class TestBibliotheque(AvecDossier):
    def test_standard_initial_cree_au_premier_acces(self):
        self.assertFalse(os.path.exists(standards.chemin()))
        liste = standards.lire()
        self.assertEqual([s["ident"] for s in liste], [standards.IDENT_INITIAL])
        s = liste[0]
        self.assertEqual(set(s["briques"]), set(standards.FAMILLES))
        self.assertEqual(s["briques"]["adressage"]["plages"], {f: list(PLAN_DEFAUT[f]) for f in ORDRE_ZONES})
        self.assertEqual((s["briques"]["outils"]["supervision"], s["briques"]["outils"]["ihm"]), ("TOPKAPI", ""))
        self.assertTrue(os.path.exists(standards.chemin()))
        self.assertEqual(standards.lire(), liste)                       # relu tel quel, pas recréé

    def test_fichier_illisible_n_est_pas_ecrase(self):
        os.makedirs(os.path.dirname(standards.chemin()), exist_ok=True)
        with open(standards.chemin(), "w", encoding="utf-8") as fh:
            fh.write('{"standards": []}')
        with self.assertRaises(ValueError):
            standards.lire()
        with open(standards.chemin(), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), {"standards": []})

    def test_trouver(self):
        self.assertEqual(standards.trouver(standards.IDENT_INITIAL)["nom"], "Standard initial")
        self.assertIsNone(standards.trouver("client-inexistant"))


class TestApplication(AvecDossier):
    def test_standard_initial_reproduit_le_comportement_d_avant(self):
        s = nouvelle()
        avant = (dict((f, zone(s.ouvrage, f)) for f in ORDRE_ZONES), s.ouvrage.decalage_modbus, s.ouvrage.supervision, s.ouvrage.ihm)
        self.assertEqual(standards.appliquer(s, standards.trouver(standards.IDENT_INITIAL)), [])
        ref = s.ouvrage.standard
        apres = (dict((f, zone(s.ouvrage, f)) for f in ORDRE_ZONES), s.ouvrage.decalage_modbus, s.ouvrage.supervision, s.ouvrage.ihm)
        self.assertEqual(avant, apres)
        self.assertEqual((ref["ident"], ref["version"]), (standards.IDENT_INITIAL, 1))
        self.assertEqual(standards.ecarts(s.ouvrage), [])
        self.assertEqual(Ouvrage.depuis_dict(asdict(s.ouvrage)).standard["ident"], standards.IDENT_INITIAL)

    def test_copie_independante_du_standard(self):
        """L'ouvrage garde sa copie : une évolution du standard ne le modifie pas, l'écart local est signalé."""
        s = nouvelle()
        choisi = standards.trouver(standards.IDENT_INITIAL)
        standards.appliquer(s, choisi)
        choisi["briques"]["outils"]["supervision"] = "Autre supervision fictive"
        choisi["version"] = 2
        standards.ecrire([choisi])
        self.assertEqual(s.ouvrage.supervision, "TOPKAPI")
        self.assertEqual(s.ouvrage.standard["version"], 1)
        self.assertEqual(s.ouvrage.standard["briques"]["outils"]["supervision"], "TOPKAPI")
        s.ouvrage.ihm = "Vijeo Designer"
        self.assertEqual(standards.ecarts(s.ouvrage), ["IHM : Vijeo Designer (standard : aucune)"])

    def test_tout_ou_rien(self):
        s = nouvelle()
        mauvais = standards.standard_initial()
        mauvais["briques"]["adressage"]["plages"]["TS"] = [3000, 3999]          # recouvre TR : refusé
        sup_avant = s.ouvrage.supervision
        with self.assertRaises(Exception):
            standards.appliquer(s, mauvais)
        self.assertEqual(zone(s.ouvrage, "TS"), tuple(PLAN_DEFAUT["TS"]))
        self.assertEqual((s.ouvrage.standard, s.ouvrage.supervision), ({}, sup_avant))

    def test_ouvrage_anterieur_sans_standard(self):
        self.assertEqual(Ouvrage.depuis_dict({"lieu": "XTST"}).standard, {})
        self.assertEqual(standards.ecarts(Ouvrage()), [])



class TestBibliothequeEtVersions(AvecDossier):
    def plages(self, **modif):
        return {f: list(PLAN_DEFAUT[f]) for f in ORDRE_ZONES} | modif

    def test_bibliotheque_initiale(self):
        b = standards.bibliotheque()
        self.assertEqual([x["ident"] for x in b["adressage"]], ["adressage-defaut"])
        self.assertEqual([x["ident"] for x in b["outils"]], ["outils-topkapi"])
        self.assertEqual(standards.emplois_briques(), {"charte:charte-ogias": 1, "adressage:adressage-defaut": 1,
                                                      "outils:outils-topkapi": 1})

    def test_fichier_de_l_etape_1_repris_sans_perte(self):
        initial = standards.standard_initial()
        for f in ("adressage", "outils", "referentiel", "charte"):
            initial["briques"][f].pop("ident")
        os.makedirs(os.path.dirname(standards.chemin()), exist_ok=True)
        with open(standards.chemin(), "w", encoding="utf-8") as fh:
            json.dump({"version": 1, "standards": [initial]}, fh)
        self.assertEqual([x["ident"] for x in standards.bibliotheque()["adressage"]], ["adressage-defaut"])
        self.assertEqual(standards.lire()[0]["briques"]["charte"]["ident"], "charte-ogias")

    def test_brique_controlee_comme_une_saisie(self):
        with self.assertRaisesRegex(RegleMetier, "recouvrement"):
            standards.creer_brique("adressage", "Plan client B", {"plages": self.plages(TS=[2000, 2100])})
        with self.assertRaisesRegex(RegleMetier, "Décalage"):
            standards.creer_brique("adressage", "Plan client B", {"plages": self.plages(), "decalage_modbus": "x"})
        with self.assertRaisesRegex(RegleMetier, "déjà le nom"):
            standards.creer_brique("adressage", "plan mémoire PAR DÉFAUT", {"plages": self.plages()})
        b, alertes = standards.creer_brique("adressage", "Plan client B", {"plages": self.plages(TS=[5000, 5999]), "decalage_modbus": -1})
        self.assertEqual((b["ident"], b["plages"]["TS"], b["decalage_modbus"], alertes), ("plan-client-b", [5000, 5999], -1, []))
        self.assertEqual(len(standards.bibliotheque()["adressage"]), 2)

    def test_standard_partage_des_briques_et_versions(self):
        standards.creer_brique("outils", "Sans supervision", {"supervision": "", "ihm": "Vijeo Designer"})
        s = standards.creer_standard("Client B", "Standard fictif", {"adressage": "adressage-defaut", "outils": "sans-supervision"})
        self.assertEqual((s["ident"], s["version"], s["briques"]["outils"]["ihm"]), ("client-b", 1, "Vijeo Designer"))
        self.assertEqual(standards.emplois_briques()["adressage:adressage-defaut"], 2)       # brique partagée
        with self.assertRaisesRegex(RegleMetier, "brique"):
            standards.creer_standard("Client C", "", {"adressage": "inexistante", "outils": "outils-topkapi"})
        with self.assertRaisesRegex(RegleMetier, "motif"):
            standards.reviser_standard("client-b", {"adressage": "adressage-defaut", "outils": "outils-topkapi"}, None, "")
        with self.assertRaisesRegex(RegleMetier, "Aucun changement"):
            standards.reviser_standard("client-b", {"adressage": "adressage-defaut", "outils": "sans-supervision"}, None, "essai")
        r = standards.reviser_standard("client-b", {"adressage": "adressage-defaut", "outils": "outils-topkapi"}, None, "TOPKAPI retenu")
        self.assertEqual((r["version"], r["historique"][0]["version"], r["historique"][0]["briques"]["outils"]), (2, 1, "Sans supervision"))

    def test_archivage(self):
        with self.assertRaisesRegex(RegleMetier, "au moins un standard actif"):
            standards.changer_statut(standards.IDENT_INITIAL, "archivé")
        standards.creer_standard("Client B", "", {"adressage": "adressage-defaut", "outils": "outils-topkapi"})
        self.assertEqual(standards.changer_statut(standards.IDENT_INITIAL, "archivé")["statut"], "archivé")

    def test_application_a_un_ouvrage_existant(self):
        """Sur demande : réglages remplacés, adresses validées inchangées, référence mise à jour."""
        s = nouvelle()
        standards.appliquer(s, standards.trouver(standards.IDENT_INITIAL))
        standards.creer_brique("adressage", "Plan client B", {"plages": self.plages(TS=[5000, 5999])})
        b = standards.creer_standard("Client B", "", {"adressage": "plan-client-b", "outils": "outils-topkapi"})
        apercu = standards.ecarts(s.ouvrage, b["briques"])
        self.assertEqual(apercu, ["Plage TS : %MW1000 à %MW1999 (standard : %MW5000 à %MW5999)"])
        standards.appliquer(s, b)
        self.assertEqual(zone(s.ouvrage, "TS"), (5000, 5999))
        self.assertEqual((s.ouvrage.standard["ident"], standards.ecarts(s.ouvrage)), ("client-b", []))



class TestChartesReglables(AvecDossier):
    CLIENT = {"ouvrage": [{"type": "texte", "valeur": "EAU"}, {"type": "type_ouvrage", "longueur": 3, "caracteres": "lettres"},
                          {"type": "numero_ouvrage", "longueur": 3}],
              "equipement": [{"type": "sous_ensemble", "longueur": 2, "caracteres": "chiffres"}, {"type": "equipement"}],
              "separateur": "_"}

    def test_charte_ogias_inchangee(self):
        self.assertEqual(charte.controler(charte.CHARTE_OGIAS), charte.CHARTE_OGIAS)
        self.assertEqual(charte.exemple(charte.CHARTE_OGIAS), {"ouvrage": "XTSTRV01", "equipement": "XTSTRV01PM01"})
        self.assertTrue(charte.applicable(charte.CHARTE_OGIAS))
        self.assertEqual(charte.motif_champ(charte.CHARTE_OGIAS, "lieu"), "[A-Z0-9]{4}")
        b = standards.bibliotheque()["charte"]
        self.assertEqual([x["ident"] for x in b], ["charte-ogias"])

    def test_charte_client_personnalisee(self):
        c = charte.controler(self.CLIENT)
        self.assertEqual(charte.exemple(c), {"ouvrage": "EAU_RVR_001", "equipement": "EAU_RVR_001_00_PM01"})
        self.assertFalse(charte.applicable(c))
        self.assertIsNone(charte.motif_champ(c, "lieu"))                     # pas de lieu dans cette charte
        self.assertTrue(re.fullmatch(charte.motif_champ(c, "numero_ouvrage"), "007"))
        self.assertFalse(re.fullmatch(charte.motif_champ(c, "numero_ouvrage"), "000"))

    def test_charte_refusee(self):
        cas = {"segment inconnu": {**self.CLIENT, "ouvrage": [{"type": "autre"}]},
               "doublon": {**self.CLIENT, "ouvrage": [*self.CLIENT["ouvrage"], {"type": "numero_ouvrage", "longueur": 2}]},
               "sans type ni numéro": {**self.CLIENT, "ouvrage": [{"type": "lieu", "longueur": 4, "caracteres": "lettres"}]},
               "sans équipement": {**self.CLIENT, "equipement": [{"type": "texte", "valeur": "X"}]},
               "texte invalide": {**self.CLIENT, "ouvrage": [{"type": "texte", "valeur": "é!"}, {"type": "numero_ouvrage", "longueur": 2}]},
               "longueur": {**self.CLIENT, "ouvrage": [{"type": "numero_ouvrage", "longueur": 9}]},
               "séparateur": {**self.CLIENT, "separateur": "/"},
               "trop long": {**self.CLIENT, "ouvrage": [*({"type": "texte", "valeur": "ABCDEFGH"} for _ in range(4)),
                                                        {"type": "numero_ouvrage", "longueur": 2}]}}
        for nom, c in cas.items():
            with self.subTest(nom), self.assertRaises(RegleMetier):
                charte.controler(c)

    def test_standard_avec_charte_client_ne_cree_pas_d_ouvrage(self):
        """Tant que les repères ne sont pas fabriqués selon une autre charte : refus clair, rien n'est modifié."""
        b, alertes = standards.creer_brique("charte", "Charte client fictif", self.CLIENT)
        self.assertTrue(alertes and "pas encore" in alertes[0])
        s = standards.creer_standard("Client fictif", "", {"charte": b["ident"], "adressage": "adressage-defaut",
                                                         "outils": "outils-topkapi"})
        session = nouvelle()
        avant = asdict(session.ouvrage)
        with self.assertRaisesRegex(RegleMetier, "pas encore"):
            standards.appliquer(session, s)
        self.assertEqual(asdict(session.ouvrage), avant)


if __name__ == "__main__":
    unittest.main()
