"""Interface web : l'API du serveur local, appelée comme le ferait le navigateur (HTTP réel)."""
import base64
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sorep_web.serveur import demarrer
from genvar.referentiel_depot import Depot


class TestInterfaceWeb(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-http-test-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name
        self.serveur, self.url, self.app = demarrer(ouvrir_navigateur=False, port=0)
        self.url = f"http://127.0.0.1:{self.serveur.server_address[1]}/"
        from genvar import modeles
        self.app.s.modeles = modeles.vide()                    # essai sur un référentiel vierge
        self.thread = threading.Thread(target=self.serveur.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.serveur.shutdown()
        self.thread.join(timeout=5)
        self.serveur.server_close()
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def appel(self, chemin, donnees=None):
        req = urllib.request.Request(self.url + chemin.lstrip("/"),
                                     data=None if donnees is None else json.dumps(donnees).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_z_communes_reference_et_selection_http(self):
        """Test bout-en-bout de la liste préchargée via l'API web, sans ouvrage réel."""
        code, resultat = self.appel("/api/listes-ouvrage")
        self.assertEqual(code, 200)
        self.assertGreaterEqual(len(resultat["lieux"]), 15)
        self.assertEqual(sum(x["regie"] == "ESB" for x in resultat["lieux"]), 11)
        self.assertEqual(sum(x["regie"] == "RESO" for x in resultat["lieux"]), 4)
        self.assertEqual(self.appel("/api/nouveau", {"mode": "Neuf"})[0], 200)
        self.assertEqual(self.appel("/api/identification/selection", {"champ":"lieu", "valeur":"MRGS"})[0], 200)
        self.assertEqual(self.appel("/api/identification/type", {"code":"RV"})[0], 200)
        code, ouvrage = self.appel("/api/ouvrage")
        self.assertEqual((ouvrage["identification"]["lieu"], ouvrage["prefixe"]), ("MRGS", "MRGSRV"))
        self.assertEqual(self.appel("/api/accueil")[1]["ouvrages"], [])  # aucune création implicite
        self.assertEqual(self.appel("/api/fiche-ouvrage", {"action": "creer", "identification": {
            "lieu":"MRGS", "code_ouvrage":"RV", "numero_ouvrage":"01", "libelle":"Ouvrage de test", "automate":"",
            "localisation":"", "communication":"", "revision":"A"}})[0], 200)
        ouvrage = self.appel("/api/ouvrage")[1]
        # Nettoyage du projet FICTIF utilisé uniquement par cet essai HTTP.
        self.assertEqual(self.appel("/api/supprimer_ouvrage", {"chemin": ouvrage["chemin"]})[0], 200)

    def test_page_et_parcours_inventaire(self):
        with urllib.request.urlopen(self.url) as r:
            self.assertIn("OGIAS", r.read().decode())
        self.assertEqual(self.appel("/api/accueil")[1]["ouvrages"], [])
        self.assertEqual(self.appel("/api/nouveau", {"mode": "Neuf"})[0], 200)
        # équipement refusé tant que l'ouvrage n'est pas identifié
        code, r = self.appel("/api/equipement/ajouter", {"type": "HV", "se": "11", "numero": "01"})
        self.assertEqual(code, 400)
        self.assertIn("lieu", r["erreur"])
        code, r = self.appel("/api/definir", {"champ": "lieu", "valeur": "M12"})
        self.assertEqual(code, 400)                                     # 4 caractères exigés
        self.assertEqual(self.appel("/api/listes-ouvrage/action", {"action": "ajouter", "groupe": "lieux",
                           "code": "XT25", "libelle": "Lieu fictif"})[0], 200)
        for champ, val in (("lieu", "XT25"), ("code_ouvrage", "RV"), ("libelle", "Réservoir d'essai")):
            self.assertEqual(self.appel("/api/definir", {"champ": champ, "valeur": val})[0], 200)
        self.assertEqual(self.appel("/api/accueil")[1]["ouvrages"], [])
        self.assertEqual(self.appel("/api/fiche-ouvrage", {"action": "creer", "identification": {
            "lieu": "XT25", "code_ouvrage": "RV", "numero_ouvrage": "01", "libelle": "Réservoir d'essai",
            "automate": "", "localisation": "", "communication": "", "revision": "A"}})[0], 200)
        self.assertEqual(self.appel("/api/uf", {"action": "ajouter", "code": "UF01", "libelle": "Stockage", "se": "11"})[0], 200)
        # référentiel : lecture seule, modification dans un brouillon, puis validation et publication
        code, r = self.appel("/api/referentiel/action", {"action": "creer_modele", "type": "HV", "nom": "Vanne 2 FDC", "depuis_catalogue": True})
        self.assertEqual(code, 400)                                       # pas de brouillon : refusé
        self.assertEqual(self.appel("/api/referentiel/cycle/action", {"action": "creer_brouillon"})[0], 200)
        # Le type historique de l'inventaire fictif est ajouté dans le cycle,
        # sans dépendre des types présents dans la ressource livrée du moment.
        brouillon = Depot().brouillon()
        if "A--P" not in brouillon["donnees"]["modeles"]["types"]:
            self.assertEqual(self.appel("/api/referentiel/action", {"action": "creer_type", "code": "A--P",
                                                                   "designation": "Armoire process"})[0], 200)
        code, r = self.appel("/api/referentiel/action", {"action": "creer_modele", "type": "HV", "nom": "Vanne 2 FDC", "depuis_catalogue": True})
        self.assertEqual(code, 200, r)
        vue = self.appel("/api/referentiel/vue?source=brouillon")[1]
        hv = next(t for t in vue["types"] if t["code"] == "HV")
        self.assertTrue(next(m for m in hv["modeles"] if m["nom"] == "Vanne 2 FDC")["lignes"])
        self.assertTrue(vue["nb_modifications"])
        self.assertNotIn("Vanne 2 FDC", self.app.s.modeles["modeles"])   # la révision en service n'a pas changé
        self.assertEqual(self.appel("/api/referentiel/cycle/action", {"action": "publier", "motif": "x", "empreinte": "?"})[0], 400)
        code, r = self.appel("/api/referentiel/cycle/action", {"action": "valider"})
        self.assertEqual(code, 200, r)
        code, p = self.appel("/api/referentiel/cycle/action", {"action": "publier", "motif": "Modèle de vanne à 2 FDC",
                                                                 "empreinte": r["empreinte_validee"]})
        self.assertEqual(code, 200, p)
        self.assertIn("Vanne 2 FDC", self.app.s.modeles["modeles"])
        self.assertTrue(self.appel("/api/modele?nom=Vanne 2 FDC".replace(" ", "%20"))[1]["lignes"])
        code, r = self.appel("/api/equipement/ajouter", {"type": "HV", "modele": "Vanne 2 FDC", "se": "11", "numero": "01",
                                                        "libelle": "Vanne", "uf": "UF01"})
        self.assertEqual(code, 200, r)
        ident = r["ident"]
        code, eq = self.appel("/api/equipement?ident=" + ident)
        self.assertEqual(eq["pcf"], "XT25RV01HV01")      # charte du 9 novembre : sans sous-ensemble
        self.assertGreater(len(eq["informations"]), 0)
        # lignes de l'équipement : ajouter, modifier, supprimer
        self.assertEqual(self.appel("/api/equipement/ligne", {"action": "ajouter", "ident_eq": ident,
                         "champs": {"role": "ALA", "libelle": "Temps de manœuvre trop long", "suffixe": "TML"}})[0], 200)
        eq = self.appel("/api/equipement?ident=" + ident)[1]
        tml = next(i for i in eq["informations"] if i["suffixe"] == "TML")
        self.assertEqual(tml["mnemonique"], "ALA_RV01HV01_TML")
        self.assertEqual(self.appel("/api/equipement/ligne", {"action": "modifier", "ident_eq": ident, "id": tml["id"],
                         "champs": {"role": "ALA", "libelle": "TML", "suffixe": "TML_MAN"}})[0], 200)
        premiere = eq["informations"][0]["id"]
        self.assertEqual(self.appel("/api/equipement/ligne", {"action": "supprimer", "ident_eq": ident, "ids": [premiere]})[0], 200)
        eq = self.appel("/api/equipement?ident=" + ident)[1]
        self.assertNotIn(premiere, [i["id"] for i in eq["informations"]])
        self.assertIn("TML_MAN", [i["suffixe"] for i in eq["informations"]])
        # étape 2 : l'accès E/S est bloqué tant que le paramétrage des équipements n'est pas validé.
        self.assertEqual(self.appel("/api/es")[0], 400)
        # HV à deux fins de course : discordance et position intermédiaire proposées, à décider.
        fiche = self.appel("/api/equipement?ident=" + ident)[1]
        f = {x["cle"]: x for x in fiche["fonctionnelles"]}
        self.assertEqual((f["TS_DISC"]["etat"], f["TS_DISC"]["sources"]), ("proposée", ["ES_FDC_FER", "ES_FDC_OUV"]))
        self.assertEqual(fiche["a_decider"], 2)
        self.assertEqual(self.appel("/api/equipement/valider", {"idents": [ident], "valide": True})[0], 400)
        self.assertEqual(self.appel("/api/equipement/proposition", {"ident_eq": ident, "cle": "TS_INT",
                                                                    "decision": "ecarter"})[0], 400)   # motif exigé
        self.assertEqual(self.appel("/api/equipement/proposition", {"ident_eq": ident, "cle": "TS_INT",
                         "decision": "ecarter", "motif": "vanne quart de tour sans arrêt intermédiaire"})[0], 200)
        self.assertEqual(self.appel("/api/equipement/proposition", {"ident_eq": ident, "decision": "retenir"})[1]["n"], 1)
        f = {x["cle"]: x for x in self.appel("/api/equipement?ident=" + ident)[1]["fonctionnelles"]}
        self.assertEqual((f["TS_DISC"]["etat"], f["TS_INT"]["etat"]), ("retenue", "écartée"))
        self.assertEqual(f["TS_INT"]["motif"], "vanne quart de tour sans arrêt intermédiaire")
        self.assertEqual(self.appel("/api/equipement/valider", {"idents": [ident], "valide": True})[0], 200)
        es = self.appel("/api/es")[1]
        self.assertTrue(es["points"])
        self.assertEqual(self.appel("/api/modules", {"action": "ajouter", "rack": 0, "position": 2, "nature": "ET", "voies": 16})[0], 200)
        r = self.appel("/api/modules", {"action": "implanter"})[1]
        self.assertGreater(r["affectees"], 0)
        es = self.appel("/api/es")[1]
        et = [p for p in es["points"] if p["point"] == "ET"]
        self.assertTrue(all(p["adresse"].startswith("%I0.2.") for p in et))
        self.assertEqual(self.appel("/api/es/valider", {"paires": [{"ident_eq": p["ident_eq"], "cle": p["cle"]} for p in et]})[1]["n"], len(et))
        self.assertEqual(self.appel("/api/es/definir", {"ident_eq": et[0]["ident_eq"], "cle": et[0]["cle"], "sens": "1 = Ouverte"})[0], 200)
        for quoi in ("liste_es", "cartes"):
            with urllib.request.urlopen(self.url + "api/export?quoi=" + quoi) as rep:
                self.assertEqual(rep.read(2), b"PK")
        self.assertEqual(self.appel("/api/numero?type=HV&se=12")[1]["numero"], "02")   # numérotation par type dans l'ouvrage
        # Import strict : un fichier contenant un ouvrage étranger est entièrement refusé.
        csv = "COD_EQPT;LIB_EQPT;COD_TYP_MAT\nXT25RV01PM01;POMPE 1;PM--\nXT25RV01A01P;ARMOIRE;A--P\nX000YY01HV01;AUTRE;HV--\n"
        self.assertEqual(self.appel("/api/referentiel/action", {"action": "creer_type", "code": "A--P",
                                                               "designation": "Armoire process"})[0], 400)
        fichier = {"nom": "liste.csv", "contenu": base64.b64encode(csv.encode()).decode(), "nature": "inventaire"}
        code, ap = self.appel("/api/inbound/apercu", fichier)
        self.assertEqual(code, 200, ap)
        self.assertFalse(ap["integrable"])
        self.assertGreater(ap["statistiques"]["erreurs"], 0)
        self.assertEqual(self.appel("/api/inbound/appliquer", {"jeton": ap["jeton"], "confirmer": True})[0], 400)
        # Retrait du signal hors ouvrage : une nouvelle prévisualisation est nécessaire.
        conforme = "COD_EQPT;LIB_EQPT;COD_TYP_MAT\nXT25RV01PM01;POMPE 1;PM--\nXT25RV01A01P;ARMOIRE;A--P\n"
        fichier["contenu"] = base64.b64encode(conforme.encode()).decode()
        code, ap = self.appel("/api/inbound/apercu", fichier)
        self.assertEqual(code, 200, ap)
        self.assertTrue(ap["integrable"])
        self.assertEqual(self.appel("/api/inbound/appliquer", {"jeton": ap["jeton"], "confirmer": True})[1]["crees"], 2)
        o = self.appel("/api/ouvrage")[1]
        self.assertIn("XT25RV01A01P", [e["pcf"] for e in o["equipements"]])
        # enregistrement après confirmation : l'ouvrage figure dans la liste
        fiches = self.appel("/api/accueil")[1]["ouvrages"]
        self.assertEqual([f["repere"] for f in fiches], ["XT25RV01"])
        # suppression : corbeille
        self.assertEqual(self.appel("/api/supprimer_ouvrage", {"chemin": fiches[0]["chemin"]})[0], 200)
        a = self.appel("/api/accueil")[1]
        self.assertEqual((a["ouvrages"], a["corbeille"], a["ouvert"]), ([], 1, False))

    def test_referentiel_et_erreurs(self):
        r = self.appel("/api/referentiel")[1]
        self.assertIn("Sûreté", r["domaines"])
        self.assertEqual(self.appel("/api/referentiel/action", {"action": "creer_type", "code": "XYZ1"})[0], 400)
        self.assertEqual(self.appel("/api/inbound/apercu", {"nom": "x.exe", "contenu": ""})[0], 400)


if __name__ == "__main__":
    unittest.main()
