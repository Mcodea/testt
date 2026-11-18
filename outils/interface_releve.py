"""Relevé de l'interface pour la refonte : captures de chaque écran (clair et sombre) et registre des commandes.

Usage : python outils/interface_releve.py <url du serveur de démonstration> <dossier de sortie>
Le serveur vient de outils/interface_demo.py (ouvrage fictif). Produit :
- <sortie>/captures/<écran>_<thème>.png ;
- <sortie>/actions.json : pour chaque écran, les commandes visibles (boutons, liens d'action, champs).
Le registre sert à vérifier, lot après lot, qu'aucune commande ne disparaît d'un écran refait.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

from playwright.sync_api import sync_playwright

ECRANS = [("01_ouvrages", "#/ouvrages"), ("02_tableau_de_bord", "#/dashboard"), ("03_equipements", "#/inventaire"),
          ("04_liste_es", "#/es"), ("05_materiel", "#/materiel"), ("06_variables", "#/variables"),
          ("07_recette", "#/recette"), ("08_referentiel", "#/referentiel")]

# Clé stable d'une commande : son id, sinon ses attributs data-* (avec la valeur pour ceux qui désignent l'action).
SELECTEUR = ("#vue button, #vue [role=button], #vue a[data-nav], #vue input, #vue select, #vue textarea, "
             ".v30-ribbon button")
COMMANDES = """() => [...document.querySelectorAll('""" + SELECTEUR + """')]
  .filter(e => e.offsetParent !== null)
  .map(e => { const d = Object.keys(e.dataset).filter(k => !k.startsWith('v31')).sort();
    const cle = e.id ? '#' + e.id : d.length ? '[' + d.map(k => k + (['export', 'action', 'nav', 'onglet', 'ptOnglet']
      .includes(k) ? '=' + e.dataset[k] : '')).join('][') + ']' : '';
    const texte = (e.innerText || e.value || e.getAttribute('aria-label') || e.placeholder || '').trim()
      .replace(/\\s+/g, ' ').slice(0, 60);
    return {cle, balise: e.tagName.toLowerCase(), texte}; })
  .filter(x => x.cle || x.texte)"""


def _commandes(page) -> list[dict]:
    vues, sortie = set(), []
    for x in page.evaluate(COMMANDES):
        k = (x["cle"], "" if x["cle"] else x["texte"])
        if k not in vues:
            vues.add(k)
            sortie.append(x)
    return sortie


def releve(url: str, sortie: Path) -> dict:
    (sortie / "captures").mkdir(parents=True, exist_ok=True)
    registre: dict[str, list] = {}
    erreurs: list[str] = []
    with sync_playwright() as p:
        navigateur = p.chromium.launch()
        for theme in ("clair", "sombre"):
            ctx = navigateur.new_context(viewport={"width": 1600, "height": 900})
            valeur = "dark" if theme == "sombre" else "light"
            ctx.add_init_script(f"try{{localStorage.setItem('ogias-ui-theme','{valeur}')}}catch(e){{}}")
            page = ctx.new_page()
            page.on("pageerror", lambda e: erreurs.append(str(e)))
            page.goto(url + "#/ouvrages", wait_until="networkidle")
            time.sleep(0.5)
            page.locator("[data-project]").first.click()
            time.sleep(0.8)
            for nom, route in ECRANS:
                page.evaluate(f"location.hash='{route}'")
                page.wait_for_load_state("networkidle")
                time.sleep(0.9)
                page.screenshot(path=str(sortie / "captures" / f"{nom}_{theme}.png"))
                if theme == "clair":
                    registre[nom[3:]] = _commandes(page)
                if nom == "03_equipements":                    # fiche d'un équipement : premier de l'arborescence
                    page.locator("[data-v]").nth(1).click()
                    time.sleep(0.8)
                    page.screenshot(path=str(sortie / "captures" / f"03b_fiche_equipement_{theme}.png"))
                    if theme == "clair":
                        registre["fiche_equipement"] = _commandes(page)
            ctx.close()
        navigateur.close()
    (sortie / "actions.json").write_text(json.dumps(registre, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"commandes": {k: len(v) for k, v in registre.items()}, "erreurs_js": erreurs}


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    print(json.dumps(releve(sys.argv[1].rstrip("/") + "/", Path(sys.argv[2])), ensure_ascii=False, indent=1))
