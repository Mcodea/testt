"""Relevé de l'interface pour la refonte : captures de chaque écran (clair et sombre) et registre des commandes.

Usage : python outils/interface_releve.py <url du serveur de démonstration> <dossier de sortie> [actions.json de référence]
Le serveur vient de outils/interface_demo.py (ouvrage fictif). Produit :
- <sortie>/captures/<écran>_<thème>.png ;
- <sortie>/actions.json : pour chaque écran, les commandes visibles (boutons, liens d'action, champs).
Le registre sert à vérifier, lot après lot, qu'aucune commande ne disparaît d'un écran refait : avec un registre de
référence (par exemple validation/refonte_interface/lot0_avant/actions.json), les commandes disparues sont listées
et le programme s'arrête en erreur s'il en manque.
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
             ".v30-ribbon button, #o-sortie .parcours-points button")   # lot 2b : contrôles déplacés au panneau de sortie
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


def disparues(reference: Path, actuel: Path) -> dict[str, list[str]]:
    """Commandes du registre de référence absentes du registre actuel, par écran."""
    ref, act = (json.loads(p.read_text(encoding="utf-8")) for p in (reference, actuel))
    sortie = {}
    for ecran, commandes in ref.items():
        avant = {x["cle"] or x["texte"] for x in commandes}
        apres = {x["cle"] or x["texte"] for x in act.get(ecran, [])}
        if avant - apres:
            sortie[ecran] = sorted(avant - apres)
    return sortie


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        raise SystemExit(__doc__)
    resultat = releve(sys.argv[1].rstrip("/") + "/", Path(sys.argv[2]))
    if len(sys.argv) == 4:
        resultat["commandes_disparues"] = disparues(Path(sys.argv[3]), Path(sys.argv[2]) / "actions.json")
    print(json.dumps(resultat, ensure_ascii=False, indent=1))
    if resultat.get("commandes_disparues") or resultat["erreurs_js"]:
        raise SystemExit(1)
