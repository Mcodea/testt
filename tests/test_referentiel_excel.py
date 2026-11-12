"""Référentiel ↔ Excel dans le cycle unique brouillon → validation → publication : export, réimport sans perte,
contrôles, aperçu, révisions, ouvrages protégés."""
import os
import tempfile
import unittest

from genvar import chemins, modeles
from genvar import referentiel_excel as rx
from genvar.catalogue import Catalogue
from genvar.modele import Equipement
from genvar.session import Session, RegleMetier
from genvar.referentiel_depot import Depot

try:
    import openpyxl                       # présent en développement : simule un enregistrement par Excel
except ImportError:                        # pragma: no cover
    openpyxl = None


class Base(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.dossier = tempfile.mkdtemp()
        os.environ["SOREP_DATA_DIR"] = self.dossier
        self.s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        self.f = os.path.join(self.dossier, "ref.xlsx")
        self.s.exporter_referentiel(self.f)
        Depot().creer_brouillon("essai")                     # un classeur s'importe dans un brouillon

    def publier(self, motif):
        d = Depot()
        b = d.valider("essai")
        r = d.publier(motif, b["empreinte_validee"], "essai")
        self.s._recharger_referentiel()
        return r["revision"]

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def modifier(self, action):
        """Ouvre le classeur comme Excel, applique `action(classeur)`, enregistre (chaînes partagées)."""
        wb = openpyxl.load_workbook(self.f)
        action(wb)
        wb.save(self.f)

    @staticmethod
    def ligne_ou(ws, colonne, valeur):
        titres = [c.value for c in ws[1]]
        j = titres.index(colonne) + 1
        return next(r for r in range(2, ws.max_row + 1) if ws.cell(r, j).value == valeur)

    @staticmethod
    def col(ws, titre):
        return [c.value for c in ws[1]].index(titre) + 1


class TestAllerRetour(Base):
    def test_export_puis_reimport_sans_modification(self):
        r = self.s.analyser_classeur_referentiel(self.f)
        self.assertEqual((r["erreurs"], r["differences"], r["integrable"]), ([], [], False))
        cat, ref = rx.construire(rx.lire(self.f)[0], self.s._catalogue_commun, modeles.charger())
        self.assertEqual(rx.etat(cat, ref), rx.etat(self.s._catalogue_commun, modeles.charger()))   # rien de perdu

    @unittest.skipUnless(openpyxl, "openpyxl absent")
    def test_aller_retour_par_excel(self):
        self.modifier(lambda wb: None)                       # ouvert et réenregistré tel quel
        r = self.s.analyser_classeur_referentiel(self.f)
        self.assertEqual((r["erreurs"], r["differences"]), ([], []))

    def test_classeur_etranger_refuse(self):
        from genvar.export_xlsx import ecrire_xlsx
        autre = os.path.join(self.dossier, "autre.xlsx")
        ecrire_xlsx(autre, [("Feuil1", ["A"], [["x"]], [10])])
        with self.assertRaises(rx.ReferentielInvalide):
            self.s.analyser_classeur_referentiel(autre)

    def test_listes_deroulantes_et_identifiants(self):
        import zipfile
        with zipfile.ZipFile(self.f) as z:
            signaux = z.read("xl/worksheets/sheet3.xml").decode()
        self.assertIn('<dataValidation type="list"', signaux)
        self.assertIn("Valeurs!$", signaux)
        self.assertIn("HV.TS_DISC", signaux)


@unittest.skipUnless(openpyxl, "openpyxl absent")
class TestModifications(Base):
    def test_ajout_modification_suppression_puis_application(self):
        def action(wb):
            ws = wb["Signaux"]
            r = self.ligne_ou(ws, "ID signal", "HV.TS_INT")
            ws.cell(r, self.col(ws, "Information")).value = "Position intermédiaire (vanne)"
            n = ws.max_row + 1
            for titre, v in (("Ordre", "4.5"), ("Type", "HV"), ("Famille", "TS"), ("Code", "MAINT"),
                             ("Information", "En maintenance"), ("Nature E/S", "Interne"), ("Type logique", "BOOL"),
                             ("Alarme", "Non"), ("Présence", "Par défaut"), ("Statut", "À valider")):
                ws.cell(n, self.col(ws, titre)).value = v
            ml = wb["Lignes de modèles"]
            premiere = ml.cell(2, self.col(ml, "ID ligne")).value
            ml.cell(2, self.col(ml, "Supprimer")).value = "Oui"
            self.premiere = premiere
        self.modifier(action)
        r = self.s.analyser_classeur_referentiel(self.f)
        self.assertEqual(r["erreurs"], [])
        vus = {(d["action"], d["id"]) for d in r["differences"]}
        self.assertIn(("ajout", "HV.TS_MAINT"), vus)
        self.assertIn(("modification", "HV.TS_INT"), vus)
        self.assertIn(("suppression", self.premiere), vus)
        with self.assertRaises(RegleMetier):
            self.s.integrer_classeur_referentiel("empreinte-inconnue")      # seul l'aperçu montré s'intègre
        self.s.integrer_classeur_referentiel(r["empreinte"])
        self.assertNotIn("MAINT", {s["code"] for s in self.s._catalogue_commun.signaux})   # publié : inchangé
        n = self.publier("Ajout maintenance vanne")
        self.assertEqual(n, 2)                                                # R0001 = état en service archivé
        self.assertIn("HV", {s["type"] for s in self.s._catalogue_commun.signaux if s["code"] == "MAINT"})
        self.assertTrue(self.s._catalogue_commun.version.startswith("R0002"))
        cles = [f"{s['famille']}_{s['code']}" for s in self.s._catalogue_commun.signaux_du_type("HV")]
        self.assertLess(cles.index("TS_MAINT"), cles.index("TS_DISC"))      # ordre 4.5 respecté
        # restauration de l'état initial : nouveau brouillon, puis nouvelle révision ; rien n'est effacé
        Depot().restaurer_en_brouillon(1, "essai")
        self.assertEqual(self.publier("Retour à R0001"), 3)
        self.assertNotIn("MAINT", {s["code"] for s in self.s._catalogue_commun.signaux_du_type("HV")})
        self.assertEqual([x["numero"] for x in self.s.revisions_referentiel()], [3, 2, 1])

    def test_controles_bloquants(self):
        def action(wb):
            ws = wb["Signaux"]
            r = self.ligne_ou(ws, "ID signal", "HV.TS_OUV")
            ws.cell(r, self.col(ws, "Type logique")).value = "REAL"            # TS numérique : interdit
            r2 = self.ligne_ou(ws, "ID signal", "PM.ES_MA")
            ws.delete_rows(r2)                                                # ligne disparue
            rg = wb["Règles"]
            r3 = self.ligne_ou(rg, "ID règle", "HV-03")
            rg.cell(r3, self.col(rg, "Propose (séparées par ;)")).value = "TS_DISC ; TS_INEXISTANT"
            n = ws.max_row + 1
            for titre, v in (("Type", "HV"), ("Famille", "TS"), ("Code", "OUV"), ("Information", "Doublon"),
                             ("Nature E/S", "Interne"), ("Type logique", "BOOL"), ("Présence", "Par défaut"),
                             ("Statut", "Validé")):
                ws.cell(n, self.col(ws, titre)).value = v
        self.modifier(action)
        r = self.s.analyser_classeur_referentiel(self.f)
        texte = " | ".join(r["erreurs"])
        self.assertFalse(r["integrable"])
        for attendu in ("BOOL ou EBOOL", "absent(s) du classeur", "TS_INEXISTANT", "déjà défini"):
            self.assertIn(attendu, texte)
        with self.assertRaises(RegleMetier):
            self.s.integrer_classeur_referentiel("")

    def test_renommage_d_identifiant_refuse(self):
        def action(wb):
            ws = wb["Signaux"]
            r = self.ligne_ou(ws, "ID signal", "HV.TS_INT")
            ws.cell(r, self.col(ws, "Code")).value = "INTER"
        self.modifier(action)
        r = self.s.analyser_classeur_referentiel(self.f)
        self.assertTrue(any("ne correspond plus" in e for e in r["erreurs"]))


@unittest.skipUnless(openpyxl, "openpyxl absent")
class TestOuvragesProteges(Base):
    def test_ouvrage_existant_garde_sa_version(self):
        s = self.s
        s.nouveau(False)
        s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
        s.ajouter_sous_ensemble("00")
        s.ajouter_equipement(Equipement("00", "HV", "01"))
        chemin = os.path.join(self.dossier, "Projets", "o.ouvrage.json")
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        s.enregistrer(chemin)
        avant = [(v.nom, v.cle) for v in s.variables()]

        def action(wb):
            ws = wb["Règles"]
            r = self.ligne_ou(ws, "ID règle", "HV-01")
            ws.cell(r, self.col(ws, "Libellé")).value = "Fin de course ouverte → TS ouverte (libellé revu)"
        self.modifier(action)
        r = s.analyser_classeur_referentiel(self.f)
        self.assertEqual(r["erreurs"], [])
        d = next(x for x in r["differences"] if x["id"] == "HV-01")
        self.assertIn("1 ouvrage(s)", d["consequence"])
        s.integrer_classeur_referentiel(r["empreinte"])
        self.publier("libellé HV-01")
        self.assertEqual([(v.nom, v.cle) for v in s.variables()], avant)        # ouvrage ouvert inchangé
        s2 = Session(); s2.ouvrir(chemin)
        self.assertEqual([(v.nom, v.cle) for v in s2.variables()], avant)       # ni à la réouverture
        self.assertEqual([x["type"] for x in s2.ecarts_referentiel()], ["HV"])  # écart signalé, non appliqué


if __name__ == "__main__":
    unittest.main()


class TestCycle(unittest.TestCase):
    """Garde-fous du cycle (repris du module 2) : lecture seule, brouillon unique, validation annulée par toute
    modification, fichier modifié hors cycle, classeur avec formule, verrou, restauration sans réécriture."""
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.dossier = tempfile.mkdtemp()
        os.environ["SOREP_DATA_DIR"] = self.dossier

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def test_cycle_complet_et_refus(self):
        from genvar.referentiel_depot import DepotRefuse, editer, empreinte
        d = Depot()
        b = d.creer_brouillon("a")
        with self.assertRaises(DepotRefuse):
            d.creer_brouillon("b")                                         # un seul brouillon
        with self.assertRaises(DepotRefuse):
            d.valider()                                                    # identique au publié
        donnees, lib = editer(b["donnees"], "modifier_signal", "LT.TS_B", {"presence": "Option"})
        d.remplacer_donnees(donnees, lib)
        with self.assertRaises(DepotRefuse):
            d.valider()                                                    # option non précisée : erreur bloquante
        donnees, lib = editer(donnees, "modifier_type", "LT", {"options": "Seuils réglables; Seuils d'alarme"})
        donnees, lib = editer(donnees, "modifier_signal", "LT.TS_B", {"option": "Seuils d'alarme"})
        d.remplacer_donnees(donnees, lib)
        v = d.valider("a")
        d.remplacer_donnees(donnees, "même contenu, nouvelle écriture")    # toute écriture annule la validation
        with self.assertRaises(DepotRefuse):
            d.publier("x", v["empreinte_validee"])
        v = d.valider("a")
        with self.assertRaises(DepotRefuse):
            d.publier("", v["empreinte_validee"])                          # motif obligatoire
        r = d.publier("Seuil bas LT optionnel", v["empreinte_validee"], "a")
        self.assertEqual(r["revision"], 2)
        self.assertEqual(next(s for s in Catalogue.charger().signaux if s["type"] == "LT" and s["code"] == "B")["presence"], "Option")
        # fichier en service modifié hors du cycle : détecté, publication bloquée
        cat = Catalogue.charger(); cat.signaux[0]["information"] = "modifié à la main"; cat.enregistrer(d.f_catalogue)
        self.assertIn("hors du cycle", d.etat()["incoherence"])
        with self.assertRaises(DepotRefuse):
            d.creer_brouillon("b")
        # restauration : nouveau brouillon à partir d'une révision, historique intact
        cat.signaux[0]["information"] = Depot().revision(2)["donnees"]["catalogue"]["signaux"][0]["information"]
        cat.version = Depot().revision(2)["donnees"]["catalogue"]["version"]
        cat.enregistrer(d.f_catalogue)
        self.assertEqual(empreinte(d.publie()), d.head()["empreinte"])
        d.restaurer_en_brouillon(1, "a")
        self.assertEqual([x["numero"] for x in d.revisions()], [2, 1])

    def test_classeur_avec_formule_refuse_et_verrou(self):
        from genvar.referentiel_depot import DepotRefuse, classeur_sain
        import zipfile
        f = os.path.join(self.dossier, "f.xlsx")
        with zipfile.ZipFile(f, "w") as z:
            z.writestr("xl/worksheets/sheet1.xml", '<worksheet><sheetData><row><c r="A1"><f>1+1</f></c></row></sheetData></worksheet>')
        with self.assertRaises(DepotRefuse):
            classeur_sain(f)
        d = Depot()
        os.makedirs(d.racine, exist_ok=True)
        open(os.path.join(d.racine, ".operation.lock"), "w").close()
        with self.assertRaises(DepotRefuse):
            d.creer_brouillon("a")

    def test_editeur_historique_en_lecture_seule_apres_debut_du_cycle(self):
        s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        Depot().creer_brouillon("a")
        with self.assertRaises(RegleMetier):
            s.creer_modele("HV", "Modèle direct")                          # aucune écriture hors brouillon
