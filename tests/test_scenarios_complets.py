"""Deux scénarios de bout en bout, sans interface, uniquement par la Session.

Projet neuf : création, UF, équipements, variables, commentaire, adresses, validation,
contrôles, sauvegarde, réouverture, exports XSY et Excel.
Projet existant : import d'un XSY (produit par le scénario neuf, rien d'autre n'est lu),
liste E/S, équipements détectés, table de télétransmission, décisions, export.

Un test réussi prouve la cohérence interne de l'outil, PAS l'acceptation des fichiers par
Control Expert, TOPKAPI ou SOFREL : ces essais restent à faire hors production.
"""
import os
import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from genvar import chemins, existant
from genvar.catalogue import Catalogue
from genvar.modele import Equipement
from genvar.session import Session


def nouvelle_session():
    return Session(Catalogue.charger(chemins.fichier_catalogue_origine()))


class TestScenarios(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.dossier = tempfile.mkdtemp()
        os.environ["SOREP_DATA_DIR"] = self.dossier

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    # ------------------------------------------------------------------ projet neuf
    def scenario_neuf(self):
        s = nouvelle_session()
        for champ, val in (("lieu", "F999"), ("code_ouvrage", "RV"), ("libelle", "Réservoir fictif"),
                           ("automate", "M580"), ("localisation", "Commune fictive"),
                           ("type_ouvrage", "Réservoir"), ("communication", "Modbus TCP")):
            s.definir(champ, val)
        s.ajouter_sous_ensemble("11", "Réservoir 1")
        s.ajouter_uf("UF01", "Alimentation"); s.ajouter_uf("UF02", "Pompage")
        s.ajouter_equipement(Equipement("11", "MV", "01", "Vanne d'alimentation", options=["Télécommandée"]))
        s.ajouter_equipement(Equipement("11", "FT", "01", "Débitmètre", options=["Sortie impulsions câblée"]))
        s.ajouter_equipement(Equipement("11", "PM", "01", "Pompe 1"))
        s.ajouter_equipement(Equipement("11", "PM", "02", "Pompe 2"))
        mv, ft, p1, p2 = s.ouvrage.equipements
        s.affecter_uf({mv.ident, ft.ident}, "UF01")
        s.affecter_uf({p1.ident, p2.ident}, "UF02")
        s.definir_textes(mv.ident, "TS_FER", commentaire="Vanne alimentation fermée (FDC)")
        for eq in s.ouvrage.equipements:            # informations proposées : décision explicite
            s.decider_propositions(eq.ident, "retenir")
        props, erreurs = s.plan()
        self.assertFalse(erreurs)
        s.appliquer(props)
        ok, refus = s.valider_adresses([(v.ident_eq, v.cle) for v in s.variables()])
        self.assertEqual(ok, len(s.variables()))
        # Nouvelle recette : chaque échelle et sortie d'impulsions doit être configurée
        # avant la validation explicite du paramétrage des équipements.
        for p in s.points():
            if p.point in ('EA', 'SA') and p.raccordement == 'Câblé':
                s.definir_analogique(p.ident_eq, p.cle, {'signal_min': 4, 'signal_max': 20,
                     'phys_min': 0, 'phys_max': 100, 'unite': 'u.m.'})
            if p.cle == 'ES_IMP':
                s.definir_impulsion(p.ident_eq, p.cle, {'poids': 1, 'front': 'Montant', 'unite': 'm³'})
        s.valider_equipements([eq.ident for eq in s.ouvrage.equipements])
        return s

    def test_projet_neuf_complet(self):
        s = self.scenario_neuf()
        b = s.bilan()
        self.assertEqual(b["erreurs"], 0)
        chemin = os.path.join(self.dossier, "F999RV.ouvrage.json")
        s.enregistrer(chemin)
        # réouverture : mêmes variables, mêmes adresses, mêmes validations
        s2 = nouvelle_session()
        s2.ouvrir(chemin)
        avant = [(v.nom, v.adresse, v.adresse_validee, v.commentaire, v.uf) for v in s.variables()]
        apres = [(v.nom, v.adresse, v.adresse_validee, v.commentaire, v.uf) for v in s2.variables()]
        self.assertEqual(avant, apres)
        self.assertEqual(s2.ouvrage.localisation, "Commune fictive")
        # exports
        xsy = os.path.join(self.dossier, "F999RV.xsy")
        n = s2.exporter_xsy(xsy)
        self.assertEqual(n, len(s2.variables()) + len([p for p in s2.points() if p.adresse]))
        ET.parse(xsy)                               # XML bien formé
        with open(xsy, encoding="utf-8") as f:
            self.assertIn("Vanne alimentation fermée (FDC)", f.read())
        xlsx = os.path.join(self.dossier, "F999RV.xlsx")
        s2.exporter_excel(xlsx)
        self.assertTrue(zipfile.is_zipfile(xlsx))

    def test_parcours_neuf_jusqu_aux_cartes_et_validation(self):
        """Création → équipements → liste des E/S → modules et implantation → validation des E/S →
        variables et adresses → contrôles → statut « Validé » → exports (XSY, Excel, liste E/S, cartes)."""
        s = self.scenario_neuf()
        besoins = {}
        for p in s.liste_es():
            besoins[p.point] = besoins.get(p.point, 0) + 1
        position = 1
        for nature, n in sorted(besoins.items()):
            voies = {"ET": 16, "ST": 16, "EA": 8, "SA": 4}[nature]
            for _ in range(-(-n // max(1, int(voies * 0.8)))):            # assez de modules pour garder 20 %
                s.ajouter_module(0, position, nature, voies)
                position += 1
        placees, manquantes, _ = s.implanter_es()
        self.assertEqual(manquantes, {})
        self.assertEqual(placees, len(s.liste_es()))
        self.assertEqual(s.valider_es([(p.ident_eq, p.cle) for p in s.liste_es()]), len(s.liste_es()))
        self.assertTrue(all(p.validee and p.adresse for p in s.liste_es()))
        self.assertEqual(s.bilan()["erreurs"], 0)
        s.definir("statut", "Validé")                                   # accepté : plus rien à confirmer
        chemin = os.path.join(self.dossier, "parcours.ouvrage.json")
        s.enregistrer(chemin)
        s2 = nouvelle_session()
        s2.ouvrir(chemin)
        self.assertEqual(s2.ouvrage.statut, "Validé")
        self.assertEqual([(p.nom, p.adresse) for p in s2.liste_es()], [(p.nom, p.adresse) for p in s.liste_es()])
        for nom, f in (("xsy", s2.exporter_xsy), ("xlsx", s2.exporter_excel), ("es.xlsx", s2.exporter_liste_es),
                       ("cartes.xlsx", s2.exporter_cartes_es)):
            sortie = os.path.join(self.dossier, f"parcours.{nom}")
            f(sortie)
            self.assertTrue(os.path.getsize(sortie) > 0)

    # ------------------------------------------------------------------ projet existant
    def test_projet_existant_complet(self):
        neuf = self.scenario_neuf()
        xsy = os.path.join(self.dossier, "programme_existant.xsy")
        neuf.exporter_xsy(xsy)
        attendu = {v.nom: v.adresse for v in neuf.variables()}

        s = nouvelle_session()
        s.definir("mode", "Existant")
        for champ, val in (("lieu", "F999"), ("code_ouvrage", "RV"), ("libelle", "Reprise fictive"),
                           ("automate", "M580"), ("communication", "Modbus TCP")):
            s.definir(champ, val)
        # Phase A : import, données d'origine intactes
        analyse = existant.lire_xsy_detaille(xsy)
        existant.importer_xsy_detaille(s.ouvrage, analyse)
        lus = {v.nom: v.adresse for v in s.ouvrage.existantes}
        for nom, adr in attendu.items():
            self.assertEqual(lus.get(nom), adr)
        # Équipements : détectés puis acceptés explicitement
        detectes = s.equipements_detectes()
        self.assertEqual({d.code for d in detectes}, {"11MV01", "11FT01", "11PM01", "11PM02"})
        self.assertEqual(s.ouvrage.equipements, [])
        s.ajouter_detectes(detectes)
        mv = next(e for e in s.ouvrage.equipements if e.type == "MV")
        mv.options = ["Télécommandée"]
        ft = next(e for e in s.ouvrage.equipements if e.type == "FT")
        ft.options = ["Sortie impulsions câblée"]
        # Phases C/D : table et propositions
        s.construire_table()
        n = s.proposer_associations()
        self.assertGreater(n, 0)
        lignes = s.table()
        for x in lignes:
            if x.variable_source:
                self.assertEqual(x.variable_source, x.nom_standard)   # noms normalisés : rapprochement exact
                self.assertEqual(x.statut, "À compléter")             # jamais validé automatiquement
        # Phase E : décisions de l'automaticien
        for x in lignes:
            l = x.ligne
            if l.variable_source:
                s.valider_fonction(l.ident_eq, l.cle)
                s.definir_acces(l.ident_eq, l.cle, verifie=True)       # protocole de l'ouvrage
            else:
                s.declarer_non_accessible(l.ident_eq, l.cle, "Absent du programme fictif")
        bilan = {k: v for k, v in __import__("genvar.teletransmission", fromlist=["bilan"]).bilan(
            s.ouvrage, s.catalogue).items() if v}
        self.assertEqual(set(bilan) - {"total"}, {"Validée"} | ({"Non accessible"} if "Non accessible" in bilan else set()))
        # Phase F : validation de l'ouvrage, sauvegarde, export
        s.ouvrage.statut = "Validé"
        chemin = os.path.join(self.dossier, "reprise.ouvrage.json")
        s.enregistrer(chemin)
        s2 = nouvelle_session(); s2.ouvrir(chemin)
        self.assertEqual([x.statut for x in s2.table()], [x.statut for x in s.table()])
        xlsx = os.path.join(self.dossier, "reprise.xlsx")
        s2.exporter_excel(xlsx)
        with zipfile.ZipFile(xlsx) as z:
            self.assertIn("Validée", z.read("xl/worksheets/sheet1.xml").decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
