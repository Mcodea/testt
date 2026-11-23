"""Icônes : Lucide embarquées, jamais d'emoji ni de pictogramme de texte (cahier V1-4-23)."""
import re
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
# Émojis, symboles divers et dingbats (✓ ✕ ⚠ ★…), sélecteur d'emoji. Restent permis : le séparateur « · », les flèches
# et les chevrons typographiques (← → ↑ ↓ ▾ ▸) qui servent de repères de texte.
PICTOGRAMMES = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]")


class TestAucunEmoji(unittest.TestCase):
    def test_interface_et_textes_livres_sans_pictogramme(self):
        fichiers = [f for d in ("sorep_web", "genvar") for f in (RACINE / d).rglob("*")
                    if f.suffix in (".js", ".html", ".css", ".py", ".json") and "tiers" not in f.parts and "data" not in f.parts]
        self.assertGreater(len(fichiers), 20)
        for f in fichiers:
            texte = f.read_text(encoding="utf-8", errors="ignore")
            trouves = sorted(set(PICTOGRAMMES.findall(texte)))
            with self.subTest(fichier=str(f.relative_to(RACINE))):
                self.assertEqual(trouves, [], f"pictogramme(s) {[hex(ord(c)) for c in trouves]} : utiliser une icône Lucide")


if __name__ == "__main__":
    unittest.main()
