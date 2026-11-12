"""Échange du catalogue avec Excel, sans bibliothèque externe.

- exporter : écrit le catalogue dans un classeur (onglets Catalogue et Types) ;
- importer : relit un classeur corrigé dans Excel (le fichier Catalogue_signaux
  ou un export de l'outil). Les colonnes sont repérées par leur titre.
"""

import zipfile
import xml.etree.ElementTree as ET
from typing import Any

from .catalogue import Catalogue
from .export_xlsx import ecrire_xlsx

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "pr": "http://schemas.openxmlformats.org/package/2006/relationships"}

COLONNES_SIGNAUX = ["Type", "Information", "Famille", "Code", "Type logique", "Unité", "E/S", "Organe",
                    "Alarme", "Présence", "Option", "Statut", "Remarque", "Source physique", "Logique automate",
                    "Suffixe ES"]
COLONNES_TYPES = ["Code", "Désignation", "Catégorie", "Famille de la bibliothèque", "Options prévues", "Remarque",
                  "Domaine"]
COLONNES_REGLES = ["Identifiant", "Type", "Libellé", "Si (tous présents)", "Propose", "Mode", "Logique automate"]


# ====================================================================== lecture d'un .xlsx
def _col_index(ref):
    n = 0
    for ch in ref:
        if ch.isalpha():
            n = n * 26 + ord(ch.upper()) - 64
        else:
            break
    return n


def lire_xlsx(chemin):
    """{nom de l'onglet: [lignes]} ; chaque ligne est une liste de textes (colonne 1 = indice 0)."""
    with zipfile.ZipFile(chemin) as z:
        noms = z.namelist()
        partages = []
        if "xl/sharedStrings.xml" in noms:
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
                partages.append("".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")))
        rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")).findall("pr:Relationship", NS)}
        classeur = ET.fromstring(z.read("xl/workbook.xml"))
        onglets = {}
        feuilles = classeur.find("m:sheets", NS)
        if feuilles is None:
            raise ValueError("Le classeur Excel ne contient pas de liste de feuilles.")
        for s in feuilles.findall("m:sheet", NS):
            cible = rels.get(s.get(f"{{{NS['r']}}}id"))
            if not cible:
                raise ValueError("Une feuille Excel ne possède pas de cible valide.")
            cible = cible.lstrip("/")
            if not cible.startswith("xl/"):
                cible = "xl/" + cible
            feuille = ET.fromstring(z.read(cible))
            lignes = {}
            for row in feuille.iter(f"{{{NS['m']}}}row"):
                numero = row.get("r")
                if numero is None or not numero.isdecimal() or int(numero) < 1:
                    raise ValueError("Numéro de ligne Excel absent ou invalide.")
                r = int(numero)
                valeurs = {}
                for c in row.findall("m:c", NS):
                    t = c.get("t")
                    if t == "inlineStr":
                        texte = "".join(x.text or "" for x in c.iter(f"{{{NS['m']}}}t"))
                    else:
                        v = c.find("m:v", NS)
                        texte = "" if v is None or v.text is None else v.text
                        if t == "s" and texte:
                            texte = partages[int(texte)]
                        elif t == "b":
                            texte = "Oui" if texte == "1" else ""
                    valeurs[_col_index(c.get("r"))] = texte
                if valeurs:
                    lignes[r] = [valeurs.get(i, "") for i in range(1, max(valeurs) + 1)]
            onglets[s.get("name")] = [lignes.get(i, []) for i in range(1, (max(lignes) if lignes else 0) + 1)]
        return onglets


def _tableau(lignes, titres_requis):
    """Repère la ligne d'en-tête (celle qui contient tous les titres requis) ; renvoie (index des colonnes, lignes de données)."""
    for i, ligne in enumerate(lignes[:10]):
        titres = [" ".join(str(x).split()) for x in ligne]
        if all(t in titres for t in titres_requis):
            return {t: titres.index(t) for t in titres if t}, lignes[i + 1:]
    raise ValueError("Colonnes introuvables : " + ", ".join(titres_requis))


# ====================================================================== import
def importer(chemin):
    """Renvoie (catalogue, messages). Les messages décrivent ce qui a été fusionné ou ignoré."""
    onglets = lire_xlsx(chemin)
    if "Catalogue" not in onglets or "Types" not in onglets:
        raise ValueError("Le classeur doit contenir les onglets « Catalogue » et « Types ».")
    messages = []
    col, donnees = _tableau(onglets["Types"], ["Code", "Désignation"])
    val = lambda ligne, titre: (str(ligne[col[titre]]).strip() if titre in col and col[titre] < len(ligne) else "")
    types: list[dict[str, Any]] = []
    index: dict[str, dict[str, Any]] = {}
    for ligne in donnees:
        code = val(ligne, "Code").upper()
        if not code:
            continue
        options = [o.strip() for o in val(ligne, "Options prévues").split(";") if o.strip()]
        fb = val(ligne, "Famille de la bibliothèque")
        t: dict[str, Any] = {"code": code, "designation": val(ligne, "Désignation"), "categorie": val(ligne, "Catégorie") or "Équipement",
             "famille_biblio": "" if fb == "—" else fb, "options": options, "remarque": val(ligne, "Remarque"),
             "domaine": val(ligne, "Domaine")}
        if code in index:
            premier = index[code]
            notes = [x for x in options if x not in premier["options"]]
            if t["remarque"] and t["remarque"] not in premier["remarque"]:
                notes.append(t["remarque"])
            if notes:
                premier["remarque"] = (premier["remarque"] + " | " if premier["remarque"] else "") + "Note : " + " ; ".join(notes)
                messages.append(f"Type {code} déclaré deux fois : première ligne gardée, note ajoutée en remarque ({' ; '.join(notes)}).")
            else:
                messages.append(f"Type {code} déclaré deux fois : première ligne gardée.")
            continue
        index[code] = t
        types.append(t)

    col, donnees = _tableau(onglets["Catalogue"], ["Type", "Information", "Famille", "Code"])
    val = lambda ligne, titre: (str(ligne[col[titre]]).strip() if titre in col and col[titre] < len(ligne) else "")
    signaux = []
    for ligne in donnees:
        if not val(ligne, "Type") and not val(ligne, "Code"):
            continue
        signaux.append({"type": val(ligne, "Type").upper(), "information": val(ligne, "Information"),
                        "famille": val(ligne, "Famille").upper(), "code": val(ligne, "Code").upper(),
                        "type_logique": val(ligne, "Type logique").upper() or "BOOL", "unite": val(ligne, "Unité"),
                        "es": val(ligne, "E/S") or "Interne", "alarme": val(ligne, "Alarme") == "Oui",
                        "presence": val(ligne, "Présence") or "Par défaut", "option": val(ligne, "Option"),
                        "statut": val(ligne, "Statut") or "À valider", "remarque": val(ligne, "Remarque"),
                        "organe": val(ligne, "Organe").upper(), "source": val(ligne, "Source physique").upper(),
                        "logique": val(ligne, "Logique automate")})
        if val(ligne, "Suffixe ES"):                  # facultatif : seulement les collisions de clé (D4)
            signaux[-1]["suffixe_es"] = val(ligne, "Suffixe ES").upper()
    regles = []
    if "Règles" in onglets:
        col, donnees = _tableau(onglets["Règles"], ["Identifiant", "Type", "Si (tous présents)", "Propose"])
        val = lambda ligne, titre: (str(ligne[col[titre]]).strip() if titre in col and col[titre] < len(ligne) else "")
        for ligne in donnees:
            if not val(ligne, "Identifiant"):
                continue
            regles.append({"id": val(ligne, "Identifiant"), "type": val(ligne, "Type").upper(),
                           "libelle": val(ligne, "Libellé"),
                           "si": [x.strip().upper() for x in val(ligne, "Si (tous présents)").split(";") if x.strip()],
                           "propose": [x.strip().upper() for x in val(ligne, "Propose").split(";") if x.strip()],
                           "mode": val(ligne, "Mode") or "proposition", "logique": val(ligne, "Logique automate")})
    cat = Catalogue(types, signaux, regles=regles)
    sans_signal = [t["code"] for t in types if not any(s["type"] == t["code"] for s in signaux)]
    if sans_signal:
        messages.append("Types encore sans signal : " + ", ".join(sans_signal) + ".")
    return cat, messages


# ====================================================================== export
def exporter(catalogue, chemin):
    s_lig = [[s["type"], s["information"], s["famille"], s["code"], s["type_logique"], s.get("unite", ""), s.get("es", ""),
              s.get("organe", ""), "Oui" if s.get("alarme") else "", s["presence"], s.get("option", ""), s.get("statut", ""),
              s.get("remarque", ""), s.get("source", ""), s.get("logique", ""), s.get("suffixe_es", "")]
             for s in catalogue.signaux]
    t_lig = [[t["code"], t["designation"], t["categorie"], t.get("famille_biblio", "") or "—", " ; ".join(t.get("options", [])),
              t.get("remarque", ""), t.get("domaine", "")] for t in catalogue.types]
    r_lig = [[r.get("id", ""), r.get("type", ""), r.get("libelle", ""), " ; ".join(r.get("si", [])),
              " ; ".join(r.get("propose", [])), r.get("mode", ""), r.get("logique", "")] for r in catalogue.regles]
    ecrire_xlsx(chemin, [
        ("Catalogue", COLONNES_SIGNAUX, s_lig, [7, 30, 8, 10, 9, 9, 9, 8, 8, 12, 22, 11, 50, 14, 60, 12]),
        ("Types", COLONNES_TYPES, t_lig, [8, 30, 18, 22, 44, 62, 24]),
        ("Règles", COLONNES_REGLES, r_lig, [10, 7, 44, 34, 40, 13, 90]),
    ])
