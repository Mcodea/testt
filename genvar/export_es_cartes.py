"""Liste des E/S par carte, d'après la trame fournie par l'utilisateur le 16/11/2026 (Trame_ES.xlsx).

Philosophie de la trame :
- une feuille « Architecture » : gamme automate, identité de l'automate, racks dessinés emplacement par
  emplacement (alimentation, processeur, communication, cartes), réserve de chaque carte et réserves globales ;
- une feuille par carte d'E/S (ETOR, STOR, EANA, SANA) : rack, position, nombre de voies, réserve, puis une
  ligne par voie — adresse, sens du contact ou échelle physique, organe, désignation, repère PCF, colonne de
  validation SAT, mnémonique automate.

Règles : rien n'est inventé. Les champs que l'ouvrage ne contient pas (nom et adresses réseau de l'automate)
restent à renseigner, signalés comme tels. Les réserves sont des formules Excel calculées sur les feuilles des
cartes, donc justes après une modification à la main. Les E/S sans voie ou par communication ne sont pas
perdues : elles figurent sur une feuille dédiée.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

NATURE_FEUILLE = {"ET": "ETOR", "ST": "STOR", "EA": "EANA", "SA": "SANA"}
NATURE_LIBELLE = {"ET": "Entrées TOR", "ST": "Sorties TOR", "EA": "Entrées analogiques", "SA": "Sorties analogiques"}
PREFIXE = {"ET": "%I", "ST": "%Q", "EA": "%IW", "SA": "%QW"}
GAMME = {"M340": "Modicon M340", "M580": "Modicon M580", "STB": "Advantys STB", "S4W": "SOFREL S4W"}

# Palette sobre : bleu nuit pour la structure, une teinte claire par nature, jaune pâle pour « à renseigner ».
BLEU_NUIT = "14243B"
GRIS_ENTETE = "E8EEF5"
GRIS_LIGNE = "F6F8FB"
TEINTE = {"ET": "E3F2E8", "ST": "FDEBD8", "EA": "E1ECFA", "SA": "EDE4F7"}
FONCE = {"ET": "1E7A46", "ST": "A84A00", "EA": "1F5FBF", "SA": "6B3FA0"}
TEINTE_ROLE = {"alimentation": "FFF4CC", "processeur": "D9DEE7", "communication": "DCE9F5", "extension": "EEEEEE"}
A_RENSEIGNER = "FFF9DB"

FIN = Side(style="thin", color="9AA5B4")
MOYEN = Side(style="medium", color=BLEU_NUIT)
BORD = Border(left=FIN, right=FIN, top=FIN, bottom=FIN)
BORD_FORT = Border(left=MOYEN, right=MOYEN, top=MOYEN, bottom=MOYEN)
POLICE = "Calibri"


def _f(gras=False, taille=10, couleur="1F2937", italique=False):
    return Font(name=POLICE, bold=gras, size=taille, color=couleur, italic=italique)


def _remplir(c, couleur):
    c.fill = PatternFill("solid", fgColor=couleur)


def _centre(retour=True, rotation=0):
    return Alignment(horizontal="center", vertical="center", wrap_text=retour, text_rotation=rotation)


def _gauche(retour=True):
    return Alignment(horizontal="left", vertical="center", wrap_text=retour)


def _nom_feuille(m):
    return f"{NATURE_FEUILLE[m.nature]}-{m.rack}-{m.position:02d}"


def _place(p):
    """(clé de carte « r.p », voie) d'une E/S placée, sinon (None, None)."""
    from .cartes_es import place
    k, v = place(p)
    return (k, v) if k is not None and v is not None else (None, None)


def _echelle(p):
    a = p.analogique or {}
    if not a:
        return "à définir"
    phys = f"{a['phys_min']:g} – {a['phys_max']:g} {a.get('unite', '')}".strip()
    return f"{phys}\n{a['signal_min']:g}–{a['signal_max']:g} mA"


def _organe(ouvrage, p, eqs, ufs):
    eq = eqs.get(p.ident_eq)
    lieu = ufs.get(p.uf) or (f"UF {p.uf}" if p.uf else ouvrage.libelle)
    nom = (eq.libelle if eq and eq.libelle else "") or (p.organe1.capitalize() if p.organe1 else p.repere)
    return f"{lieu}\n{nom}" if lieu else nom


def _racks(ouvrage):
    """Racks retenus ; à défaut, racks déduits des cartes déclarées (sans alimentation ni processeur connus)."""
    if ouvrage.racks:
        return ouvrage.racks
    par_rack: dict[int, int] = {}
    for m in ouvrage.modules:
        par_rack[m.rack] = max(par_rack.get(m.rack, 0), m.position + 1)
    return [{"numero": r, "reference": "rack non retenu", "positions": n, "cpu": []} for r, n in sorted(par_rack.items())]


def _entete_ouvrage(ws, ouvrage, sous_titre, largeur):
    """Bandeau commun : ouvrage, sous-titre de la feuille, révision et date d'édition."""
    fin = get_column_letter(largeur)
    ws.merge_cells(f"A1:{fin}1")
    c = ws["A1"]
    c.value = f"{ouvrage.prefixe()} — {ouvrage.libelle}".strip(" —")
    c.font = _f(True, 13, "FFFFFF")
    c.alignment = _gauche(False)
    _remplir(c, BLEU_NUIT)
    ws.row_dimensions[1].height = 24
    ws.merge_cells(f"A2:{fin}2")
    c = ws["A2"]
    c.value = f"{sous_titre}    ·    Révision {ouvrage.revision}    ·    édité le {datetime.now():%d/%m/%Y}"
    c.font = _f(False, 9, "526176")
    c.alignment = _gauche(False)


def _mise_en_page(ws, paysage, lignes_titres=None):
    ws.page_setup.orientation = "landscape" if paysage else "portrait"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_options.horizontalCentered = True
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.page_margins.top = ws.page_margins.bottom = 0.5
    if lignes_titres:
        ws.print_title_rows = lignes_titres
    ws.oddFooter.left.text = "&8OGIAS — liste des E/S"
    ws.oddFooter.center.text = "&8&A"
    ws.oddFooter.right.text = "&8Page &P / &N"
    ws.sheet_view.showGridLines = False


# ------------------------------------------------------------------ feuille d'une carte
LIGNE_TITRES, PREMIERE = 6, 7          # ligne des en-têtes du tableau, première voie


def _feuille_carte(wb, ouvrage, m, occupants, eqs, ufs, reserve_min):
    ws = wb.create_sheet(_nom_feuille(m))
    nat, ana = m.nature, m.nature in ("EA", "SA")
    entree = m.nature in ("ET", "EA")
    ws.sheet_properties.tabColor = FONCE[nat]
    largeurs = {"A": 12, "B": 22 if ana else 18, "C": 34, "D": 30, "E": 17, "F": 11, "G": 26, "H": 26, "I": 4}
    for col, w in largeurs.items():
        ws.column_dimensions[col].width = w
    ws.column_dimensions["I"].hidden = True                 # 1 = voie libre (calcul de la réserve)
    _entete_ouvrage(ws, ouvrage, f"{NATURE_LIBELLE[nat]} — carte {m.reference or nat} en {m.rack}.{m.position}", 8)

    # Identité de la carte (philosophie de la trame : rack, position, nombre d'infos, réserve)
    derniere = PREMIERE + m.voies - 1
    etiquettes = [("A", "N° Rack", m.rack), ("B", "N° Position", m.position), ("C", "Référence", m.reference or "à préciser"),
                  ("D", "Nature", NATURE_LIBELLE[nat]), ("E", "Nb d'infos", m.voies),
                  ("F", "Utilisées", f"=COUNTIF(I{PREMIERE}:I{derniere},0)"),
                  ("G", "Réserve", f"=SUM(I{PREMIERE}:I{derniere})/E5")]
    for col, lib, val in etiquettes:
        t, v = ws[f"{col}4"], ws[f"{col}5"]
        t.value, v.value = lib, val
        t.font, t.alignment = _f(True, 9, "526176"), _centre(False)
        v.font, v.alignment, v.border = _f(True, 11), _centre(False), BORD_FORT
        _remplir(v, TEINTE[nat])
    ws["G5"].number_format = "0.0 %"
    ws["H4"].value, ws["H5"].value = "Réserve exigée", reserve_min
    ws["H4"].font, ws["H4"].alignment = _f(True, 9, "526176"), _centre(False)
    ws["H5"].number_format, ws["H5"].alignment, ws["H5"].font = "0 %", _centre(False), _f(False, 11, "526176")
    ws.conditional_formatting.add("G5", CellIsRule(operator="lessThan", formula=["$H$5"],
                                                   fill=PatternFill("solid", fgColor="FDECEA"), font=Font(bold=True, color="B42318")))
    ws.row_dimensions[4].height, ws.row_dimensions[5].height = 16, 22

    # Tableau des voies
    titres = ["ENTRÉE" if entree else "SORTIE", "ÉCHELLE PHYSIQUE" if ana else ("SENS CONTACT" if entree else "SENS COMMANDE"),
              "ORGANE", "DÉSIGNATION", "PCF", "VALIDATION\nSAT", "MNÉMONIQUE API", "OBSERVATIONS SAT", "libre"]
    for i, t in enumerate(titres, start=1):
        c = ws.cell(LIGNE_TITRES, i, t)
        c.font, c.alignment, c.border = _f(True, 9, "FFFFFF"), _centre(), BORD
        _remplir(c, BLEU_NUIT)
    ws.row_dimensions[LIGNE_TITRES].height = 30
    sat = DataValidation(type="list", formula1='"OK,NOK,Non testé"', allow_blank=True,
                         errorTitle="Validation SAT", error="Choisissez OK, NOK ou Non testé.")
    ws.add_data_validation(sat)
    for v in range(m.voies):
        r = PREMIERE + v
        p = occupants.get(v)
        adresse = f"{PREFIXE[nat]}{m.rack}.{m.position}.{v}"
        if p is None:
            valeurs = [adresse, "", "", "Réserve", "", "", "", "", 1]
        else:
            valeurs = [adresse, _echelle(p) if ana else (p.sens or "à définir"), _organe(ouvrage, p, eqs, ufs),
                       p.information or p.designation or p.commentaire, p.repere, "", p.nom, "", 0]
        for i, val in enumerate(valeurs, start=1):
            c = ws.cell(r, i, val)
            c.border = BORD
            c.font = _f(i in (1, 7), 10, "1F2937")
            c.alignment = _centre(False) if i in (1, 5, 6) else _gauche()
        if p is None:
            for i in range(2, 9):
                ws.cell(r, i).font = _f(False, 9, "8A94A3", italique=(i == 4))
            for i in range(1, 9):
                _remplir(ws.cell(r, i), GRIS_LIGNE)
        else:
            if (ana and not p.analogique) or (not ana and not p.sens):
                ws.cell(r, 2).font = _f(False, 10, "A84A00", italique=True)
        ws.cell(r, 7).font = Font(name="Consolas", size=10, bold=True, color="14243B")
        ws.cell(r, 1).font = Font(name="Consolas", size=10, bold=True, color=FONCE[nat])
        ws.cell(r, 5).font = Font(name="Consolas", size=10, color="1F2937")
        ws.row_dimensions[r].height = 30 if p is not None else 16
    sat.add(f"F{PREMIERE}:F{derniere}")
    ws.conditional_formatting.add(f"F{PREMIERE}:F{derniere}", FormulaRule(
        formula=[f'F{PREMIERE}="OK"'], fill=PatternFill("solid", fgColor="E3F4EC"), font=Font(bold=True, color="0B7A4B")))
    ws.conditional_formatting.add(f"F{PREMIERE}:F{derniere}", FormulaRule(
        formula=[f'F{PREMIERE}="NOK"'], fill=PatternFill("solid", fgColor="FDECEA"), font=Font(bold=True, color="B42318")))
    ws.freeze_panes = f"A{PREMIERE}"
    ws.auto_filter.ref = f"A{LIGNE_TITRES}:H{derniere}"
    ws["H3"].value = "← Architecture"
    ws["H3"].hyperlink = "#'Architecture'!A1"
    ws["H3"].font = Font(name=POLICE, size=9, color="1F5FBF", underline="single")
    ws["H3"].alignment = Alignment(horizontal="right")
    _mise_en_page(ws, paysage=True, lignes_titres=f"{LIGNE_TITRES}:{LIGNE_TITRES}")
    return ws


# ------------------------------------------------------------------ feuille Architecture
def _feuille_architecture(ws, ouvrage, racks, cartes, feuilles, plateforme, reserve_min):
    ws.title = "Architecture"
    ws.sheet_properties.tabColor = BLEU_NUIT
    max_pos = max([int(r.get("positions", 0)) for r in racks] + [12])
    largeur = 3 + max_pos
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 10                     # PS
    for i in range(max_pos):
        ws.column_dimensions[get_column_letter(4 + i)].width = 10
    _entete_ouvrage(ws, ouvrage, "Architecture automate et réserves", largeur)

    ws["B4"].value = f"Gamme automate : {GAMME.get(plateforme, plateforme or 'à préciser')}"
    ws["B4"].font = _f(True, 14, BLEU_NUIT)
    lignes = [("Source d'acquisition", ouvrage.automate or "à renseigner dans la fiche ouvrage", bool(ouvrage.automate)),
              ("Nom automate", "", False), ("Adresse réseau automate", "", False),
              ("Masque de sous-réseau", "", False), ("Adresse passerelle (gateway)", "", False),
              ("Protocoles", ouvrage.communication or "", bool(ouvrage.communication))]
    for k, (lib, val, connu) in enumerate(lignes):
        r = 6 + k
        ws.cell(r, 2, lib).font = _f(True, 10, "526176")
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=7)
        c = ws.cell(r, 3, val if connu else (val or "à renseigner"))
        c.font = _f(connu, 10, "1F2937" if connu else "A84A00", italique=not connu)
        c.alignment = _gauche(False)
        for col in range(3, 8):
            ws.cell(r, col).border = BORD
            if not connu:
                _remplir(ws.cell(r, col), A_RENSEIGNER)

    r0 = 14
    par_cle = {f"{m.rack}.{m.position}": m for m in cartes}
    for rack in racks:
        n, positions = int(rack.get("numero", 0)), int(rack.get("positions", 0))
        occ = {int(o["position"]): o for o in rack.get("occupation", []) if "position" in o}
        cpu = set(rack.get("cpu", []))
        ws.cell(r0, 2, f"Rack {n}").font = _f(True, 12, BLEU_NUIT)
        ws.merge_cells(start_row=r0, start_column=3, end_row=r0, end_column=3 + positions)
        ws.cell(r0, 3, f"{rack.get('reference', '')} · {positions} emplacements").font = _f(False, 10, "526176")
        r_res, r_pos, r_mod, r_nat = r0 + 1, r0 + 2, r0 + 3, r0 + 4
        ws.cell(r_res, 2, "Réserve de la carte").font = _f(False, 9, "526176")
        ws.cell(r_pos, 2, "Emplacement").font = _f(True, 9, "526176")
        ws.cell(r_mod, 2, "Module").font = _f(True, 9, "526176")
        ws.cell(r_mod, 2).alignment = _gauche(False)
        ws.cell(r_nat, 2, "Rôle").font = _f(False, 9, "526176")
        ws.row_dimensions[r_mod].height = 118
        # Alimentation (emplacement CPS, hors numérotation)
        alim = rack.get("alimentation") or ""
        _case(ws, r_pos, r_mod, r_nat, 3, "PS", alim if alim and "choisir" not in alim else "à choisir",
              "alimentation", TEINTE_ROLE["alimentation"])
        pos = 0
        while pos < positions:
            col = 4 + pos
            o = occ.get(pos)
            if o and o.get("role") == "processeur" and occ.get(pos + 1, {}).get("reference") == o["reference"] \
                    and occ[pos + 1].get("role") == "processeur":
                # Processeur M580 double largeur : un seul module sur deux emplacements (00-01)
                _case(ws, r_pos, r_mod, r_nat, col, f"{pos}–{pos + 1}", o["reference"], "processeur",
                      TEINTE_ROLE["processeur"], double=True)
                pos += 2
                continue
            if o:
                _case(ws, r_pos, r_mod, r_nat, col, str(pos), o["reference"], o.get("role", ""),
                      TEINTE_ROLE.get(o.get("role", ""), "FFFFFF"))
            elif pos in cpu:
                _case(ws, r_pos, r_mod, r_nat, col, str(pos), "processeur", "processeur", TEINTE_ROLE["processeur"])
            elif f"{n}.{pos}" in par_cle:
                m = par_cle[f"{n}.{pos}"]
                c = _case(ws, r_pos, r_mod, r_nat, col, str(pos), m.reference or NATURE_FEUILLE[m.nature],
                          NATURE_FEUILLE[m.nature], TEINTE[m.nature], couleur_texte=FONCE[m.nature])
                c.hyperlink = f"#'{feuilles[m.cle]}'!A1"
                res = ws.cell(r_res, col, f"='{feuilles[m.cle]}'!G5")
                res.number_format, res.alignment, res.font = "0 %", _centre(False), _f(True, 9, "1F2937")
                ws.conditional_formatting.add(res.coordinate, CellIsRule(
                    operator="lessThan", formula=[str(reserve_min)], font=Font(bold=True, color="B42318")))
            else:
                _case(ws, r_pos, r_mod, r_nat, col, str(pos), "libre", "", "FFFFFF", couleur_texte="9AA5B4")
            pos += 1
        r0 += 7

    # Réserves globales par nature (formules sur les feuilles des cartes : justes après une retouche à la main)
    ws.cell(r0, 2, "Réserves globales").font = _f(True, 12, BLEU_NUIT)
    entetes = ["Nature", "Cartes", "Voies", "Utilisées", "Libres", "Réserve"]
    for i, t in enumerate(entetes):
        c = ws.cell(r0 + 1, 2 + i, t)
        c.font, c.alignment, c.border = _f(True, 9, "FFFFFF"), _centre(False), BORD
        _remplir(c, BLEU_NUIT)
    for k, nat in enumerate(("ET", "ST", "EA", "SA")):
        r = r0 + 2 + k
        noms = [feuilles[m.cle] for m in cartes if m.nature == nat]
        somme = (lambda cel: "=" + "+".join(f"'{s}'!{cel}" for s in noms)) if noms else None
        valeurs = [f"{NATURE_FEUILLE[nat]} — {NATURE_LIBELLE[nat]}", len(noms),
                   somme("E5") if somme else 0, somme("F5") if somme else 0,
                   f"={get_column_letter(4)}{r}-{get_column_letter(5)}{r}" if noms else 0,
                   f"=IF({get_column_letter(4)}{r}=0,\"NC\",{get_column_letter(6)}{r}/{get_column_letter(4)}{r})" if noms else "NC"]
        for i, val in enumerate(valeurs):
            c = ws.cell(r, 2 + i, val)
            c.border, c.font = BORD, _f(i in (0, 5), 10, FONCE[nat] if i == 0 else "1F2937")
            c.alignment = _gauche(False) if i == 0 else _centre(False)
            if i == 0:
                _remplir(c, TEINTE[nat])
        ws.cell(r, 7).number_format = "0.0 %"
        ws.conditional_formatting.add(f"G{r}", CellIsRule(operator="lessThan", formula=[str(reserve_min)],
                                                          fill=PatternFill("solid", fgColor="FDECEA"), font=Font(bold=True, color="B42318")))
    ws.merge_cells(start_row=r0 + 6, start_column=2, end_row=r0 + 6, end_column=8)
    note = ws.cell(r0 + 6, 2, f"Réserve exigée par carte : {reserve_min:.0%}. Une réserve inférieure apparaît en rouge. "
                              "Cliquez une carte du rack pour ouvrir sa feuille.")
    note.font, note.alignment = _f(False, 9, "526176", italique=True), _gauche()
    ws.row_dimensions[r0 + 6].height = 28
    _mise_en_page(ws, paysage=True)


def _case(ws, r_pos, r_mod, r_nat, col, pos, texte, role, teinte, double=False, couleur_texte="1F2937"):
    fin = col + 1 if double else col
    if double:
        for r in (r_pos, r_mod, r_nat):
            ws.merge_cells(start_row=r, start_column=col, end_row=r, end_column=fin)
    p = ws.cell(r_pos, col, pos)
    p.font, p.alignment = _f(True, 9, "FFFFFF"), _centre(False)
    m = ws.cell(r_mod, col, texte)
    m.font, m.alignment = _f(True, 10, couleur_texte), _centre(True, rotation=90)
    n = ws.cell(r_nat, col, role)
    n.font, n.alignment = _f(False, 8, "526176"), _centre(False)
    for c in range(col, fin + 1):
        _remplir(ws.cell(r_pos, c), BLEU_NUIT)
        _remplir(ws.cell(r_mod, c), teinte)
        for r in (r_pos, r_mod):
            ws.cell(r, c).border = BORD_FORT if r == r_mod else BORD
    return m


# ------------------------------------------------------------------ E/S hors cartes
def _feuille_hors_cartes(wb, ouvrage, points, eqs, ufs):
    ws = wb.create_sheet("Hors cartes")
    ws.sheet_properties.tabColor = "9AA5B4"
    for col, w in {"A": 18, "B": 8, "C": 34, "D": 30, "E": 26, "F": 34}.items():
        ws.column_dimensions[col].width = w
    _entete_ouvrage(ws, ouvrage, "E/S sans voie sur une carte (à implanter) ou raccordées par communication", 6)
    titres = ["PCF", "POINT", "ORGANE", "DÉSIGNATION", "MNÉMONIQUE API", "SITUATION"]
    for i, t in enumerate(titres, start=1):
        c = ws.cell(4, i, t)
        c.font, c.alignment, c.border = _f(True, 9, "FFFFFF"), _centre(), BORD
        _remplir(c, BLEU_NUIT)
    r = 5
    for p in points:
        situation = "Par communication (pas de voie)" if p.raccordement == "Communication" else "Sans voie : à implanter à l'étape Matériel"
        for i, val in enumerate([p.repere, p.point, _organe(ouvrage, p, eqs, ufs),
                                 p.information or p.designation or p.commentaire, p.nom, situation], start=1):
            c = ws.cell(r, i, val)
            c.border, c.alignment, c.font = BORD, _gauche(), _f(False, 10)
        ws.row_dimensions[r].height = 30
        r += 1
    if r == 5:
        ws.cell(5, 1, "Toutes les E/S câblées sont placées sur une carte.").font = _f(False, 10, "0B7A4B", italique=True)
    ws.freeze_panes = "A5"
    _mise_en_page(ws, paysage=True, lignes_titres="4:4")


# ------------------------------------------------------------------ point d'entrée
def exporter(chemin, ouvrage, points, plateforme=""):
    """Écrit le classeur et renvoie le chemin."""
    eqs = {e.ident: e for e in ouvrage.equipements}
    ufs = {u.code: u.libelle for u in ouvrage.unites}
    cartes = sorted(ouvrage.modules, key=lambda m: (m.rack, m.position))
    occupants: dict[str, dict[int, object]] = defaultdict(dict)
    hors = []
    for p in points:
        k, v = _place(p)
        if p.raccordement == "Communication" or k is None:
            hors.append(p)
        else:
            occupants[k][int(v)] = p
    wb = Workbook()
    feuilles = {m.cle: _nom_feuille(m) for m in cartes}
    _feuille_architecture(wb.active, ouvrage, _racks(ouvrage), cartes, feuilles, plateforme, ouvrage.reserve_min)
    for m in cartes:
        _feuille_carte(wb, ouvrage, m, occupants.get(m.cle, {}), eqs, ufs, ouvrage.reserve_min)
    _feuille_hors_cartes(wb, ouvrage, hors, eqs, ufs)
    wb.properties.title = f"Liste des E/S — {ouvrage.prefixe()}"
    wb.properties.creator = "OGIAS"
    wb.save(chemin)
    return chemin
