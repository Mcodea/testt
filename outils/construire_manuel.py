"""Construit le manuel de l'utilisateur : captures de l'interface réelle sur l'ouvrage FICTIF de démonstration, puis
MANUEL_UTILISATEUR.pdf à partir de MANUEL_UTILISATEUR.md (cahier V1-9-06, V1-9-07).

Usage : python outils/construire_manuel.py [--sans-pdf]

- Les captures sont prises par `outils/interface_demo.py` (lieu XTST, aucune donnée réelle) dans
  `docs/manuel/captures/`, à 1440 × 900.
- Le PDF est imprimé par Chromium (Playwright) à partir du Markdown converti par markdown-it-py (outil de
  développement, `requirements-ci.lock`) ; il n'est pas livré par le programme, seulement avec la documentation.
"""
from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
CAPTURES = RACINE / "docs" / "manuel" / "captures"
SOURCE = RACINE / "MANUEL_UTILISATEUR.md"
PDF = RACINE / "MANUEL_UTILISATEUR.pdf"
EXEMPLE_FORMAT = ('"Name","Data Type","Logical Address","Comment"\n'
                  '"Marche","Bool","%I4.0","Marche"\n"Niveau","Int","%IW64","Niveau"\n')


def demarrer_demo(dossier: Path) -> tuple[subprocess.Popen, str]:
    srv = subprocess.Popen([sys.executable, str(RACINE / "outils" / "interface_demo.py"), str(dossier)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    for _ in range(600):
        f = dossier / "url.txt"
        if f.exists() and f.read_text(encoding="utf-8").strip():
            return srv, f.read_text(encoding="utf-8").strip()
        if srv.poll() is not None:
            break
        time.sleep(0.1)
    srv.kill()
    raise RuntimeError("Le serveur de démonstration n'a pas démarré.")


def api(url: str, route: str, corps: dict | None = None):
    req = urllib.request.Request(url + route.lstrip("/"), data=None if corps is None else json.dumps(corps).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def captures(url: str, travail: Path) -> None:
    from playwright.sync_api import sync_playwright
    CAPTURES.mkdir(parents=True, exist_ok=True)
    exemple = travail / "liste_es_exemple.csv"
    exemple.write_text(EXEMPLE_FORMAT, encoding="utf-8")
    with sync_playwright() as p:
        nav = p.chromium.launch()
        page = nav.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)

        def ecran(route: str, nom: str, attendre: str = "#vue *"):
            page.goto(url + route, wait_until="networkidle")
            page.locator(attendre).first.wait_for()
            page.wait_for_timeout(500)
            page.screenshot(path=str(CAPTURES / f"{nom}.png"))

        ecran("#/ouvrages", "01_mes_ouvrages")
        ecran("#/dashboard", "02_tableau_de_bord")
        ecran("#/inventaire", "03_equipements")
        ecran("#/es", "04_liste_es")
        ecran("#/materiel", "05_materiel")
        ecran("#/variables", "06_variables")
        ecran("#/recette", "07_recette", "#rc-indices .rc-groupe-tete")
        api(url, "/api/revisions/action", {"action": "livrer", "motif": "Première diffusion pour visa",
                                            "auteur": "Bureau d'études"})
        api(url, "/api/revisions/action", {"action": "suivant"})
        eq = api(url, "/api/ouvrage")["equipements"][0]
        api(url, "/api/equipement/modifier", {"ident": eq["ident"], "type": eq["type"], "numero": "77",
                                               "se": eq.get("se") or "00"})
        page.goto(url + "#/dashboard", wait_until="networkidle")      # même ancre : pas de nouveau rendu
        page.goto(url + "#/recette", wait_until="networkidle")
        page.locator(".ri-detail").wait_for()
        page.locator("#rc-indices").scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        page.screenshot(path=str(CAPTURES / "08_indices.png"))
        ecran("#/standards", "09_standards", ".std-gammes")
        ecran("#/apprentissage", "11_apprentissage", ".ap-etapes")
        page.locator("#fa-apprendre").click()
        boite = page.locator(".boite")
        boite.locator("#fa-fichier").set_input_files(str(exemple))
        boite.locator("#fa-analyser").click()
        boite.locator(".fa-conversions").wait_for()
        boite.locator("#fa-apercu").click()
        boite.locator("#fa-apercu-zone > *").first.wait_for()
        page.wait_for_timeout(300)
        boite.screenshot(path=str(CAPTURES / "10_format_appris.png"))
        nav.close()


GABARIT = """<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>{titre}</title><style>
@page {{ size: A4; margin: 18mm 16mm 20mm; }}
body {{ font-family: "Segoe UI", Arial, sans-serif; color: #14243b; font-size: 10.5pt; line-height: 1.45; }}
h1 {{ font-size: 22pt; margin: 0 0 6mm; }} h2 {{ font-size: 15pt; margin: 8mm 0 3mm; page-break-after: avoid; }}
h3 {{ font-size: 12pt; margin: 5mm 0 2mm; page-break-after: avoid; }}
img {{ max-width: 100%; border: 1px solid #c8cfe0; border-radius: 4px; margin: 2mm 0 4mm; page-break-inside: avoid; }}
code {{ font-family: Consolas, monospace; font-size: 9.5pt; background: #eef1fb; padding: 0 2px; }}
li {{ margin: 1mm 0; }} p {{ margin: 2mm 0; }}
.pied {{ margin-top: 10mm; font-size: 8.5pt; color: #5a6680; }}
</style></head><body>{corps}<p class="pied">OGIAS {version} — manuel généré le {date}. Captures prises sur un ouvrage fictif.</p></body></html>"""


def pdf() -> None:
    from markdown_it import MarkdownIt
    from playwright.sync_api import sync_playwright
    sys.path.insert(0, str(RACINE))
    from genvar import VERSION
    texte = SOURCE.read_text(encoding="utf-8")
    corps = MarkdownIt("commonmark").render(texte).replace('src="docs/', f'src="{(RACINE / "docs").as_uri()}/')
    page_html = GABARIT.format(titre="OGIAS — Manuel de l'utilisateur", corps=corps, version=html.escape(VERSION),
                               date=time.strftime("%d/%m/%Y"))
    with tempfile.TemporaryDirectory() as d:
        source = Path(d) / "manuel.html"
        source.write_text(page_html, encoding="utf-8")
        with sync_playwright() as p:
            nav = p.chromium.launch()
            page = nav.new_page()
            page.goto(source.as_uri(), wait_until="load")
            page.pdf(path=str(PDF), format="A4", print_background=True, display_header_footer=True,
                     header_template="<span></span>",
                     footer_template='<div style="font-size:8pt;width:100%;text-align:center;color:#5a6680">'
                                     'OGIAS — Manuel de l\'utilisateur · <span class="pageNumber"></span> / '
                                     '<span class="totalPages"></span></div>',
                     margin={"top": "18mm", "bottom": "20mm", "left": "16mm", "right": "16mm"})
            nav.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sans-pdf", action="store_true", help="captures seulement")
    args = parser.parse_args()
    travail = Path(tempfile.mkdtemp(prefix="ogias-manuel-"))
    srv, url = demarrer_demo(travail)
    try:
        captures(url, travail)
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=10)
        except subprocess.TimeoutExpired:
            srv.kill()
        shutil.rmtree(travail, ignore_errors=True)
    if not args.sans_pdf:
        pdf()
    print(f"Captures : {CAPTURES}\n" + ("" if args.sans_pdf else f"PDF : {PDF}"))


if __name__ == "__main__":
    main()
