"""Table de télétransmission au format d'études (échanges avec les autres entreprises), d'après la trame fournie
par l'utilisateur le 16/11/2026 : Repère, UF, Sous-ensemble, Équipement, Information, Famille, Nom de variable,
Type, Adresse, Adresse validée, Registre Modbus, Unité, Alarme, Priorité, Commentaire automate, Libellé Topkapi.

Rien n'est inventé : une adresse seulement proposée est marquée « proposée » ; le registre Modbus n'est donné que
si la convention protocolaire est déclarée (registre = mot %MW + décalage), sinon « convention à déclarer » ;
la priorité d'alarme, absente de l'ouvrage, est une liste à remplir (P1 / P2 / P3).
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

BLEU_NUIT = "14243B"
BANDE = "F6F8FB"
FIN = Side(style="thin", color="9AA5B4")
BORD = Border(left=FIN, right=FIN, top=FIN, bottom=FIN)
POLICE = "Calibri"
FAMILLES = {"TS": "Télésignalisation", "TM": "Télémesure", "TC": "Télécommande", "TR": "Téléréglage",
            "RTR": "Retour de téléréglage", "CP": "Comptage"}
TEINTE_FAMILLE = {"TS": "E3F2E8", "TM": "E1ECFA", "TC": "FDEBD8", "TR": "EDE4F7", "RTR": "EDE4F7", "CP": "FFF4CC"}

COLONNES = [("Repère", 16), ("UF", 7), ("Sous-ensemble", 9), ("Équipement", 20), ("Information", 30),
            ("Famille", 8), ("Nom de variable", 24), ("Type", 7), ("Adresse", 12), ("Adresse validée", 10),
            ("Registre Modbus", 11), ("Unité", 8), ("Alarme", 8), ("Priorité", 9), ("Commentaire automate", 42),
            ("Libellé Topkapi", 34)]


def _f(gras=False, taille=10, couleur="1F2937", italique=False, police=POLICE):
    return Font(name=police, bold=gras, size=taille, color=couleur, italic=italique)


def _remplir(c, couleur):
    c.fill = PatternFill("solid", fgColor=couleur)


def lignes(session):
    """Lignes de la table, dans l'ordre de l'ouvrage (équipement puis famille puis adresse)."""
    o = session.ouvrage
    plan = session.plan_adressage()
    auto = {(a.ident_eq, a.cle): a for a in plan.affectations if a.niveau == "automate"}
    tele = {(a.ident_eq, a.cle): a for a in plan.affectations if a.niveau == "teletransmission"}
    eqs = {e.ident: e for e in o.equipements}
    rang = {e.ident: i for i, e in enumerate(session.equipements_tries())}
    ordre = list(FAMILLES)
    sortie = []
    for v in sorted(session.variables(), key=lambda v: (rang.get(v.ident_eq, 0),
                                                       ordre.index(v.famille) if v.famille in ordre else 99, v.nom)):
        a, t = auto.get((v.ident_eq, v.cle)), tele.get((v.ident_eq, v.cle))
        adresse = v.adresse or (a.proposee if a else "")
        etat = "Oui" if v.adresse and v.adresse_validee else ("Appliquée" if v.adresse else ("Proposée" if adresse else "Non"))
        registre = (t.actuelle or t.proposee) if t and (t.actuelle or t.proposee) else (
            "convention à déclarer" if adresse and not o.protocole_declare else "")
        eq = eqs.get(v.ident_eq)
        sortie.append({"repere": v.repere, "uf": v.uf, "se": eq.sous_ensemble if eq else "",
                       "equipement": v.designation, "information": v.information, "famille": v.famille,
                       "nom": v.nom, "type": v.type_logique, "adresse": adresse, "validee": etat,
                       "registre": registre, "unite": v.unite, "alarme": "Oui" if v.alarme else "",
                       "priorite": "", "commentaire": v.commentaire, "libelle": v.libelle_topkapi})
    return sortie


def exporter(chemin, session):
    o = session.ouvrage
    donnees = lignes(session)
    wb = Workbook()
    ws = wb.active
    ws.title = "Télétransmission"
    n = len(COLONNES)
    fin = get_column_letter(n)
    ws.merge_cells(f"A1:{fin}1")
    ws["A1"].value = f"{o.prefixe()} — {o.libelle}".strip(" —")
    ws["A1"].font, ws["A1"].alignment = _f(True, 13, "FFFFFF"), Alignment(vertical="center")
    _remplir(ws["A1"], BLEU_NUIT)
    ws.row_dimensions[1].height = 24
    ws.merge_cells(f"A2:{fin}2")
    ws["A2"].value = (f"Table de télétransmission — format d'études    ·    Révision {o.revision}    ·    "
                      f"édité le {datetime.now():%d/%m/%Y}    ·    {len(donnees)} variable(s)")
    ws["A2"].font = _f(False, 9, "526176")
    ws.merge_cells(f"A3:{fin}3")
    ws["A3"].value = ("Adresse validée : Oui = validée et protégée · Appliquée = posée, à valider · Proposée = calculée, "
                      "non appliquée. Registre Modbus : selon la convention déclarée dans OGIAS. Priorité : à renseigner.")
    ws["A3"].font = _f(False, 9, "526176", italique=True)
    entete = 5
    for i, (titre, largeur) in enumerate(COLONNES, start=1):
        c = ws.cell(entete, i, titre)
        c.font, c.border = _f(True, 9, "FFFFFF"), BORD
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        _remplir(c, BLEU_NUIT)
        ws.column_dimensions[get_column_letter(i)].width = largeur
    ws.row_dimensions[entete].height = 30
    cles = ["repere", "uf", "se", "equipement", "information", "famille", "nom", "type", "adresse", "validee",
            "registre", "unite", "alarme", "priorite", "commentaire", "libelle"]
    mono = {"repere", "nom", "adresse", "registre"}
    centre = {"uf", "se", "famille", "type", "adresse", "validee", "registre", "unite", "alarme", "priorite"}
    precedent, bande = None, False
    for k, d in enumerate(donnees):
        r = entete + 1 + k
        if d["repere"] != precedent:                  # une bande de fond par équipement : lecture par blocs
            bande, precedent = not bande, d["repere"]
        for i, cle in enumerate(cles, start=1):
            c = ws.cell(r, i, d[cle])
            c.border = BORD
            c.font = _f(cle in ("nom",), 10, "1F2937", police="Consolas" if cle in mono else POLICE)
            c.alignment = Alignment(horizontal="center" if cle in centre else "left", vertical="center",
                                    wrap_text=cle in ("information", "commentaire", "libelle", "equipement"))
            if bande:
                _remplir(c, BANDE)
        fam = ws.cell(r, 6)
        _remplir(fam, TEINTE_FAMILLE.get(d["famille"], "FFFFFF"))
        fam.font = _f(True, 10)
        if d["validee"] != "Oui":
            ws.cell(r, 10).font = _f(True, 10, "A84A00")
        if d["registre"] == "convention à déclarer":
            ws.cell(r, 11).font = _f(False, 9, "A84A00", italique=True)
    derniere = entete + max(len(donnees), 1)
    prio = DataValidation(type="list", formula1='"P1,P2,P3"', allow_blank=True,
                          errorTitle="Priorité d'alarme", error="Choisissez P1, P2 ou P3.")
    ws.add_data_validation(prio)
    prio.add(f"N{entete + 1}:N{derniere}")
    # Alarme sans priorité : signalée pour être complétée
    ws.conditional_formatting.add(f"N{entete + 1}:N{derniere}", FormulaRule(
        formula=[f'AND($M{entete + 1}="Oui",$N{entete + 1}="")'], fill=PatternFill("solid", fgColor="FFF1E0")))
    ws.conditional_formatting.add(f"M{entete + 1}:M{derniere}", FormulaRule(
        formula=[f'$M{entete + 1}="Oui"'], font=Font(bold=True, color="B42318")))
    ws.freeze_panes = ws.cell(entete + 1, 2)
    ws.auto_filter.ref = f"A{entete}:{fin}{derniere}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = f"{entete}:{entete}"
    ws.oddFooter.left.text = "&8OGIAS — table de télétransmission"
    ws.oddFooter.right.text = "&8Page &P / &N"
    ws.sheet_view.showGridLines = False

    # Synthèse : volumes par famille et état des adresses
    sy = wb.create_sheet("Synthèse")
    sy.sheet_view.showGridLines = False
    sy.column_dimensions["A"].width, sy.column_dimensions["B"].width = 30, 14
    sy["A1"].value = f"Synthèse — {o.prefixe()}"
    sy["A1"].font = _f(True, 13, BLEU_NUIT)
    par_fam, par_etat = Counter(d["famille"] for d in donnees), Counter(d["validee"] for d in donnees)
    r = 3
    for titre, compte, libelles in (("Variables par famille", par_fam, FAMILLES),
                                    ("Adresses", par_etat, {"Oui": "Validées", "Appliquée": "Appliquées, à valider",
                                                            "Proposée": "Proposées", "Non": "Sans adresse"})):
        sy.cell(r, 1, titre).font = _f(True, 11, BLEU_NUIT)
        r += 1
        for cle, lib in libelles.items():
            if compte.get(cle):
                sy.cell(r, 1, f"{cle} — {lib}" if titre.startswith("Variables") else lib).border = BORD
                c = sy.cell(r, 2, compte[cle])
                c.border, c.alignment = BORD, Alignment(horizontal="center")
                r += 1
        r += 1
    sy.cell(r, 1, "Alarmes").font = _f(True, 11, BLEU_NUIT)
    sy.cell(r + 1, 1, "Variables en alarme").border = BORD
    c = sy.cell(r + 1, 2, sum(1 for d in donnees if d["alarme"]))
    c.border, c.alignment = BORD, Alignment(horizontal="center")
    wb.properties.title = f"Table de télétransmission — {o.prefixe()}"
    wb.properties.creator = "OGIAS"
    wb.save(chemin)
    return chemin
