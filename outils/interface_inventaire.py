"""Inventaire chiffré des styles et scripts de l'interface : mesure l'avancement de la refonte, lot après lot.

Usage : python outils/interface_inventaire.py [dossier static] — affiche un JSON.
Compte, pour chaque feuille de style : règles, couleurs écrites en dur, « !important », variables définies ;
pour l'ensemble : sélecteurs redéfinis dans plusieurs feuilles, tailles de police, rayons et couleurs distincts ;
pour chaque script : styles en ligne, couleurs en dur, messages éphémères (toast).
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import re
import sys

STATIC = Path(__file__).resolve().parents[1] / "sorep_web" / "static"
RE_COULEUR = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(")


def regles(texte: str) -> list[tuple[str, str]]:
    """(sélecteur, déclarations) de chaque règle, @media compris ; commentaires retirés."""
    texte = re.sub(r"/\*.*?\*/", "", texte, flags=re.S)
    sortie, pile, tampon = [], [], ""
    for c in texte:
        if c == "{":
            pile.append(tampon.strip())
            tampon = ""
        elif c == "}":
            if pile:
                sel = pile.pop()
                if not sel.startswith("@") and tampon.strip():
                    sortie.append((sel, tampon.strip()))
            tampon = ""
        else:
            tampon += c
    return sortie


def inventaire(static: Path = STATIC) -> dict:
    feuilles = sorted(static.glob("*.css"))
    par_selecteur: dict[str, set] = defaultdict(set)
    tout, res = "", {"css": {}, "js": {}}
    for f in feuilles:
        t = f.read_text(encoding="utf-8")
        tout += t
        r = regles(t)
        for sel, _ in r:
            for s in sel.split(","):
                par_selecteur[re.sub(r"\s+", " ", s.strip())].add(f.name)
        res["css"][f.name] = {"lignes": t.count("\n"), "regles": len(r), "couleurs_en_dur": len(RE_COULEUR.findall(t)),
                              "important": t.count("!important"),
                              "variables_definies": len(set(re.findall(r"(--[\w-]+)\s*:", t)))}
    tailles = set(re.findall(r"font-size\s*:\s*([\d.]+(?:px|rem|em))", tout))
    res["selecteurs_redefinis_dans_plusieurs_feuilles"] = sum(1 for v in par_selecteur.values() if len(v) > 1)
    res["tailles_de_police_distinctes"] = len(tailles)
    res["rayons_distincts"] = len(set(x.strip() for x in re.findall(r"border-radius\s*:\s*([^;}\n]+)", tout)))
    res["couleurs_distinctes"] = len({c.lower() for c in re.findall(r"#[0-9a-fA-F]{3,8}\b", tout)})
    for f in sorted(static.glob("*.js")):
        t = f.read_text(encoding="utf-8")
        res["js"][f.name] = {"lignes": t.count("\n"), "styles_en_ligne": len(re.findall(r"style=[\"'\\]", t)),
                             "couleurs_en_dur": len(re.findall(r"#[0-9a-fA-F]{6}\b", t)), "toasts": t.count("toast(")}
    return res


if __name__ == "__main__":
    print(json.dumps(inventaire(Path(sys.argv[1]) if len(sys.argv) > 1 else STATIC), ensure_ascii=False, indent=1))
