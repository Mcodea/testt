"""Règles CSS mortes des anciennes feuilles (refonte, lot 7) : sélecteurs qui visent une classe ou un identifiant
qu'aucun code d'OGIAS ne produit plus.

Usage : python outils/interface_css_mort.py [--appliquer] [feuille.css ...]
Sans argument : app.css, v031.css et industrial-ui.css. Sans --appliquer, le programme liste seulement.

Règle de prudence : une classe est vivante dès qu'elle apparaît comme mot dans un script, une page ou le serveur,
ou qu'un de ses préfixes (« v31-f- » pour « v31-f-ET ») est suivi d'une construction dynamique (${…} ou +).
Les jetons placés entre parenthèses (:not(…), :is(…), :has(…)…) sont ignorés : ils ne suffisent jamais à déclarer
une règle morte. Une règle n'est retirée que si TOUS ses sélecteurs sont morts ; sinon seuls les sélecteurs morts
de sa liste sont retirés.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

RACINE = Path(__file__).resolve().parents[1]
STATIQUE = RACINE / "sorep_web" / "static"
FEUILLES = ["app.css", "v031.css", "industrial-ui.css"]


def _sources() -> str:
    fichiers = [*STATIQUE.glob("*.js"), *STATIQUE.glob("*.html"), *(RACINE / "sorep_web").glob("*.py"),
                *(RACINE / "genvar").glob("*.py")]                    # valeurs d'état venues du moteur
    return "\n".join(f.read_text(encoding="utf-8") for f in fichiers)


def _vivant(jeton: str, sources: str) -> bool:
    if re.search(r"(?<![\w-])" + re.escape(jeton) + r"(?![\w-])", sources):
        return True
    morceaux = jeton.split("-")
    for i in range(1, len(morceaux)):
        prefixe = "-".join(morceaux[:i]) + "-"
        if re.search(re.escape(prefixe) + r"""(\$\{|['"]\s*\+)""", sources):
            return True
    return False


def _jetons(selecteur: str) -> list[str]:
    hors_parentheses, profondeur = [], 0
    for c in selecteur:
        profondeur += c == "("
        if not profondeur:
            hors_parentheses.append(c)
        profondeur -= c == ")" and profondeur > 0
    texte = re.sub(r"\[[^\]]*\]", "", "".join(hors_parentheses))      # [attr="…"] : pas de jeton
    return re.findall(r"[.#](-?[A-Za-z_][\w-]*)", texte)


def _regles(css: str):
    """(début, fin du bloc, début du sélecteur, fin du sélecteur) de chaque règle de style, @media compris."""
    i, n, pile = 0, len(css), []
    debut_sel = 0
    while i < n:
        if css.startswith("/*", i):
            i = css.index("*/", i) + 2
            if not pile or pile[-1] == "@":
                debut_sel = i
            continue
        c = css[i]
        if c == "{":
            entete = css[debut_sel:i].strip()
            if entete.startswith("@"):
                pile.append("@")
                debut_sel = i + 1
            else:
                fin = css.index("}", i)
                yield debut_sel, fin + 1, entete
                i = fin + 1
                debut_sel = i
                continue
        elif c == "}":
            if pile:
                pile.pop()
            debut_sel = i + 1
        elif c == ";" and (not pile or pile[-1] == "@") and css[debut_sel:i].strip().startswith("@"):
            debut_sel = i + 1
        i += 1


def analyser(feuille: Path, sources: str):
    css = feuille.read_text(encoding="utf-8")
    morts = []
    for debut, fin, entete in _regles(css):
        selecteurs = [s.strip() for s in entete.split(",") if s.strip()]
        mort = [s for s in selecteurs if any(not _vivant(j, sources) for j in _jetons(s))]
        if mort:
            morts.append((debut, fin, entete, selecteurs, mort))
    return css, morts


def appliquer(feuille: Path, sources: str) -> int:
    css, morts = analyser(feuille, sources)
    for debut, fin, entete, selecteurs, mort in reversed(morts):
        bloc = css[debut:fin]
        if len(mort) == len(selecteurs):
            # retire la règle et, s'il y en a, ses espaces de tête (la ligne vide éventuelle reste)
            css = css[:debut] + bloc[len(bloc) - len(bloc.lstrip()):][len(bloc.lstrip()):] + css[fin:]
        else:
            garde = ",".join(s for s in selecteurs if s not in mort)
            tete = bloc[: len(bloc) - len(bloc.lstrip())]
            css = css[:debut] + tete + garde + bloc[bloc.index("{"):] + css[fin:]
    feuille.write_text(css, encoding="utf-8")
    return len(morts)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--appliquer"]
    sources = _sources()
    for nom in args or FEUILLES:
        feuille = STATIQUE / nom
        if "--appliquer" in sys.argv:
            print(f"{nom} : {appliquer(feuille, sources)} règle(s) nettoyée(s)")
        else:
            _, morts = analyser(feuille, sources)
            print(f"== {nom} : {len(morts)} règle(s) avec sélecteur mort")
            for _d, _f, _e, sel, mort in morts:
                print(("   [règle entière] " if len(mort) == len(sel) else "   [en partie]     ") + " | ".join(mort)[:160])
