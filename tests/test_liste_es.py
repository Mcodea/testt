"""Liste des E/S d'un projet neuf : premier livrable, indépendant des variables de supervision.

Parcours complet sur un ouvrage fictif : ouvrage, UF, équipements et options, génération de la liste,
modifications, équipement personnalisé, mises à jour sans doublon ni perte, adresses par module et
voie, sauvegarde / réouverture, exports Excel, HTML (PDF) et XSY des E/S.
Un test réussi ne vaut pas validation dans Control Expert ou S4W-Tools.
"""
import os
import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.modele import Equipement
from genvar.session import Session, RegleMetier


class TestListeES(unittest.TestCase):
    def setUp(self):
        self.ancien = os.environ.get("SOREP_DATA_DIR")
        self.dossier = tempfile.mkdtemp()
        os.environ["SOREP_DATA_DIR"] = self.dossier
        s = self.s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        # 1. ouvrage  2. UF
        s.definir("lieu", "F999"); s.definir("code_ouvrage", "RV"); s.definir("libelle", "Réservoir fictif")
        s.ajouter_sous_ensemble("11", "Réservoir")
        s.ajouter_uf("UF01", "Stockage"); s.ajouter_uf("UF02", "Distribution")
        # 3. équipements  4. options
        for e in (Equipement("11", "CU", "01", options=["Mesure de niveau", "Contacts de niveau"], uf="UF01"),
                  Equipement("11", "MV", "03", options=["Télécommandée", "Boutons locaux"], uf="UF01"),
                  Equipement("11", "PM", "01", uf="UF02"),
                  Equipement("11", "PM", "02", options=["Variateur"], uf="UF02"),
                  Equipement("11", "FT", "01", options=["Sortie impulsions câblée"], uf="UF02"),
                  Equipement("11", "PT", "01", uf="UF02")):
            s.ajouter_equipement(e)
        self.mv = next(e for e in s.ouvrage.equipements if e.type == "MV")

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien

    def es(self):
        return {p.nom: p for p in self.s.liste_es()}

    def test_parcours_complet(self):
        s = self.s
        # 5. génération : reflète la configuration réelle, sans aucune variable de supervision préalable
        es = self.es()
        for nom in ("ET_F999RV11MV03_OUV", "ET_F999RV11MV03_FER", "ET_F999RV11MV03_BP_OUV",
                    "ET_F999RV11MV03_BP_FER", "ST_F999RV11MV03_OUV", "ST_F999RV11MV03_FER",
                    "EA_F999RV11CU01_NIV", "ET_F999RV11CU01_PH", "EA_F999RV11PM02_FREQ", "SA_F999RV11PM02_FREQ",
                    "ET_F999RV11FT01_IMP", "EA_F999RV11PT01_PRE"):
            self.assertIn(nom, es)
        self.assertNotIn("EA_F999RV11PM01_FREQ", es)               # pompe directe : pas de variateur
        self.assertNotIn("ET_F999RV11CU01_TP", es)                 # option trop-plein non choisie
        self.assertEqual(es["ET_F999RV11MV03_BP_OUV"].variable, "")  # bouton local : E/S locale
        self.assertEqual(es["ET_F999RV11MV03_OUV"].variable, "TS_F999RV11MV03_OUV")
        self.assertTrue(all(not p.validee and not p.adresse for p in es.values()))
        b = s.bilan_es()
        self.assertEqual(b["total"], len(es))
        # 6. modifier et compléter : désignation, module / voie → adresse calculée, validation
        p = es["ET_F999RV11MV03_OUV"]
        s.definir_es(p.ident_eq, p.cle, designation="FDC ouverture vanne sortie", module="0.2", voie=0, validee=True)
        p = self.es()["ET_F999RV11MV03_OUV"]
        self.assertEqual((p.adresse, p.commentaire, p.validee), ("%I0.2.0", "FDC ouverture vanne sortie", True))
        q = es["ST_F999RV11MV03_OUV"]
        s.definir_es(q.ident_eq, q.cle, module="4", voie=1)
        self.assertEqual(self.es()["ST_F999RV11MV03_OUV"].adresse, "%Q0.4.1")
        r = es["ET_F999RV11MV03_FER"]
        with self.assertRaises(RegleMetier):                        # même voie : refus, rien n'est écrit
            s.definir_es(r.ident_eq, r.cle, module="0.2", voie=0, designation="ne doit pas rester")
        self.assertEqual(self.es()["ET_F999RV11MV03_FER"].designation, "")
        with self.assertRaises(RegleMetier):
            s.definir_es(r.ident_eq, r.cle, type_logique="REAL")   # type impossible pour une ET
        # information par communication : distinguée du câblé, sans adresse exigée
        f = es["EA_F999RV11PM02_FREQ"]
        s.definir_es(f.ident_eq, f.cle, raccordement="Communication", validee=True)
        self.assertEqual(self.es()["EA_F999RV11PM02_FREQ"].raccordement, "Communication")
        self.assertFalse(any("EA_F999RV11PM02_FREQ : adresse physique" in a.message for a in s.anomalies()))
        # 7. équipement personnalisé + E/S ajoutée à la main
        s.ajouter_equipement(Equipement("11", "KM", "01", uf="UF02"))
        cle = s.ajouter_es(self.mv.ident, "ET", "DEF_COUPLE", "Défaut couple actionneur")
        self.assertIn("ET_F999RV11MV03_DEF_COUPLE", self.es())
        with self.assertRaises(RegleMetier):
            s.ajouter_es(self.mv.ident, "ET", "DEF_COUPLE", "doublon")
        # 8. mise à jour : ajout d'une option, retrait d'une E/S, sans doublon ni perte des validations
        self.mv.options.append("Modulante")
        noms = [p.nom for p in s.liste_es()]
        self.assertEqual(len(noms), len(set(noms)))
        self.assertIn("EA_F999RV11MV03_POS", noms)
        p = self.es()["ET_F999RV11MV03_OUV"]
        self.assertEqual((p.adresse, p.validee), ("%I0.2.0", True))   # rien de validé n'a bougé
        s.retirer_es(self.mv.ident, "ES_BP_FER")                      # bouton absent sur le terrain
        self.assertNotIn("ET_F999RV11MV03_BP_FER", self.es())
        s.retirer_es(self.mv.ident, cle)                              # E/S ajoutée : supprimée
        self.assertNotIn("ET_F999RV11MV03_DEF_COUPLE", self.es())
        # changer l'adresse d'une E/S validée la repasse « à valider »
        s.definir_es(p.ident_eq, p.cle, module="0.2", voie=3)
        self.assertFalse(self.es()["ET_F999RV11MV03_OUV"].validee)
        # 9. adresses physiques contrôlées
        self.assertTrue(any("adresse physique à renseigner" in a.message for a in s.anomalies()))
        self.assertTrue(any("non validée" in a.message for a in s.anomalies()))
        # 10. enregistrer, rouvrir : tout est conservé
        chemin = os.path.join(self.dossier, "o.ouvrage.json")
        s.enregistrer(chemin)
        s2 = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        s2.ouvrir(chemin)
        avant = [(p.nom, p.adresse, p.module, p.voie, p.validee, p.raccordement, p.commentaire) for p in s.liste_es()]
        apres = [(p.nom, p.adresse, p.module, p.voie, p.validee, p.raccordement, p.commentaire) for p in s2.liste_es()]
        self.assertEqual(avant, apres)
        # 11. exports Excel et HTML (base du PDF), 12. XSY des E/S adressées seulement
        xlsx = os.path.join(self.dossier, "es.xlsx")
        s2.exporter_liste_es(xlsx)
        with zipfile.ZipFile(xlsx) as z:
            feuille = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        self.assertIn("ET_F999RV11MV03_OUV", feuille)
        self.assertIn("Communication", feuille)
        h = s2.html_liste_es()
        self.assertIn("Liste des entrées / sorties", h)
        self.assertIn("à valider ou à adresser", h)
        xsy = os.path.join(self.dossier, "es.xsy")
        n = s2.exporter_xsy_es(xsy)
        noms_xsy = [v.get("name") for v in ET.parse(xsy).getroot().iter("variables")]
        self.assertEqual(set(noms_xsy), {p.nom for p in s2.liste_es() if p.adresse})
        self.assertEqual(n, len(noms_xsy))
        self.assertFalse(any(nom.startswith(("TS_", "TM_")) for nom in noms_xsy))   # pas de variables d'échange

    def test_liste_es_independante_des_variables(self):
        # la liste existe et s'exporte alors qu'aucune adresse d'échange n'est attribuée
        self.assertTrue(all(not v.adresse for v in self.s.variables()))
        xlsx = os.path.join(self.dossier, "es.xlsx")
        self.assertGreater(self.s.exporter_liste_es(xlsx), 20)

    def test_suppression_equipement_apres_generation(self):
        s = self.s
        p = self.es()["ET_F999RV11MV03_OUV"]
        s.definir_es(p.ident_eq, p.cle, module="0.2", voie=0, validee=True)
        pm = next(e for e in s.ouvrage.equipements if e.type == "PM")
        s.supprimer_equipement(pm.ident)
        p = self.es()["ET_F999RV11MV03_OUV"]
        self.assertEqual((p.adresse, p.validee), ("%I0.2.0", True))
        self.assertFalse(any(x.repere.endswith("PM01") for x in s.liste_es()))

    def test_adresse_module(self):
        self.assertEqual(Session.adresse_module("EA", "1.5", 2), "%IW1.5.2")
        self.assertEqual(Session.adresse_module("SA", "6", "0"), "%QW0.6.0")
        with self.assertRaises(RegleMetier):
            Session.adresse_module("ET", "a", 1)


if __name__ == "__main__":
    unittest.main()
