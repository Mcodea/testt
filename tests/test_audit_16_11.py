"""Corrections de l'audit du 16/11/2026 et retours de 15 h 08 : serveur local fermé aux autres sites, liste de
l'ouvrage en temps linéaire, cohérence carte / voie / référence, source d'acquisition obligatoire, réserve de
20 % au moins. Données fictives (lieu XTST)."""
import http.client
import json
import os
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from genvar.session import RegleMetier  # noqa: E402
from sorep_web.serveur import Application, demarrer  # noqa: E402


class _Base(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.donnees = tempfile.TemporaryDirectory(prefix="ogias-audit-")
        os.environ["SOREP_DATA_DIR"] = self.donnees.name

    def tearDown(self):
        self.donnees.cleanup()
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    @staticmethod
    def ouvrage(app, automate="Sch - M340", numero="01"):
        app.nouveau({"mode": "Neuf"})
        app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
        app.fiche_ouvrage({"action": "creer", "identification": {
            "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": numero, "libelle": "Audit",
            "automate": automate, "revision": "A"}})

    @staticmethod
    def equipements_valides(app, types=("PM", "MV", "HV")):
        ids = [app.ajouter_equipement({"type": t, "numero": f"{k + 1:02d}", "se": "00"})["ident"]
               for k, t in enumerate(types)]
        for i in ids:
            app.decider_proposition({"ident_eq": i, "decision": "retenir"})
        app.valider_equipements({"idents": ids, "valide": True})
        pts = app.es({})["points"]
        app.es_valider({"niveau": "contenu", "paires": [{"ident_eq": p["ident_eq"], "cle": p["cle"]} for p in pts]})
        return ids


class TestServeurFermeAuxAutresSites(_Base):
    def setUp(self):
        super().setUp()
        self.serveur, _, self.app = demarrer(ouvrir_navigateur=False, port=0)
        self.port = self.serveur.server_address[1]
        self.thread = threading.Thread(target=self.serveur.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.serveur.shutdown()
        self.thread.join(timeout=5)
        self.serveur.server_close()
        super().tearDown()

    def requete(self, methode, chemin, corps=None, entetes=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request(methode, chemin, body=corps, headers=entetes or {})
        r = c.getresponse()
        return r.status, r.read()

    def test_post_d_un_autre_site_refuse(self):
        corps = json.dumps({"champ": "libelle", "valeur": "pirate"})
        self.assertEqual(self.requete("POST", "/api/definir", corps, {"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.requete("POST", "/api/definir", corps, {
            "Content-Type": "application/json", "Origin": "https://site-quelconque.test"})[0], 403)
        self.assertEqual(self.requete("POST", "/api/definir", corps, {
            "Content-Type": "application/json", "Sec-Fetch-Site": "cross-site"})[0], 403)
        # La même requête venant de l'interface d'OGIAS passe
        statut, _ = self.requete("POST", "/api/listes-ouvrage/action", json.dumps(
            {"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"}),
            {"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{self.port}"})
        self.assertEqual(statut, 200)

    def test_rebinding_dns_refuse(self):
        self.assertEqual(self.requete("GET", "/api/ouvrage", entetes={"Host": "attaquant.test"})[0], 421)
        self.assertEqual(self.requete("GET", "/api/ouvrage", entetes={"Host": f"localhost:{self.port}"})[0], 200)

    def test_un_fichier_hors_de_mes_ouvrages_n_est_jamais_deplace(self):
        dossier = tempfile.mkdtemp(prefix="ogias-victime-")
        victime = os.path.join(dossier, "rapport.docx")
        with open(victime, "w", encoding="utf-8") as f:
            f.write("contenu")
        statut, corps = self.requete("POST", "/api/supprimer_ouvrage", json.dumps({"chemin": victime}),
                                     {"Content-Type": "application/json"})
        self.assertEqual(statut, 400)
        self.assertIn("Mes ouvrages", json.loads(corps)["erreur"])
        self.assertTrue(os.path.isfile(victime))
        self.assertEqual(os.listdir(dossier), ["rapport.docx"])

    def test_requetes_mal_formees(self):
        json_ = {"Content-Type": "application/json"}
        self.assertEqual(self.requete("POST", "/api/definir", b"[1,2]", json_)[0], 400)
        self.assertEqual(self.requete("POST", "/api/definir", b"{oops", json_)[0], 400)
        self.assertEqual(self.requete("POST", "/api/definir", b"{}", dict(json_, **{"Content-Length": "abc"}))[0], 400)
        self.assertEqual(self.requete("GET", "/../../etc/passwd")[0], 404)


class TestPerformanceListeOuvrage(_Base):
    def test_300_equipements_en_temps_lineaire(self):
        app = Application()
        self.ouvrage(app)
        for k in range(297):
            app.ajouter_equipement({"type": ("PM", "MV", "HV")[k % 3], "numero": f"{k // 3 + 1:02d}", "se": "00"})
        debut = time.perf_counter()
        o = app.ouvrage({})
        duree = time.perf_counter() - debut
        self.assertEqual(len(o["equipements"]), 297)
        self.assertTrue(all(e["nb_es"] > 0 for e in o["equipements"]))
        self.assertLess(duree, 4.0, f"/api/ouvrage : {duree:.2f} s pour 297 équipements (19,7 s avant correction)")


class TestCoherenceCartesEtVoies(_Base):
    def setUp(self):
        super().setUp()
        self.app = Application()
        self.ouvrage(self.app)
        self.equipements_valides(self.app)
        self.app.materiel_action({"action": "appliquer"})
        self.app.modules_action({"action": "implanter"})
        self.s = self.app.s

    def test_voie_module_et_nature_controles_a_la_saisie(self):
        et = [p for p in self.s.points() if p.point == "ET" and p.adresse]
        carte = next(m for m in self.s.ouvrage.modules if m.nature == "ET")
        cas = ((carte.cle, carte.voies + 3, f"n'a que {carte.voies} voies"), ("0.7", 0, "Aucune carte"))
        for module, voie, motif in cas:
            with self.assertRaisesRegex(RegleMetier, motif):
                self.s.definir_es(et[0].ident_eq, et[0].cle, module=module, voie=voie)

    def test_reference_du_catalogue_impose_nature_et_voies(self):
        libre = next(p for p in range(1, self.s.ouvrage.racks[0]["positions"])
                     if p not in self.s.ouvrage.racks[0]["cpu"] and not any(m.position == p for m in self.s.ouvrage.modules))
        with self.assertRaisesRegex(RegleMetier, "16 voies"):
            self.s.ajouter_module(0, libre, "ET", 64, "BMX DDI 1602")
        with self.assertRaisesRegex(RegleMetier, "carte ET"):
            self.s.ajouter_module(0, libre, "SA", 16, "BMX DDI 1602")
        self.s.ajouter_module(0, libre, "ET", 16, "BMX DDI 1602")        # conforme au catalogue

    def test_validation_et_export_refuses_si_incoherence_d_un_ancien_fichier(self):
        p = next(x for x in self.s.points() if x.point == "ET" and x.adresse)
        eq = self.s.ouvrage.equipement(p.ident_eq)                                 # comme dans un ancien fichier
        eq.adresses_es[p.cle] = "%I0.9.0"
        eq.es_meta.setdefault(p.cle, {}).update(module="0.9", voie="0")
        with self.assertRaisesRegex(RegleMetier, "Matériel incohérent"):
            self.s.valider_materiel()
        with self.assertRaisesRegex(RegleMetier, "Export refusé"):
            self.app.exporter({"quoi": "es_xsy"})


class TestSourceEtReserve(_Base):
    def test_sans_source_aucun_materiel_suppose(self):
        app = Application()
        self.ouvrage(app, automate="")
        self.equipements_valides(app)
        self.assertIn("non renseignée", app.materiel({})["blocage"])
        with self.assertRaises(RegleMetier):
            app.materiel_action({"action": "appliquer"})

    def test_reserve_de_vingt_pour_cent_au_moins(self):
        app = Application()
        self.ouvrage(app)
        for taux in (0.15, 0.0, 0.95, "abc"):
            with self.assertRaises(RegleMetier, msg=str(taux)):
                app.s.definir_reserve(taux)
        app.modules_action({"action": "reserve", "taux": 0.3})
        self.assertEqual(app.s.ouvrage.reserve_min, 0.3)


if __name__ == "__main__":
    unittest.main()
