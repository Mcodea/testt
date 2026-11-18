"""Système de design de l'interface (refonte, lot 1) : garde-fous automatiques.

- ogias.css est la source unique des couleurs : chargée en dernier, couleurs écrites seulement dans les blocs de jetons ;
- les thèmes clair et sombre définissent les mêmes jetons ;
- contrastes WCAG 2.1 AA vérifiés par le calcul (texte 4,5:1, bordure de champ 3:1) ;
- cliquet : les anciennes feuilles ne gagnent plus aucune couleur en dur ni aucun « !important » (valeurs du lot 0).
"""
from __future__ import annotations

from pathlib import Path
import re
import unittest

STATIC = Path(__file__).resolve().parents[1] / "sorep_web" / "static"
OGIAS = (STATIC / "ogias.css").read_text(encoding="utf-8")
BLOC_CLAIR = ':root, html[data-theme="light"] {'
BLOC_SOMBRE = 'html[data-theme="dark"] {'
RE_COULEUR = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(")
# Plafonds qui ne remontent jamais : mesures du lot 0, abaissées à chaque lot qui retire d'anciennes règles
# (lot 2b : contrôles d'étape déplacés au panneau de sortie, leurs anciens styles retirés).
PLAFONDS = {"app.css": (348, 28), "v031.css": (53, 98), "industrial-ui.css": (83, 99)}


def _sans_commentaires(texte: str) -> str:
    return re.sub(r"/\*.*?\*/", "", texte, flags=re.S)


def _bloc(entete: str) -> str:
    debut = OGIAS.index(entete)
    return OGIAS[debut:OGIAS.index("}", debut)]


def _jetons(entete: str) -> dict[str, str]:
    return dict(re.findall(r"(--o-[\w-]+)\s*:\s*([^;]+);", _sans_commentaires(_bloc(entete))))


def _luminance(hexa: str) -> float:
    canaux = [int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canaux]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contraste(a: str, b: str) -> float:
    claire, foncee = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (claire + 0.05) / (foncee + 0.05)


# (texte, fond, seuil) : seuil 4,5 pour du texte, 3 pour une bordure de composant
PAIRES = ([(t, f, 4.5) for t in ("texte", "texte-2", "texte-3") for f in ("surface", "surface-2", "surface-3", "fond")]
          + [("action", "surface", 4.5), ("action", "surface-2", 4.5), ("action", "action-fond", 4.5),
             ("texte", "action-fond", 4.5), ("sur-action", "action-plein", 4.5), ("sur-action", "action-survol", 4.5),
             ("ok", "ok-fond", 4.5), ("ok", "surface", 4.5), ("alerte", "alerte-fond", 4.5), ("alerte", "surface", 4.5),
             ("erreur", "erreur-fond", 4.5), ("erreur", "surface", 4.5),
             ("nuit-texte", "nuit", 4.5), ("nuit-texte-2", "nuit", 4.5),
             ("nuit-texte", "nuit-2", 4.5), ("nuit-texte-2", "nuit-2", 4.5),
             ("champ-bord", "surface", 3), ("champ-bord", "surface-2", 3), ("champ-bord", "fond", 3)])


class TestSystemeDesign(unittest.TestCase):
    def test_ogias_css_chargee_en_dernier(self):
        page = (STATIC / "index.html").read_text(encoding="utf-8")
        feuilles = re.findall(r'<link rel="stylesheet" href="([^"]+)"', page)
        self.assertEqual(feuilles[-1], "ogias.css", feuilles)

    def test_couleurs_seulement_dans_les_blocs_de_jetons(self):
        reste = _sans_commentaires(OGIAS.replace(_bloc(BLOC_CLAIR), "").replace(_bloc(BLOC_SOMBRE), ""))
        self.assertEqual(RE_COULEUR.findall(reste), [], "couleur écrite en dur hors des jetons dans ogias.css")

    def test_memes_jetons_dans_les_deux_themes(self):
        self.assertEqual(set(_jetons(BLOC_CLAIR)), set(_jetons(BLOC_SOMBRE)))
        self.assertGreaterEqual(len(_jetons(BLOC_CLAIR)), 30)

    def test_contrastes_wcag_aa(self):
        for nom, entete in (("clair", BLOC_CLAIR), ("sombre", BLOC_SOMBRE)):
            j = _jetons(entete)
            for texte, fond, seuil in PAIRES:
                with self.subTest(theme=nom, texte=texte, fond=fond):
                    r = contraste(j["--o-" + texte].strip(), j["--o-" + fond].strip())
                    self.assertGreaterEqual(r, seuil, f"{nom} : --o-{texte} sur --o-{fond} = {r:.2f}:1")

    def test_jetons_utilises_sont_definis(self):
        definis = set(_jetons(BLOC_CLAIR)) | set(re.findall(r"(--o-[\w-]+)\s*:", OGIAS))
        for f in STATIC.glob("*.css"):
            for nom in set(re.findall(r"var\((--o-[\w-]+)", f.read_text(encoding="utf-8"))):
                with self.subTest(feuille=f.name, jeton=nom):
                    self.assertIn(nom, definis)

    def test_anciennes_feuilles_ne_regressent_pas(self):
        for nom, (couleurs, important) in PLAFONDS.items():
            texte = (STATIC / nom).read_text(encoding="utf-8")
            with self.subTest(feuille=nom):
                self.assertLessEqual(len(RE_COULEUR.findall(texte)), couleurs, "nouvelle couleur en dur")
                self.assertLessEqual(texte.count("!important"), important, "nouveau !important")

    def test_pas_de_nouvelle_feuille_de_style(self):
        self.assertEqual(sorted(f.name for f in STATIC.glob("*.css")),
                         ["app.css", "industrial-ui.css", "ogias.css", "v031.css"])


if __name__ == "__main__":
    unittest.main()
