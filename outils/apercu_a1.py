"""Génère l'aperçu des renommages et des ajouts du rapport V1 (décision A1), à approuver par l'utilisateur.

    py outils/apercu_a1.py             # écrit docs/APERCU_A1_A_APPROUVER.md et .xlsx
    py outils/apercu_a1.py --verifier  # échoue si les fichiers ne correspondent plus aux sources

Lecture seule : rien n'est appliqué au référentiel ni à un ouvrage. Sources : le catalogue livré
(`genvar/data/catalogue_defaut.json`), la bibliothèque V1 (`docs/referentiel/OGIAS_V031_bibliotheque_ES_physiques.xlsx`)
et la correspondance déterministe (`validation/referentiel/correspondance_es_v1.csv`, `outils/correspondance_es_v1.py`).
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
from genvar.modele import suffixe_physique  # noqa: E402

MD = RACINE / "docs" / "APERCU_A1_A_APPROUVER.md"
XLSX = RACINE / "docs" / "APERCU_A1_A_APPROUVER.xlsx"
DECISIONS = "Approuvé,Refusé,À discuter"


def _donnees():
    catalogue = json.loads((RACINE / "genvar/data/catalogue_defaut.json").read_text(encoding="utf-8"))
    signaux = {(s["type"], s["es"], s["code"]): s for s in catalogue["signaux"]}
    types = {t["code"]: t for t in catalogue["types"]}
    classeur = load_workbook(RACINE / "docs/referentiel/OGIAS_V031_bibliotheque_ES_physiques.xlsx", read_only=True, data_only=True)
    try:
        lignes = list(classeur["Bibliothèque E-S"].values)
    finally:
        classeur.close()
    bibliotheque = {x["Identifiant"]: x for x in (dict(zip(lignes[0], l)) for l in lignes[1:] if l[0])}
    with open(RACINE / "validation/referentiel/correspondance_es_v1.csv", encoding="utf-8") as f:
        correspondance = list(csv.DictReader(f, delimiter=";"))
    return catalogue, signaux, types, bibliotheque, correspondance


def _repere(nom_exemple: str) -> str:
    """« ET_SR02AB01_NIV_B » → « SR02AB01 » (repère de l'exemple de la bibliothèque)."""
    morceaux = (nom_exemple or "").split("_")
    return morceaux[1] if len(morceaux) > 2 else "…"


def _tele(code: str, repere: str) -> str:
    """« TS_NIV_B » + repère → « TS_SR02AB01_NIV_B » ; vide si la bibliothèque ne donne pas d'information associée."""
    if not code:
        return ""
    if "_" not in code:
        return "information produite par les règles du type"
    famille, reste = code.split("_", 1)
    return f"{famille}_{repere}_{reste}"


def calculer():
    catalogue, signaux, types, bibliotheque, correspondance = _donnees()
    renommages, ajouts, inchanges, particuliers = [], [], 0, []
    for c in correspondance:
        if c["Évolution"] == "Inchangé":
            inchanges += 1
            continue
        x = bibliotheque.get(c["Identifiant V1"])
        if not x:
            continue
        if c["Évolution"] == "Harmonisé":
            s = signaux.get((c["Type"], c["Nature"], c["Code catalogue"]))
            if not s:
                particuliers.append(f"{c['Identifiant V1']} : type {c['Type']} supprimé du catalogue (consolidé dans FT, décision de la V2) ; "
                                    f"l'E/S correspond à la nouvelle `FT.ES_IMP` (décision R1 sur le repère, déjà documentée dans docs/RAPPORT_ECARTS_V2.md).")
                continue
            rep = _repere(x["Nom généré (exemple)"])
            renommages.append({
                "type": c["Type"], "nature": c["Nature"], "equipement": x["Équipement"], "libelle": x["Libellé standard"],
                "variante": x["Variante / option"] or "Base",
                "code_actuel": c["Code catalogue"], "code_propose": c["Code V1"],
                "physique_actuel": f"{c['Nature']}_{rep}_{suffixe_physique(s)}", "physique_propose": x["Nom généré (exemple)"],
                "tele_actuel": f"{s['famille']}_{rep}_{s['code']}", "tele_propose": _tele(x["Télétransmission"], rep),
                "rapprochement": c["Rapprochement"]})
        elif c["Évolution"] == "Ajouté":
            ajouts.append({
                "id": c["Identifiant V1"], "type": c["Type"], "equipement": x["Équipement"], "nature": c["Nature"], "code": c["Code V1"],
                "libelle": x["Libellé standard"], "precision": x["Précision"] or "", "variante": x["Variante / option"] or "Base",
                "presence": x["Présence"] or "", "physique": x["Nom généré (exemple)"], "tele": x["Télétransmission"] or "",
                "type_nouveau": c["Type"] not in types})
    signaux_connus = {(c["Type"], c["Nature"], c["Code catalogue"]) for c in correspondance if c["Code catalogue"]}
    for c in correspondance:
        if not c["Évolution"] and c["Code catalogue"]:
            particuliers.append(f"Signal du catalogue `{c['Type']}.{c['Code catalogue']}` (index {c['Index catalogue']}) absent de la bibliothèque V1 : "
                                "conservé tel quel, aucune décision à prendre.")
    del signaux_connus
    renommages.sort(key=lambda r: (r["type"], r["nature"], r["code_actuel"]))
    ajouts.sort(key=lambda r: (r["type"], r["nature"], r["code"]))
    return {"renommages": renommages, "ajouts": ajouts, "inchanges": inchanges, "types": types, "particuliers": particuliers}


def _md(d) -> str:
    ren, aj = d["renommages"], d["ajouts"]
    nouveaux = sorted({a["type"] for a in aj if a["type_nouveau"]})
    par_type_ren = Counter(r["type"] for r in ren)
    par_type_aj = Counter(a["type"] for a in aj)
    l = ["# Aperçu A1 : renommages et ajouts à approuver", "",
         "Document généré par `outils/apercu_a1.py` (ne pas modifier à la main). **Rien n'est appliqué** : ni le référentiel livré, "
         "ni aucun ouvrage. Les ouvrages existants gardent leur référentiel figé quoi que vous décidiez ; ils n'adoptent une "
         "révision que par l'action volontaire « Examiner et appliquer… », ligne à ligne, avec sauvegarde.", "",
         "## 1. En bref", "",
         f"- **{len(ren)} renommages** de codes d'E/S physiques existantes (le rapport du 10/11 en annonçait 54 : le recalcul "
         f"sur le catalogue actuel en trouve {len(ren)} ; l'écart est à valider avec vous).",
         f"- **{len(aj)} ajouts** d'E/S absentes du catalogue, dont **{len([1 for a in aj if a['type_nouveau']])}** dans "
         f"{len(nouveaux)} types à créer ({', '.join(nouveaux)}).",
         f"- {d['inchanges']} E/S restent inchangées (aucune décision).", "",
         "**Comment répondre.** Dans le classeur `docs/APERCU_A1_A_APPROUVER.xlsx`, choisissez « Approuvé », « Refusé » ou "
         "« À discuter » à chaque ligne (une liste déroulante est prévue), ou dites simplement ici « tout approuvé », "
         "« renommages approuvés, ajouts refusés », ou « approuvé sauf le type X ». Je prépare alors un **brouillon** de "
         "référentiel avec les seules lignes approuvées, avec correspondances d'adresses, contrôles et tests : il ne sera "
         "publié qu'après votre dernier accord.", "",
         "## 2. Ce que change un renommage", "",
         "Le nom d'une E/S physique se construit `NATURE_repère_suffixe` ; l'information de télétransmission "
         "`FAMILLE_repère_code`. Un renommage change le code, donc ces noms, **pour les nouveaux ouvrages seulement**. "
         "Pour un ouvrage existant, la table de correspondance rattache l'ancienne clé à la nouvelle : adresses %MW, voies "
         "et repères sont conservés, jamais recalculés. Les exemples ci-dessous utilisent le repère d'essai de la bibliothèque.", "",
         "## 3. Renommages", "",
         "| Type | Nature | Variante | Code actuel → proposé | Nom physique actuel → proposé | Information actuelle → proposée | Décision |",
         "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in ren:
        if not r["tele_propose"]:
            tele = f"`{r['tele_actuel']}`"
        elif " " in r["tele_propose"]:
            tele = f"`{r['tele_actuel']}` → {r['tele_propose']}"
        else:
            tele = f"`{r['tele_actuel']}` → `{r['tele_propose']}`"
        l.append(f"| {r['type']} | {r['nature']} | {r['variante']} | `{r['code_actuel']}` → `{r['code_propose']}` | "
                 f"`{r['physique_actuel']}` → `{r['physique_propose']}` | {tele} | ☐ |")
    l += ["", "Par type : " + ", ".join(f"{t} {n}" for t, n in sorted(par_type_ren.items())) + ".", "",
          *(["### Cas particuliers (hors décision A1)", "", *[f"- {x}" for x in d["particuliers"]], ""] if d["particuliers"] else []),
          "## 4. Ajouts", "",
          "Les types marqués **(nouveau type)** n'existent pas encore dans le catalogue : les approuver revient aussi à créer le type.", ""]
    for t in sorted(par_type_aj):
        lignes = [a for a in aj if a["type"] == t]
        marque = " (nouveau type)" if lignes[0]["type_nouveau"] else ""
        l += [f"### {t} — {lignes[0]['equipement']}{marque}", "",
              "| Nature | Code | Libellé | Présence | Nom physique (exemple) | Information associée | Décision |", "| --- | --- | --- | --- | --- | --- | --- |"]
        for a in lignes:
            l.append(f"| {a['nature']} | `{a['code']}` | {a['libelle']} | {a['presence']} · {a['variante']} | `{a['physique']}` | "
                     f"{('`' + a['tele'] + '`') if a['tele'] else '—'} | ☐ |")
        l.append("")
    l += ["## 5. Points d'attention", "",
          "- **54 ou " + str(len(ren)) + " renommages ?** Le rapport du 10/11 disait 54, le recalcul en trouve " + str(len(ren)) + ". Je n'ai pas modifié "
          "les chiffres pour les faire concorder : la liste de la section 3 fait foi.",
          "- **FV, VV, OU** : ces types n'ont aucune E/S dans le catalogue livré ; leurs E/S ne viennent que de ces ajouts.",
          "- **Rien n'est supposé** pour les caractéristiques constructeur : le tableau reprend la bibliothèque V1 telle quelle.",
          "- **Après votre accord** : brouillon du référentiel, contrôles de cohérence, essais d'adoption sur un ouvrage fictif, "
          "puis publication seulement sur votre ordre explicite. Aucun projet réel n'est touché.", ""]
    return "\n".join(l)


def _xlsx(d, chemin: Path) -> None:
    wb = Workbook()
    gras, fond = Font(bold=True), PatternFill("solid", fgColor="DDE6F3")
    liste = DataValidation(type="list", formula1=f'"{DECISIONS}"', allow_blank=True)
    for nom, colonnes, lignes in (
            ("Renommages", ["Type", "Nature", "Équipement", "Variante", "Code actuel", "Code proposé", "Nom physique actuel", "Nom physique proposé",
                            "Information actuelle", "Information proposée", "Décision", "Remarque"],
             [[r["type"], r["nature"], r["equipement"], r["variante"], r["code_actuel"], r["code_propose"], r["physique_actuel"],
               r["physique_propose"], r["tele_actuel"], r["tele_propose"], "", ""] for r in d["renommages"]]),
            ("Ajouts", ["Type", "Équipement", "Nouveau type", "Nature", "Code", "Libellé", "Présence", "Variante", "Nom physique (exemple)",
                        "Information associée", "Décision", "Remarque"],
             [[a["type"], a["equipement"], "oui" if a["type_nouveau"] else "non", a["nature"], a["code"], a["libelle"], a["presence"],
               a["variante"], a["physique"], a["tele"], "", ""] for a in d["ajouts"]])):
        ws = wb.active if nom == "Renommages" else wb.create_sheet()
        ws.title = nom
        ws.append(colonnes)
        for ligne in lignes:
            ws.append(ligne)
        for c in ws[1]:
            c.font, c.fill, c.alignment = gras, fond, Alignment(wrap_text=True, vertical="top")
        for i, c in enumerate(colonnes, 1):
            ws.column_dimensions[ws.cell(1, i).column_letter].width = 34 if c in ("Équipement", "Libellé", "Remarque") else 22
        ws.freeze_panes = "A2"
        if lignes:
            colonne = ws.cell(1, colonnes.index("Décision") + 1).column_letter
            validation = DataValidation(type="list", formula1=f'"{DECISIONS}"', allow_blank=True)
            ws.add_data_validation(validation)
            validation.add(f"{colonne}2:{colonne}{len(lignes) + 1}")
    del liste
    wb.save(chemin)


def generer(d=None):
    d = d or calculer()
    return _md(d), d


def main(argv) -> int:
    texte, d = generer()
    if "--verifier" in argv:
        if not MD.is_file() or MD.read_text(encoding="utf-8") != texte or not XLSX.is_file():
            print("L'aperçu A1 n'est plus à jour : py outils/apercu_a1.py")
            return 1
        wb = load_workbook(XLSX, read_only=True)
        try:
            if wb["Renommages"].max_row - 1 != len(d["renommages"]) or wb["Ajouts"].max_row - 1 != len(d["ajouts"]):
                print("Le classeur de l'aperçu A1 n'est plus à jour : py outils/apercu_a1.py")
                return 1
        finally:
            wb.close()
        return 0
    MD.write_text(texte, encoding="utf-8", newline="\n")
    _xlsx(d, XLSX)
    print(f"Écrit : {MD} et {XLSX}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
