"""Modèles de livrables à variables (lot 1, 19/11/2026) : syntaxe, portées, blocs, encodage, bibliothèque.
Ouvrage fictif (lieu XTST) ; modèles d'essai neutres (format d'aucun outil)."""
import os
import tempfile
import unittest
from unittest import mock

from genvar import modeles_livrables as ml
from genvar.modele import Equipement
from tests.test_coherence import nouvelle


def ouvrage():
    s = nouvelle()
    for t, n in (("HV", "01"), ("PM", "01")):
        e = s.ajouter_equipement(Equipement("00", t, n, "Fictif"))
        s.decider_propositions(e.ident, "retenir")
    return s


class TestSyntaxe(unittest.TestCase):
    def test_portees_et_blocs(self):
        _, erreurs, emplois = ml.analyser("<#OUVRAGE#><#DEBUT_EQUIPEMENTS#><#REPERE#><#DEBUT_VARIABLES_TS#><#NOM#>"
                                          "<#FIN_VARIABLES_TS#><#FIN_EQUIPEMENTS#>")
        self.assertEqual(erreurs, [])
        self.assertEqual({e["nom"]: e["portee"] for e in emplois}, {"OUVRAGE": "ouvrage", "REPERE": "équipement",
                                                                     "NOM": "variable"})

    def test_erreurs_signalees(self):
        cas = {"<#NOM#>": "bloc VARIABLES", "<#INCONNUE#>": "inconnue", "<#DEBUT_ES#>": "jamais fermé",
               "<#DEBUT_VARIABLES#><#FIN_ES#><#FIN_VARIABLES#>": "ne ferme pas",
               "<#DEBUT_VARIABLES#><#DEBUT_EQUIPEMENTS#><#FIN_EQUIPEMENTS#><#FIN_VARIABLES#>": "mal imbriqué",
               "<#DEBUT_VARIABLES_XX#><#FIN_VARIABLES_XX#>": "Bloc inconnu", "<#N#>": "dans un bloc"}
        for texte, attendu in cas.items():
            with self.subTest(texte=texte):
                erreurs = ml.analyser(texte)[1]
                self.assertTrue(any(attendu in e for e in erreurs), erreurs)
                with self.assertRaises(ml.ModeleRefuse):
                    ml.remplir(texte, ouvrage())

    def test_balise_seule_sur_sa_ligne(self):
        s = ouvrage()
        sortie = ml.remplir("A\r\n<#DEBUT_EQUIPEMENTS#>\r\n<#N#>;<#REPERE#>\r\n<#FIN_EQUIPEMENTS#>\r\nZ", s)
        self.assertEqual(sortie, "A\r\n1;XTSTRV01HV01\r\n2;XTSTRV01PM01\r\nZ")


class TestRemplissage(unittest.TestCase):
    def test_exemple_csv(self):
        s = ouvrage()
        lignes = ml.remplir(ml.EXEMPLE, s).split("\r\n")
        self.assertEqual(lignes[0], "Repère;Variable;Famille;Type;Adresse automate;Registre Modbus;Libellé")
        self.assertEqual(len([x for x in lignes[1:] if x]), len(s.variables()))
        self.assertTrue(all(x.startswith("XTSTRV01") for x in lignes[1:] if x))

    def test_blocs_imbriques_et_filtres(self):
        s = ouvrage()
        sortie = ml.remplir("<#DEBUT_EQUIPEMENTS#>[<#REPERE#>:<#DEBUT_ES_ET#><#ES_NOM#>,<#FIN_ES_ET#>]<#FIN_EQUIPEMENTS#>", s)
        es_hv = sorted(p.nom for p in s.points() if p.point == "ET" and "HV01" in p.repere)
        self.assertTrue(sortie.startswith("[XTSTRV01HV01:" + ",".join(es_hv) + ",]"))
        familles = {x.split("|")[1] for x in ml.remplir("<#DEBUT_VARIABLES_TS#><#NOM#>|<#FAMILLE#>\n<#FIN_VARIABLES_TS#>", s).split("\n") if x}
        self.assertEqual(familles, {"TS"})

    def test_echappement_xml(self):
        s = ouvrage()
        s.ouvrage.libelle = "Réservoir <A> & B"
        self.assertEqual(ml.remplir("<v n=\"<#LIBELLE_OUVRAGE#>\"/>", s, "xml"), "<v n=\"Réservoir &lt;A&gt; &amp; B\"/>")
        self.assertEqual(ml.remplir("<#LIBELLE_OUVRAGE#>", s), "Réservoir <A> & B")


class TestBibliotheque(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.addCleanup(self.dossier.cleanup)
        p = mock.patch.dict(os.environ, {"SOREP_DATA_DIR": self.dossier.name})
        p.start()
        self.addCleanup(p.stop)

    def test_import_generation_suppression(self):
        self.assertEqual(ml.lister(), [])
        m = ml.ajouter_exemple()
        self.assertEqual((m["extension"], m["encodage"]), ("csv", "utf-8"))
        self.assertEqual(ml.resume(m)["erreurs"], [])
        nom, octets = ml.generer(m["ident"], ouvrage())
        self.assertTrue(nom.endswith("_Exemple_liste_des_variables_CSV.csv"))
        self.assertTrue(octets.decode("utf-8").startswith("Repère;Variable"))
        with self.assertRaisesRegex(ml.ModeleRefuse, "déjà le nom"):
            ml.ajouter_exemple()
        ml.supprimer(m["ident"])
        self.assertEqual(ml.lister(), [])

    def test_encodage_windows_conserve(self):
        octets = "Désignation;<#OUVRAGE#>\r\n".encode("cp1252")
        m = ml.importer("Modèle Windows fictif", "fictif.txt", octets)
        self.assertEqual(m["encodage"], "cp1252")
        s = ouvrage()
        self.assertEqual(ml.generer(m["ident"], s)[1], "Désignation;XTSTRV01\r\n".encode("cp1252"))
        s.ouvrage.libelle = "Réservoir ★"
        m2 = ml.importer("Modèle Windows fictif 2", "fictif.txt", "Libellé : <#LIBELLE_OUVRAGE#>".encode("cp1252"))
        with self.assertRaisesRegex(ml.ModeleRefuse, "encodage"):
            ml.generer(m2["ident"], s)

    def test_refus_a_l_import(self):
        for octets, attendu in ((b"sans variable", "Aucune variable"), (b"\x00\x01<#OUVRAGE#>", "binaire"), (b"", "vide")):
            with self.subTest(attendu=attendu), self.assertRaisesRegex(ml.ModeleRefuse, attendu):
                ml.importer("Modèle fictif", "f.txt", octets)
        self.assertEqual(ml.lister(), [])

    def test_modele_avec_erreur_garde_mais_generation_refusee(self):
        m = ml.importer("Modèle fictif à corriger", "f.txt", b"<#NOM#>")
        self.assertTrue(ml.resume(m)["erreurs"])
        with self.assertRaisesRegex(ml.ModeleRefuse, "corriger"):
            ml.generer(m["ident"], ouvrage())


if __name__ == "__main__":
    unittest.main()
