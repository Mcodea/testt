"""Non-régression de la gestion des projets et de l'adressage de la V0.6."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from genvar import chemins, projets
from genvar.catalogue import Catalogue
from genvar.modele import Ouvrage, Equipement, SousEnsemble
from genvar.session import Session, RegleMetier


class TestRegistreProjets(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.contexte = patch.dict(os.environ, {"SOREP_DATA_DIR": self.tmp.name})
        self.contexte.start()
        self.addCleanup(self.contexte.stop)
        self.repertoire = Path(chemins.dossier_projets())

    def fichier(self, nom, **champs):
        o = Ouvrage(lieu="XT25", code_ouvrage="RV", libelle=nom, **champs)
        cible = self.repertoire / (nom + ".ouvrage.json")
        o.enregistrer(str(cible))
        return cible

    def test_accueil_liste_archivage_sans_suppression(self):
        p = self.fichier("reservoir")
        fiches = projets.lister()
        self.assertEqual(len(fiches), 1)
        self.assertFalse(fiches[0].archive)
        projets.archiver(str(p), True)
        self.assertTrue(p.exists())
        self.assertTrue(projets.lister()[0].archive)
        projets.archiver(str(p), False)
        self.assertFalse(projets.lister()[0].archive)
        self.assertTrue(Path(str(p) + ".bak").exists())

    def test_duplication_identite_independante(self):
        p = self.fichier("reservoir")
        o = Ouvrage.ouvrir(str(p))
        o.sous_ensembles.append(SousEnsemble("11"))
        eq = Equipement("11", "PM", "01")
        o.equipements.append(eq)
        o.enregistrer(str(p))
        cible = projets.dupliquer(str(p))
        original = Ouvrage.ouvrir(str(p))
        copie = Ouvrage.ouvrir(cible)
        self.assertNotEqual(original.ident_projet, copie.ident_projet)
        self.assertNotEqual(original.equipements[0].ident, copie.equipements[0].ident)
        self.assertEqual(original.equipements[0].type, copie.equipements[0].type)

    def test_import_anciens_projets_sans_doublon(self):
        with tempfile.TemporaryDirectory() as ancien:
            source = Path(ancien) / "Donnees" / "Projets"
            source.mkdir(parents=True)
            Ouvrage(lieu="XT25", code_ouvrage="SP", libelle="Station").enregistrer(
                str(source / "station.ouvrage.json"))
            self.assertEqual(len(projets.importer_dossier(ancien)), 1)
            self.assertEqual(len(projets.importer_dossier(ancien)), 0)
            self.assertEqual(len(projets.lister()), 1)
            self.assertTrue((source / "station.ouvrage.json").exists())

    def test_fichier_illisible_sans_faire_disparaitre_les_autres(self):
        self.fichier("reservoir")
        (self.repertoire / "incomplet.ouvrage.json").write_text("{", encoding="utf-8")
        f = projets.lister()
        self.assertEqual(len(f), 2)
        self.assertEqual(sum(bool(x.erreur) for x in f), 1)


class TestAdressageSecurise(unittest.TestCase):
    def setUp(self):
        self.s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
        self.s.definir("lieu", "XT25")
        self.s.definir("code_ouvrage", "RV")
        self.s.ajouter_sous_ensemble("11", "Essai")
        self.s.ajouter_equipement(Equipement("11", "PM", "01", options=["Variateur"]))
        self.s.modifie = False

    def trouve(self, nom):
        famille, code = nom.split("_", 1)
        return next(v for v in self.s.variables() if v.famille == famille and v.code == code)

    def test_bit_hors_plage_rejete_et_aucun_changement(self):
        v = self.trouve("TS_MA")
        with self.assertRaisesRegex(RegleMetier, "Bit invalide"):
            self.s.definir_adresses(v.ident_eq, v.cle, adresse="%MW1000.16")
        self.assertEqual(self.s.ouvrage.equipement(v.ident_eq).adresses, {})

    def test_adresse_reelle_pair_et_miroir_rtr(self):
        prop, erreur = self.s.plan()
        self.assertFalse(erreur)
        self.s.appliquer(prop)
        adresses = {v.nom: v.adresse for v in self.s.variables()}
        self.assertEqual(adresses[self.trouve("TR_FREQ").nom], "%MW100")
        self.assertEqual(adresses[self.trouve("RTR_FREQ").nom], "%MW4000")

    def test_collision_refusee_et_transaction_atomique(self):
        a = self.trouve("TS_MA")
        b = self.trouve("TS_DEF")
        self.s.definir_adresses(a.ident_eq, a.cle, adresse="%MW1000.0")
        with self.assertRaisesRegex(RegleMetier, "déjà occupée"):
            self.s.definir_adresses(b.ident_eq, b.cle, adresse="%MW1000.0")
        self.assertEqual(self.s.ouvrage.equipement(b.ident_eq).adresses.get(b.cle), None)
        with self.assertRaises(RegleMetier):
            self.s.definir_adresses(a.ident_eq, a.cle, adresse="%MW1000.1", adresse_es="%QW0.1.0")
        self.assertEqual(self.s.ouvrage.equipement(a.ident_eq).adresses.get(a.cle), "%MW1000.0")

    def test_refus_plan_partiel_sans_effacer_adresse(self):
        props, err = self.s.plan()
        self.assertFalse(err)
        self.s.appliquer(props)
        adresses_anciennes = {v.nom: v.adresse for v in self.s.variables()}
        self.s.ouvrage.zones_fin['TR'] = 101
        with self.assertRaises(RegleMetier):
            self.s.appliquer([], tout_refaire=True)
        self.assertEqual(adresses_anciennes, {v.nom: v.adresse for v in self.s.variables()})

    def test_projet_existant_non_redit_editable(self):
        self.s.definir("mode", "Existant")
        v = self.trouve("TS_MA")
        with self.assertRaises(RegleMetier):
            self.s.definir_adresses(v.ident_eq, v.cle, adresse="%MW1000.0")


if __name__ == "__main__":
    unittest.main()
