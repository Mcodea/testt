"""Lecture de classeurs sans dépendance : .xlsx / .xlsm (Office Open XML), .ods (OpenDocument), .csv.

Renvoie les feuilles sous forme de listes de lignes (listes de textes). Lecture seule : le fichier
source n'est jamais modifié. Les macros d'un .xlsm ne sont ni lues ni exécutées.
"""
import csv
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

NS_X = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
NS_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
NS_T = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
NS_TX = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
MAX_COLONNES = 256
MAX_LIGNES_VIDES = 2000


def _col(ref):
    n = 0
    colonne = re.match(r"[A-Z]+", ref)
    if colonne is None:
        raise ValueError("Référence de cellule Excel invalide.")
    for c in colonne.group(0):
        n = n * 26 + ord(c) - 64
    return n - 1


def _lire_xlsx(z):
    partages = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(NS_X + "si"):
            partages.append("".join(t.text or "" for t in si.iter(NS_X + "t")))
    classeur = ET.fromstring(z.read("xl/workbook.xml"))
    rels = {r.get("Id"): r.get("Target") for r in
            ET.fromstring(z.read("xl/_rels/workbook.xml.rels")).iter(NS_REL + "Relationship")}
    feuilles = {}
    for f in classeur.iter(NS_X + "sheet"):
        cible = rels.get(f.get(NS_R + "id"))
        if not cible:
            raise ValueError("Une feuille Excel ne possède pas de cible valide.")
        chemin = "xl/" + cible.lstrip("/").removeprefix("xl/")
        if chemin not in z.namelist():
            continue
        lignes = []
        for row in ET.fromstring(z.read(chemin)).iter(NS_X + "row"):
            valeurs = {}
            for c in row.iter(NS_X + "c"):
                ref, t = c.get("r", ""), c.get("t")
                v = c.find(NS_X + "v")
                if t == "s" and v is not None:
                    if v.text is None:
                        raise ValueError("Référence de texte partagé Excel vide.")
                    try:
                        indice = int(v.text)
                        if indice < 0:
                            raise IndexError
                        texte = partages[indice]
                    except (ValueError, IndexError) as exc:
                        raise ValueError("Référence de texte partagé Excel invalide.") from exc
                elif t == "inlineStr":
                    texte = "".join(x.text or "" for x in c.iter(NS_X + "t"))
                else:
                    texte = v.text if v is not None and v.text is not None else ""
                if ref:
                    valeurs[_col(ref)] = texte
            if valeurs:
                largeur = min(max(valeurs) + 1, MAX_COLONNES)
                lignes.append([valeurs.get(i, "") for i in range(largeur)])
        feuilles[f.get("name")] = lignes
    return feuilles


def _lire_ods(z):
    racine = ET.fromstring(z.read("content.xml"))
    feuilles = {}
    for tab in racine.iter(NS_T + "table"):
        nom = tab.get(NS_T + "name", "")
        if nom.startswith("'") and "#" in nom:            # copie cache d'un classeur externe lié
            continue
        lignes, vides = [], 0
        for r in tab.iter(NS_T + "table-row"):
            cellules: list[str] = []
            for c in r:
                if c.tag not in (NS_T + "table-cell", NS_T + "covered-table-cell"):
                    continue
                n = int(c.get(NS_T + "number-columns-repeated", "1"))
                texte = " / ".join("".join(p.itertext()) for p in c.iter(NS_TX + "p"))
                cellules += [texte] * min(n, MAX_COLONNES - len(cellules))
                if len(cellules) >= MAX_COLONNES:
                    break
            while cellules and not cellules[-1]:
                cellules.pop()
            if cellules:
                lignes.append(cellules)
                vides = 0
            else:
                vides += int(r.get(NS_T + "number-rows-repeated", "1"))
                if vides > MAX_LIGNES_VIDES:
                    break
        feuilles[nom] = lignes
    return feuilles


def lire_classeur(chemin):
    """{nom de feuille: [[cellule, …], …]}."""
    p = Path(chemin)
    ext = p.suffix.lower()
    if ext in (".xlsx", ".xlsm"):
        with zipfile.ZipFile(p) as z:
            return _lire_xlsx(z)
    if ext == ".ods":
        with zipfile.ZipFile(p) as z:
            return _lire_ods(z)
    if ext in (".csv", ".txt"):
        donnees = p.read_bytes()
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                texte = donnees.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        sep = ";" if texte.count(";") >= texte.count(",") else ","
        return {p.stem: [r for r in csv.reader(io.StringIO(texte), delimiter=sep)]}
    raise ValueError(f"Format non pris en charge : {ext} (xlsx, xlsm, ods ou csv).")
