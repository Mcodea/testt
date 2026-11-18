"""Audit d'accessibilité de chaque écran (refonte, lot 7b), thèmes clair et sombre.

Usage : python outils/interface_accessibilite.py <url du serveur de démonstration> [sortie.json]
Le serveur vient de outils/interface_demo.py (ouvrage fictif). Trois contrôles, sur ce qui est visible :
- contraste du texte sur son fond réel (WCAG 2.1 AA : 4,5:1, ou 3:1 pour le grand texte) ;
- nom accessible des boutons, liens et champs (texte, aria-label, title, étiquette, placeholder) ;
- atteinte au clavier : un bouton, lien ou champ actif ne doit pas avoir tabindex="-1" hors d'un composant qui gère
  lui-même le focus (lignes de tableau dense, menus).
Le texte désactivé (disabled) est exempté du contraste, comme le permet WCAG.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

from playwright.sync_api import sync_playwright

ECRANS = [("ouvrages", "#/ouvrages"), ("tableau_de_bord", "#/dashboard"), ("equipements", "#/inventaire"),
          ("liste_es", "#/es"), ("materiel", "#/materiel"), ("variables", "#/variables"),
          ("adressage", "#/adressage"), ("recette", "#/recette"), ("referentiel", "#/referentiel")]

AUDIT = r"""() => {
 // rgb(…)/rgba(…) en 0-255 ; color(srgb r g b / a) (issu de color-mix) en 0-1
 const lum = c => { let m = c.match(/[\d.]+/g); if (!m) return null;
   if (c.startsWith('color(')) m = [...m.slice(0, 3).map(v => v * 255), ...m.slice(3)];
   const [r, g, b] = m.slice(0, 3).map(Number)
   .map(v => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; });
   return {l: .2126 * r + .7152 * g + .0722 * b, a: m.length > 3 ? +m[3] : 1, rgb: m.slice(0, 3).map(Number)}; };
 const melange = (dessus, dessous) => dessus.a >= 1 ? dessus : lum(`rgb(${dessus.rgb.map((v, i) => v * dessus.a + dessous.rgb[i] * (1 - dessus.a)).join(',')})`);
 const fond = el => { const pile = []; for (let e = el; e; e = e.parentElement) { const c = lum(getComputedStyle(e).backgroundColor);
     if (c && c.a > 0) { pile.push(c); if (c.a >= 1) break; } }
   let f = lum(getComputedStyle(document.body).backgroundColor) || lum('rgb(255,255,255)');
   for (const c of pile.reverse()) f = melange(c, f); return f; };
 const ratio = (a, b) => (Math.max(a.l, b.l) + .05) / (Math.min(a.l, b.l) + .05);
 const visible = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
   return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && +s.opacity > 0.05
; };   // toute la page, y compris ce qui est hors de la zone visible (défilement)
 const nom = e => (e.getAttribute('aria-label') || e.getAttribute('aria-labelledby') && document.getElementById(e.getAttribute('aria-labelledby'))?.textContent
   || (e.labels && [...e.labels].map(l => l.textContent).join(' ')) || e.getAttribute('title') || e.getAttribute('placeholder')
   || (e.tagName === 'INPUT' && ['button', 'submit'].includes(e.type) ? e.value : '') || e.innerText || e.textContent || '').trim();
 const desc = e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\s+/).slice(0, 2).join('.') : '');
 const contraste = [], sansNom = [], horsClavier = [];
 const vus = new Set();
 for (const e of document.querySelectorAll('body *')) {
  if (!visible(e) || e.closest('[aria-hidden="true"], .o-masque')) continue;
  const texte = [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();
  if (texte && !e.closest(':disabled, [aria-disabled="true"]')) {
   const s = getComputedStyle(e), c = lum(s.color); if (!c) continue;
   const f = fond(e), r = ratio(melange(c, f), f), taille = parseFloat(s.fontSize), gras = +s.fontWeight >= 700;
   const seuil = taille >= 24 || (taille >= 18.66 && gras) ? 3 : 4.5;
   const cle = desc(e) + '|' + s.color + '|' + r.toFixed(2);
   if (r < seuil - 0.01 && !vus.has(cle)) { vus.add(cle); contraste.push({element: desc(e), texte: texte.slice(0, 40), ratio: +r.toFixed(2), seuil}); }
  }
  if (e.matches('button, a[href], [role=button], input:not([type=hidden]), select, textarea') && !nom(e))
   sansNom.push(desc(e));
  if (e.matches('button:not(:disabled), a[href], input:not(:disabled):not([type=hidden]), select:not(:disabled), textarea:not(:disabled)')
      && e.getAttribute('tabindex') === '-1' && !e.closest('table[data-o-pret], .o-menu, [role=menu], [role=tablist]'))
   horsClavier.push(desc(e));
 }
 return {contraste, sans_nom: [...new Set(sansNom)], hors_clavier: [...new Set(horsClavier)]};
}"""


def auditer(url: str) -> dict:
    resultats: dict[str, dict] = {}
    with sync_playwright() as p:
        navigateur = p.chromium.launch()
        for theme in ("clair", "sombre"):
            ctx = navigateur.new_context(viewport={"width": 1600, "height": 900})
            ctx.add_init_script(f"try{{localStorage.setItem('ogias-ui-theme','{'dark' if theme == 'sombre' else 'light'}')}}catch(e){{}}")
            page = ctx.new_page()
            page.goto(url + "#/ouvrages", wait_until="networkidle")
            time.sleep(0.5)
            page.locator("[data-project]").first.click()
            time.sleep(0.8)
            for nom, route in ECRANS:
                page.evaluate(f"location.hash='{route}'")
                page.wait_for_load_state("networkidle")
                time.sleep(0.8)
                resultats[f"{nom}_{theme}"] = page.evaluate(AUDIT)
            ctx.close()
        navigateur.close()
    return resultats


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit(__doc__)
    r = auditer(sys.argv[1].rstrip("/") + "/")
    if len(sys.argv) == 3:
        Path(sys.argv[2]).write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    total = {k: sum(len(v[k]) for v in r.values()) for k in ("contraste", "sans_nom", "hors_clavier")}
    print(json.dumps(total, ensure_ascii=False))
    for ecran, v in r.items():
        for k in ("contraste", "sans_nom", "hors_clavier"):
            for x in v[k][:12]:
                print(f"{ecran:24} {k:12} {x}")
    if any(total.values()):
        raise SystemExit(1)
