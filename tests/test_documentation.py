"""Documentation livrée (cahier § 9) : présence, cohérence avec le dépôt, aucune capture manquante."""
import re
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


class TestDocumentation(unittest.TestCase):
    def test_documents_attendus(self):
        for nom in ("MANUEL_UTILISATEUR.md", "MANUEL_UTILISATEUR.pdf", "GUIDE_ADMINISTRATEUR.md", "CHANGELOG.md",
                    "LICENCES_TIERCES.md", "COMPATIBILITE.md", "LICENCE.md"):
            with self.subTest(nom=nom):
                self.assertTrue((RACINE / nom).is_file(), nom)
        self.assertTrue((RACINE / "MANUEL_UTILISATEUR.pdf").read_bytes().startswith(b"%PDF"))

    def test_captures_du_manuel_presentes(self):
        texte = (RACINE / "MANUEL_UTILISATEUR.md").read_text(encoding="utf-8")
        images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", texte)
        self.assertGreaterEqual(len(images), 10)
        for chemin in images:
            with self.subTest(chemin=chemin):
                f = RACINE / chemin
                self.assertTrue(f.is_file(), chemin)
                self.assertTrue(f.read_bytes().startswith(b"\x89PNG"))

    def test_chaque_bibliotheque_livree_a_sa_licence(self):
        licences = (RACINE / "LICENCES_TIERCES.md").read_text(encoding="utf-8").lower()
        for ligne in (RACINE / "requirements-runtime.lock").read_text(encoding="utf-8").splitlines():
            if ligne.strip() and not ligne.startswith("#"):
                nom, version = ligne.split("==")
                with self.subTest(nom=nom):
                    self.assertIn(nom.lower(), licences)
                    self.assertIn(version, licences)
        for police in ("inter", "jetbrains mono", "lucide"):
            self.assertIn(police, licences)

    def test_journal_des_modifications_au_format_keep_a_changelog(self):
        texte = (RACINE / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("keepachangelog.com", texte)
        self.assertIn("## [Non publié]", texte)
        self.assertTrue(re.search(r"^## \[\d+\.\d+(\.\d+)?\] — \d{2}/\d{2}/\d{4}$", texte, re.M))

    def test_guide_administrateur_coherent_avec_le_code(self):
        guide = (RACINE / "GUIDE_ADMINISTRATEUR.md").read_text(encoding="utf-8")
        from genvar import formats_appris, gammes_materiel  # noqa: F401 — modules décrits par le guide
        for attendu in ("SOREP_DATA_DIR", "GenerateurVariables_Atelier", "journal.log", ".verrou", "127.0.0.1",
                        "Referentiel/", "formats_appris/", "gammes_materiel/", "modeles_livrables/",
                        "standards_ingenierie.json", "attributs_equipements.json"):
            with self.subTest(attendu=attendu):
                self.assertIn(attendu, guide)


if __name__ == "__main__":
    unittest.main()
