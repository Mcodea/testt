"""Livrables de la liste des E/S d'un projet neuf : Excel (travail) et HTML (base du PDF de diffusion).

La liste est un livrable indépendant des variables de supervision : elle sert aux schémas électriques,
au choix des modules et aux études d'automatisme. Les données manquantes sont signalées, jamais inventées.
"""
import html
from collections import Counter
from datetime import datetime

from .export_xlsx import ecrire_xlsx

ORDRE_POINTS = ("ET", "ST", "EA", "SA")


def statut(p):
    if p.raccordement == "Communication":
        return "Validée (communication)" if p.validee else "À valider (communication)"
    if p.validee and p.adresse:
        return "Validée"
    if p.validee:
        return "Validée, adresse à saisir"
    return "À valider"


def description_analogique(p):
    a = p.analogique or {}
    if not a or p.point not in ('EA', 'SA'):
        return ''
    return f"{a['signal_min']:g}–{a['signal_max']:g} mA → {a['phys_min']:g}–{a['phys_max']:g} {a['unite']}"


def description_brute(p):
    a = p.analogique or {}
    if 'brut_min' not in a or 'brut_max' not in a:
        return ''
    return f"{a['brut_min']:g}–{a['brut_max']:g} (comptes module)"


def description_impulsions(p):
    i = p.impulsion or {}
    if not i:
        return ''
    return f"{i['poids']:g} {i['unite']}/imp., front {i['front']}"


def lignes(ouvrage, points):
    libelles_uf = {u.code: u.libelle for u in ouvrage.unites}
    rang = {e.ident: i for i, e in enumerate(ouvrage.equipements)}
    pts = sorted(points, key=lambda p: (p.uf or "~", rang.get(p.ident_eq, 0), ORDRE_POINTS.index(p.point), p.nom))
    return [[p.repere, (f"{p.uf} {libelles_uf.get(p.uf, '')}".strip() if p.uf else "Commun"), p.point, p.nom,
             p.commentaire, p.type_logique, p.raccordement, p.module, p.voie, p.adresse or "", statut(p),
             p.variable or "(locale)", p.origine, description_analogique(p), description_brute(p),
             description_impulsions(p), p.note] for p in pts]


ENTETES = ["Repère", "UF", "Point", "Nom de l'E/S", "Désignation", "Type", "Raccordement", "Module", "Voie",
           "Adresse physique", "Statut", "Variable liée", "Origine", "Échelle analogique",
           "Brut automate", "Paramètres impulsions", "Commentaire"]


def bilan(points):
    cables = [p for p in points if p.raccordement != "Communication"]
    c = Counter(p.point for p in cables)
    modules = Counter((p.module, p.point) for p in cables if p.module)
    return c, modules, len(points) - len(cables)


def exporter_liste_es(chemin, ouvrage, points):
    c, modules, com = bilan(points)
    b_lig = [[pt, c.get(pt, 0)] for pt in ORDRE_POINTS] + [["Par communication (sans voie)", com],
             ["Total", len(points)]]
    b_lig += [[f"Module {m} ({pt})", n] for (m, pt), n in sorted(modules.items())]
    manques = [[p.repere, p.nom, ", ".join(x for x, ok in (("adresse physique", p.adresse or p.raccordement == "Communication"),
                                                          ("validation", p.validee)) if not ok)]
               for p in points if not p.validee or (not p.adresse and p.raccordement != "Communication")]
    ecrire_xlsx(chemin, [
        ("Liste des E/S", ENTETES, lignes(ouvrage, points), [16, 18, 7, 28, 40, 8, 13, 8, 6, 14, 22, 26, 14, 37, 26, 35, 42]),
        ("Bilan matériel", ["Rubrique", "Nombre"], b_lig, [34, 10]),
        ("À compléter", ["Repère", "E/S", "Manque"], manques, [16, 28, 40]),
        ("Ouvrage", ["Rubrique", "Valeur"], [["Ouvrage", f"{ouvrage.prefixe()} {ouvrage.libelle}"],
                                             ["Automate", ouvrage.automate], ["Révision", ouvrage.revision],
                                             ["Statut", "Document de travail — vérifier avant diffusion"]], [20, 50]),
    ])
    return len(points)


def html_liste_es(ouvrage, points, date=None):
    """Document HTML autonome (imprimé en PDF par l'interface)."""
    e = html.escape
    c, modules, com = bilan(points)
    date = date or datetime.now().strftime("%d/%m/%Y")
    manques = sum(1 for p in points if not p.validee or (not p.adresse and p.raccordement != "Communication"))
    # Regrouper les métadonnées utiles dans une seule colonne pour conserver un PDF lisible.
    corps = "".join(
        "<tr>" + "".join(f"<td>{e(str(v))}</td>" for v in l[:11])
        + f"<td>{e(' ; '.join(str(v) for v in l[13:16] if v))}</td><td>{e(str(l[16]))}</td></tr>"
        for l in lignes(ouvrage, points))
    bilan_txt = " · ".join(f"{pt} : {c.get(pt, 0)}" for pt in ORDRE_POINTS) + f" · communication : {com}"
    return f"""<html><head><meta charset="utf-8"><style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 8pt; color: #0F172A; }}
h1 {{ font-size: 14pt; margin: 0; }} .sous {{ color: #475569; margin: 2px 0 10px 0; }}
table {{ border-collapse: collapse; width: 100%; }}
th {{ background: #EEF2F6; text-align: left; padding: 3px 4px; border-bottom: 1px solid #94A3B8; }}
td {{ padding: 2px 4px; border-bottom: 1px solid #E2E8F0; }}
.alerte {{ color: #B45309; }}
</style></head><body>
<h1>Liste des entrées / sorties — {e(ouvrage.prefixe())} {e(ouvrage.libelle)}</h1>
<p class="sous">Automate {e(ouvrage.automate)} · révision {e(ouvrage.revision)} · {e(date)} · {len(points)} E/S ({e(bilan_txt)})</p>
{f'<p class="alerte">{manques} E/S restent à valider ou à adresser : document de travail.</p>' if manques else ''}
<table><tr>{''.join(f'<th>{e(t)}</th>' for t in ENTETES[:11] + ['Configuration analogique / impulsions', 'Commentaire'])}</tr>{corps}</table>
</body></html>"""
