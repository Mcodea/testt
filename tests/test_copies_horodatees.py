"""Cahier § 7, V1-7-03 : copies horodatées avant chaque opération lourde, restaurables depuis l'interface.

Opérations lourdes couvertes : adressage (moteur centralisé et plan historique), implantation des E/S sur les
voies, remplacement du matériel, application d'un inventaire, confirmation en lot du rapprochement, import
contrôlé (route web). Chaque copie contient l'état de l'ouvrage **juste avant** l'opération (modifications non
enregistrées comprises), à côté du fichier de l'ouvrage. Une opération refusée ou sans effet n'en crée aucune ;
une copie impossible annule l'opération. La restauration charge la copie en mémoire après une copie de l'état
courant : elle est elle-même réversible. Le fichier d'ouvrage n'est jamais touché par la copie ni par la
restauration (seul « Enregistrer » l'écrit). Lieu fictif XTST.
"""
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

from genvar import chemins, copies
from genvar.catalogue import Catalogue
from genvar.modele import Equipement, Ouvrage
from genvar.session import RegleMetier, Session
from validation.hybride.evaluer import BASE, scenario


def _ouvrage_neuf():
    s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
    s.nouveau(lieu_dans_le_nom=False)
    s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
    s.definir("automate", "M340")
    s.ajouter_sous_ensemble("00")
    for t, num in (("PM", "01"), ("MV", "02")):
        e = s.ajouter_equipement(Equipement("00", t, num))
        s.decider_propositions(e.ident, "retenir")
    s.valider_contenu_es([(p.ident_eq, p.cle) for p in s.points()])
    return s


class Base(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.dossier = tempfile.mkdtemp()
        os.environ["SOREP_DATA_DIR"] = self.dossier
        self.s = _ouvrage_neuf()
        self.fichier = os.path.join(self.dossier, "XTST_RV01.ouvrage.json")
        self.s.enregistrer(self.fichier)
        self.octets = open(self.fichier, "rb").read()

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def adresser(self):
        plan = self.s.plan_adressage()
        return self.s.appliquer_adressage(plan.empreinte)

    def adresses(self, ouvrage=None):
        o = ouvrage or self.s.ouvrage
        return {(e.ident, k): v for e in o.equipements for k, v in sorted(e.adresses.items())}


class TestCopieAvantOperation(Base):
    def test_adressage_copie_l_etat_juste_avant_y_compris_non_enregistre(self):
        self.s.definir("libelle", "Libellé non enregistré")
        self.assertFalse(self.adresses())
        self.adresser()
        self.assertTrue(self.adresses())
        liste = self.s.copies_horodatees()
        self.assertEqual([c["operation"] for c in liste], ["adressage"])
        copie = os.path.join(self.dossier, liste[0]["nom"])
        avant = Ouvrage.ouvrir(copie)
        self.assertEqual(avant.libelle, "Libellé non enregistré")       # état mémoire, pas l'ancien fichier
        self.assertFalse(self.adresses(avant))                         # avant l'opération
        self.assertEqual(open(self.fichier, "rb").read(), self.octets)  # fichier d'ouvrage intact
        self.assertTrue(liste[0]["nom"].startswith("XTST_RV01.ouvrage.json.avant-adressage-"))
        self.assertRegex(liste[0]["le"], r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$")
        self.assertTrue(avant.catalogue_snapshot)                      # référentiel figé dans la copie

    def test_plan_historique_d_adressage(self):
        props, erreurs = self.s.plan()
        self.assertFalse(erreurs)
        self.assertTrue(self.s.appliquer(props))
        self.assertEqual([c["operation"] for c in self.s.copies_horodatees()], ["adressage"])

    def test_operation_refusee_ou_sans_effet_aucune_copie(self):
        with self.assertRaises(RegleMetier):
            self.s.appliquer_adressage("empreinte périmée")
        self.assertIsNone(self.s.confirmer_en_lot())                   # rien à confirmer
        self.assertEqual(self.s.copies_horodatees(), [])

    def test_ouvrage_jamais_enregistre_aucune_copie_operation_faite(self):
        s = _ouvrage_neuf()
        plan = s.plan_adressage()
        s.appliquer_adressage(plan.empreinte)
        self.assertTrue(any(e.adresses for e in s.ouvrage.equipements))
        self.assertEqual(s.copies_horodatees(), [])
        self.assertEqual(sorted(os.listdir(self.dossier)), ["XTST_RV01.ouvrage.json"])

    def test_copie_impossible_annule_l_operation(self):
        self.s.modifie = False
        with mock.patch("genvar.copies.os.replace", side_effect=OSError(28, "No space left on device")):
            with self.assertRaises(RegleMetier) as ctx:
                self.adresser()
        self.assertIn("Copie horodatée impossible", str(ctx.exception))
        self.assertFalse(self.adresses())                              # rien d'appliqué
        self.assertFalse(self.s.modifie)
        self.assertEqual(self.s.copies_horodatees(), [])
        self.assertFalse([f for f in os.listdir(self.dossier) if f.endswith(".tmp")])

    def test_copie_impossible_restaure_aussi_le_catalogue(self):
        catalogue_avant = self.s.catalogue
        with mock.patch("genvar.copies.os.replace", side_effect=OSError(28, "No space left on device")):
            with self.assertRaises(RegleMetier):
                with self.s._operation_lourde("adressage"):
                    self.s.catalogue = Catalogue(**{**self.s.catalogue_fige(), "types": {}})
                    self.s.ouvrage.libelle = "modifié"
        self.assertEqual(self.s.catalogue.types, catalogue_avant.types)
        self.assertNotEqual(self.s.ouvrage.libelle, "modifié")

    def test_implantation_et_materiel(self):
        self.s.ajouter_module(0, 2, "ET", 16, "BMX DDI 1602")
        self.s.implanter_es()
        self.assertEqual([c["operation"] for c in self.s.copies_horodatees()], ["implantation"])
        self.s.liberer_voies_proposees()
        self.s.appliquer_materiel()
        self.assertEqual([c["operation"] for c in self.s.copies_horodatees()], ["materiel", "implantation"])

    def test_inventaire(self):
        from genvar.inventaire import LigneInventaire
        ligne = LigneInventaire("XTSTRV01PM03", sous_ensemble="00", type="PM", numero="03", etat="à créer")
        refusee = LigneInventaire("XTSTRV01PM04", sous_ensemble="00", type="PM", numero="04", etat="refusé")
        self.assertEqual(self.s.appliquer_inventaire([refusee]), 0)     # sans effet : aucune copie
        self.assertEqual(self.s.copies_horodatees(), [])
        n = self.s.appliquer_inventaire([ligne])
        self.assertEqual(n, 1)
        self.assertEqual([c["operation"] for c in self.s.copies_horodatees()], ["inventaire"])

    def test_conservation_des_dix_dernieres_par_operation_adoption_jamais_effacee(self):
        adoption = self.fichier + ".avant-adoption-20260101-000000-abc"
        open(adoption, "wb").write(self.octets)
        ancien = self.fichier + ".avant_adressage_20260101_000000"      # copie d'une version antérieure
        open(ancien, "wb").write(self.octets)
        for i in range(copies.CONSERVEES + 2):
            self.s.definir("libelle", f"essai {i}")
            copies.ecrire(self.fichier, "adressage", copies.etat(self.s))
        noms = [c["nom"] for c in self.s.copies_horodatees()]
        self.assertEqual(sum(n.startswith("XTST_RV01.ouvrage.json.avant-adressage-") for n in noms),
                         copies.CONSERVEES)
        self.assertIn(os.path.basename(adoption), noms)
        self.assertIn(os.path.basename(ancien), noms)
        restantes = [Ouvrage.ouvrir(os.path.join(self.dossier, n)).libelle for n in noms
                     if n.startswith("XTST_RV01.ouvrage.json.avant-adressage-")]
        self.assertEqual(restantes, [f"essai {i}" for i in range(copies.CONSERVEES + 1, 1, -1)])

    def test_copies_d_un_autre_ouvrage_ignorees(self):
        autre = os.path.join(self.dossier, "XTST_RV02.ouvrage.json")
        copies.ecrire(autre, "adressage", copies.etat(self.s))
        self.assertEqual(self.s.copies_horodatees(), [])


class TestConfirmationEnLot(unittest.TestCase):
    def test_copie_avant_confirmation_en_lot(self):
        dossier = tempfile.mkdtemp()
        o, cat, _truth, _eqs = scenario(BASE)
        s = Session(cat)
        s.ouvrage = o
        s.construire_table()
        s.proposer_associations()
        fichier = os.path.join(dossier, "XTST_HY.ouvrage.json")
        s.enregistrer(fichier)
        avant = [(l.ident_eq, l.cle, l.variable_source, l.fonction_validee) for l in s.ouvrage.table_tt]
        self.assertTrue(s.confirmer_en_lot())
        self.assertEqual([c["operation"] for c in s.copies_horodatees()], ["rapprochement-lot"])
        copie = Ouvrage.ouvrir(os.path.join(dossier, s.copies_horodatees()[0]["nom"]))
        self.assertEqual([(l.ident_eq, l.cle, l.variable_source, l.fonction_validee) for l in copie.table_tt],
                         avant)


class TestImportControle(Base):
    def test_copie_avant_import_puis_restauration(self):
        import base64
        from sorep_web.serveur import Application
        app = Application()
        app.s, app.ouvert, app.creation_en_attente = self.s, True, False
        n_avant = len(self.s.ouvrage.equipements)
        contenu = "Repère;Désignation;Type;Modèle\r\nXTSTRV01HV09;Vanne fictive;HV;\r\n"
        apercu = app.inbound_preview({"nom": "essai.csv", "nature": "inventaire",
                                      "contenu": base64.b64encode(contenu.encode()).decode()})
        self.assertTrue(apercu["integrable"], apercu)
        app.inbound_apply({"jeton": apercu["jeton"], "confirmer": True})
        self.assertEqual(len(app.s.ouvrage.equipements), n_avant + 1)
        liste = app.s.copies_horodatees()
        self.assertEqual([c["operation"] for c in liste], ["import"])
        app.restaurer_copie({"nom": liste[0]["nom"]})
        self.assertEqual(len(app.s.ouvrage.equipements), n_avant)
        self.assertEqual(len(Ouvrage.ouvrir(self.fichier).equipements), n_avant)   # enregistré par l'interface


class TestRestauration(Base):
    def test_restaurer_puis_revenir(self):
        self.adresser()
        apres = self.adresses()
        nom = self.s.copies_horodatees()[0]["nom"]
        self.s.modifie = False
        info = self.s.restaurer_copie(nom)
        self.assertFalse(self.adresses())                              # état d'avant l'adressage
        self.assertTrue(self.s.modifie)                                # à enregistrer : rien d'écrit
        self.assertEqual(open(self.fichier, "rb").read(), self.octets)
        self.assertEqual(info["restauree"], nom)
        ops = [c["operation"] for c in self.s.copies_horodatees()]
        self.assertEqual(ops, ["restauration", "adressage"])
        # la restauration est elle-même réversible
        self.s.restaurer_copie(info["copie_avant_restauration"])
        self.assertEqual(self.adresses(), apres)

    def test_restauration_garde_le_referentiel_fige_de_la_copie(self):
        self.adresser()
        nom = self.s.copies_horodatees()[0]["nom"]
        version = self.s.catalogue.version
        self.s.restaurer_copie(nom)
        self.assertEqual(self.s.catalogue.version, version)
        self.assertEqual(self.s.chemin, self.fichier)                  # même fichier d'ouvrage

    def test_noms_refuses(self):
        self.adresser()
        bons = [c["nom"] for c in self.s.copies_horodatees()]
        for nom in ("", "../etc/passwd", "/etc/passwd", os.path.join(self.dossier, bons[0]),
                    "XTST_RV01.ouvrage.json", "autre.ouvrage.json.avant-adressage-20260101-000000-x",
                    "XTST_RV01.ouvrage.json.avant-adressage-inexistante", None, 3):
            with self.subTest(nom=nom), self.assertRaises(RegleMetier):
                self.s.restaurer_copie(nom)
        self.assertTrue(self.adresses())                               # rien n'a changé

    def test_copie_illisible_refusee_sans_rien_changer(self):
        self.adresser()
        nom = self.s.copies_horodatees()[0]["nom"]
        open(os.path.join(self.dossier, nom), "w").write("{ tronqué")
        with self.assertRaises(RegleMetier):
            self.s.restaurer_copie(nom)
        self.assertTrue(self.adresses())
        self.assertEqual([c["operation"] for c in self.s.copies_horodatees()], ["adressage"])

    def test_sans_fichier(self):
        s = _ouvrage_neuf()
        with self.assertRaises(RegleMetier):
            s.restaurer_copie("x.avant-adressage-1")


class TestHTTP(Base):
    def setUp(self):
        super().setUp()
        from sorep_web.serveur import demarrer
        serveur, self.url, self.app = demarrer(ouvrir_navigateur=False, port=0)
        self.url = f"http://127.0.0.1:{serveur.server_address[1]}/"
        thread = threading.Thread(target=serveur.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(serveur.server_close)
        self.addCleanup(thread.join, 5)
        self.addCleanup(serveur.shutdown)
        self.app.s = self.s
        self.app.ouvert = True

    def appel(self, route, donnees=None):
        req = urllib.request.Request(self.url + route.lstrip("/"),
                                     data=None if donnees is None else json.dumps(donnees).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)

    def test_lister_et_restaurer_depuis_l_interface(self):
        self.assertEqual(self.appel("/api/ouvrage/copies"), (200, {"copies": []}))
        self.adresser()
        code, r = self.appel("/api/ouvrage/copies")
        self.assertEqual(code, 200)
        self.assertEqual([c["operation"] for c in r["copies"]], ["adressage"])
        self.assertEqual(set(r["copies"][0]), {"nom", "operation", "libelle", "le", "taille"})
        code, r2 = self.appel("/api/ouvrage/restaurer-copie", {"nom": r["copies"][0]["nom"]})
        self.assertEqual(code, 200, r2)
        self.assertFalse(self.adresses(self.app.s.ouvrage))
        # enregistrement automatique de l'interface : le fichier contient l'état restauré, l'ancien est en .bak
        self.assertFalse(self.adresses(Ouvrage.ouvrir(self.fichier)))
        code, r3 = self.appel("/api/ouvrage/restaurer-copie", {"nom": "../../etc/passwd"})
        self.assertEqual(code, 400)
        self.assertNotIn("Traceback", json.dumps(r3))


if __name__ == "__main__":
    unittest.main()
