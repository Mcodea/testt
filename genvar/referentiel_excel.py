"""Échange du référentiel métier OGIAS avec Excel : export, contrôle, aperçu des différences, révisions.

Le référentiel interne (catalogue.json : types, signaux, règles ; referentiel_modeles.json : modèles et lignes)
reste la SEULE source de vérité. Le classeur Excel n'est qu'une interface d'édition et d'échange :
- l'export écrit tout le référentiel, avec des identifiants stables, des listes déroulantes et une empreinte ;
- l'import relit le classeur, le CONTRÔLE (aucune modification si une erreur bloquante subsiste), calcule les
  différences avec le référentiel en service et ne l'applique qu'à la demande explicite de l'utilisateur ;
- l'import n'alimente qu'un BROUILLON (genvar/referentiel_depot.py) ; la publication crée la révision numérotée.

Identifiants stables (ce sont les clés auxquelles les règles et les ouvrages se réfèrent) :
- type        : son code (HV, PM…) ;
- signal      : TYPE.FAMILLE_CODE (HV.TS_DISC) ; pour un signal propre à un modèle : TYPE[Modèle].FAMILLE_CODE ;
- règle       : son identifiant (HV-03) ;
- modèle      : son nom ;
- ligne       : identifiant technique à 8 caractères, créé par OGIAS pour une ligne nouvelle.
Renommer un code revient à supprimer un signal et à en créer un autre : l'aperçu le montre comme tel.
Une suppression est toujours EXPLICITE (colonne « Supprimer » = Oui) ; une ligne absente du classeur bloque
l'import, pour qu'aucune donnée ne disparaisse par erreur de copier-coller.

Les ouvrages ne sont jamais modifiés : chacun garde le référentiel figé dans son fichier (catalogue_snapshot,
modeles_snapshot) et n'adopte une nouvelle révision que sur décision explicite (Session.adopter_referentiel).

Excel ne porte que des données. Une règle qui exige un nouvel algorithme de traitement automate se décrit en
texte (« Logique automate ») ; son exécution éventuelle relève du moteur Python, testé, jamais du classeur.
"""
import copy
import hashlib
import json
from typing import Any
import os
import uuid
import zipfile
from datetime import datetime
from xml.sax.saxutils import escape

from . import dictionnaire_es as _dico, lexique as _lexique, modeles as _modeles
from .catalogue import (Catalogue, CATEGORIES, FAMILLES_CATALOGUE, ORGANES, POINTS_ES, PRESENCES, STATUTS,
                        TYPES_LOGIQUES, sens_incoherent)
from .catalogue_excel import lire_xlsx
from .regles import GOUVERNANCES

FORMAT = "OGIAS-REFERENTIEL-1"
MODES = ("auto", "proposition")
OUI = "Oui"

# ---------------------------------------------------------------------------- colonnes
# (titre, clé interne, largeur, liste de valeurs ou None, modifiable)
C_TYPES = [("ID type", "code", 10, None, True), ("Désignation", "designation", 32, None, True),
           ("Catégorie", "categorie", 16, "Catégorie", True), ("Famille de bibliothèque", "famille_biblio", 22, None, True),
           ("Domaine", "domaine", 22, None, True), ("Options (séparées par ;)", "options", 48, None, True),
           ("Remarque", "remarque", 40, None, True), ("Supprimer", "_supprimer", 10, "Supprimer", True)]
C_SIGNAUX = [("ID signal", "_id", 24, None, False), ("Ordre", "_ordre", 7, None, True),
             ("Type", "type", 8, "Type", True), ("Modèle (vide = tout le type)", "_portee", 22, None, True),
             ("Famille", "famille", 8, "Famille", True), ("Code", "code", 12, None, True),
             ("Information", "information", 34, None, True), ("Nature E/S", "es", 10, "E/S", True),
             ("Organe", "organe", 8, "Organe", True), ("Suffixe ES (facultatif)", "suffixe_es", 14, None, True),
             ("Type logique", "type_logique", 11, "Type logique", True),
             ("Unité", "unite", 8, None, True), ("Alarme", "alarme", 8, "Oui/Non", True),
             ("Présence", "presence", 12, "Présence", True), ("Option", "option", 22, None, True),
             ("Statut", "statut", 11, "Statut", True), ("Source physique", "source", 14, None, True),
             ("Logique automate", "logique", 60, None, True), ("Remarque", "remarque", 30, None, True),
             ("Supprimer", "_supprimer", 10, "Supprimer", True)]
C_REGLES = [("ID règle", "id", 10, None, True), ("Ordre", "_ordre", 7, None, True), ("Type", "type", 8, None, True),
            ("Libellé", "libelle", 40, None, True), ("Si (toutes présentes, séparées par ;)", "si", 34, None, True),
            ("Propose (séparées par ;)", "propose", 34, None, True), ("Mode", "mode", 12, "Mode", True),
            ("Gouvernance", "gouvernance", 24, "Gouvernance", True),
            ("Logique automate", "logique", 70, None, True), ("Supprimer", "_supprimer", 10, "Supprimer", True)]
C_TYPES_MODELES = [("ID type", "code", 10, None, True), ("Désignation", "designation", 32, None, True),
                   ("Domaine", "domaine", 18, "Domaine modèle", True), ("Archivé", "archive", 10, "Oui/Non", True),
                   ("Supprimer", "_supprimer", 10, "Supprimer", True)]
C_MODELES = [("ID modèle", "nom", 34, None, True), ("Ordre", "_ordre", 7, None, True), ("Type", "type", 10, None, True),
             ("Statut", "statut", 12, "Statut modèle", True), ("Supprimer", "_supprimer", 10, "Supprimer", True)]
C_LIGNES = [("ID ligne", "id", 11, None, False), ("Modèle", "_modele", 32, None, True), ("Ordre", "_ordre", 7, None, True),
            ("Rôle", "role", 8, "Rôle", True), ("Libellé", "libelle", 34, None, True),
            ("Suffixe", "suffixe", 18, None, True), ("Format", "format", 9, "Format", True),
            ("Unité", "unite", 8, None, True), ("Commentaire", "commentaire", 40, None, True),
            ("Supprimer", "_supprimer", 10, "Supprimer", True)]

C_LEXIQUE = [("Mot ou expression", "mot", 34, None, True), ("Abréviation", "abreviation", 16, None, True),
             ("Nature", "nature", 12, "Nature lexique", True), ("Code du dictionnaire des E/S", "dictionnaire_es", 18, "Oui/Non", True),
             ("Supprimer", "_supprimer", 10, "Supprimer", True)]
C_DICTIONNAIRE = [("Code", "code", 12, None, True), ("Nature", "nature", 8, "E/S physique", True),
                  ("Catégorie", "categorie", 16, None, True), ("Libellé standard", "libelle", 34, None, True),
                  ("Télétransmission", "teletransmission", 16, None, True),
                  ("Types qui l'utilisent (séparés par ;)", "types", 30, None, True),
                  ("Supprimer", "_supprimer", 10, "Supprimer", True)]
C_CORRESPONDANCES = [("Type", "type", 8, None, True), ("Ancienne clé", "ancienne", 18, None, True),
                     ("Nouveau type", "type_nouveau", 10, None, True), ("Nouvelle clé", "nouvelle", 18, None, True),
                     ("Motif", "motif", 60, None, True), ("Supprimer", "_supprimer", 10, "Supprimer", True)]
CHAMPS_CORRESPONDANCE = ("type", "ancienne", "type_nouveau", "nouvelle", "motif")
LISTES = {"Famille": FAMILLES_CATALOGUE, "Présence": PRESENCES, "E/S": POINTS_ES, "Type logique": TYPES_LOGIQUES,
          "Organe": [o for o in ORGANES if o], "Statut": STATUTS, "Mode": list(MODES), "Oui/Non": [OUI, "Non"],
          "Supprimer": [OUI], "Catégorie": CATEGORIES, "Rôle": list(_modeles.ROLES), "Format": list(_modeles.FORMATS),
          "Statut modèle": list(_modeles.STATUTS_MODELE), "Domaine modèle": list(_modeles.DOMAINES),
          "Nature lexique": list(_lexique.NATURES), "Gouvernance": list(GOUVERNANCES), "E/S physique": list(_dico.NATURES)}

CHAMPS_SIGNAL = ("type", "information", "famille", "code", "type_logique", "unite", "es", "alarme", "presence",
                 "option", "statut", "remarque", "organe", "source", "logique", "suffixe_es")
CHAMPS_TYPE = ("code", "designation", "categorie", "famille_biblio", "options", "remarque", "domaine")
CHAMPS_REGLE = ("id", "type", "libelle", "si", "propose", "mode", "logique", "gouvernance")
CHAMPS_LIGNE = ("id", "role", "libelle", "suffixe", "format", "unite", "commentaire")
CHAMPS_LEXIQUE = ("mot", "abreviation", "nature", "dictionnaire_es")
CHAMPS_DICTIONNAIRE = ("code", "nature", "categorie", "libelle", "teletransmission", "types")


class ReferentielInvalide(ValueError):
    """Classeur illisible ou incohérent : rien n'est modifié."""


# ============================================================================ état interne normalisé
def _signal(s):
    d = {k: s.get(k, "") for k in CHAMPS_SIGNAL}
    d["alarme"] = bool(s.get("alarme"))
    return d


def etat(catalogue, ref_modeles):
    """Vue normalisée et complète du référentiel (comparable, sérialisable)."""
    signaux = [dict(_signal(s), _portee="") for s in catalogue.signaux]
    for nom, m in _modeles_ordonnes(ref_modeles):
        for s in m.get("signaux", []) if "signaux" in m else []:
            signaux.append(dict(_signal(dict(s, type=m["type"])), _portee=nom))
    return {
        "types": [{k: (list(t.get(k, [])) if k == "options" else t.get(k, "")) for k in CHAMPS_TYPE} for t in catalogue.types],
        "signaux": signaux,
        "regles": [{k: (list(r.get(k, [])) if k in ("si", "propose") else r.get(k, "")) for k in CHAMPS_REGLE}
                   for r in catalogue.regles],
        "types_modeles": [{"code": c, "designation": t.get("designation", ""), "domaine": t.get("domaine", ""),
                           "archive": bool(t.get("archive"))}
                          for c, t in ref_modeles.get("types", {}).items()],
        "modeles": [{"nom": n, "type": m.get("type", ""), "statut": m.get("statut", "à valider"),
                     "_avec_signaux": "signaux" in m}
                    for n, m in _modeles_ordonnes(ref_modeles)],
        "lignes": [dict({k: l.get(k, "") for k in CHAMPS_LIGNE}, _modele=n)
                   for n, m in _modeles_ordonnes(ref_modeles) for l in m.get("lignes", [])],
        "lexique": [dict({k: e.get(k, "") for k in CHAMPS_LEXIQUE}, dictionnaire_es=bool(e.get("dictionnaire_es")))
                    for e in ref_modeles.get("lexique", [])],
        "dictionnaire_es": [_dico.entree(**{k: e.get(k, "") for k in CHAMPS_DICTIONNAIRE})
                            for e in ref_modeles.get("dictionnaire_es", [])],
        "correspondances": [{k: c.get(k, "") or (c.get("type", "") if k == "type_nouveau" else "")
                             for k in CHAMPS_CORRESPONDANCE} for c in ref_modeles.get("correspondances", [])],
    }


def _modeles_ordonnes(ref):
    """Modèles dans l'ordre du référentiel : par type, dans l'ordre de la liste du type, puis les autres."""
    vus, sortie = set(), []
    for t in ref.get("types", {}).values():
        for n in t.get("modeles", []):
            if n in ref.get("modeles", {}) and n not in vus:
                vus.add(n); sortie.append((n, ref["modeles"][n]))
    for n, m in ref.get("modeles", {}).items():
        if n not in vus:
            sortie.append((n, m))
    return sortie


def empreinte(e):
    texte = json.dumps(e, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()[:16]


def id_signal(s):
    portee = f"[{s['_portee']}]" if s.get("_portee") else ""
    return f"{s['type']}{portee}.{s['famille']}_{s['code']}"


# ============================================================================ export
def _col(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _cellule(ref, valeur, style):
    st = f' s="{style}"' if style else ""
    if valeur is None or valeur == "":
        return f'<c r="{ref}"{st}/>'
    texte = escape(str(valeur)).replace("\n", "&#10;")
    return f'<c r="{ref}"{st} t="inlineStr"><is><t xml:space="preserve">{texte}</t></is></c>'


STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="4"><font><sz val="10"/><name val="Calibri"/></font><font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>
<font><sz val="10"/><color rgb="FF5B6B7A"/><name val="Calibri"/></font><font><b/><sz val="14"/><color rgb="FF193854"/><name val="Calibri"/></font></fonts>
<fills count="5"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF193854"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFEEF1F4"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF5B6B7A"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border>
<border><left style="thin"><color rgb="FFC9D3DC"/></left><right style="thin"><color rgb="FFC9D3DC"/></right>
<top style="thin"><color rgb="FFC9D3DC"/></top><bottom style="thin"><color rgb="FFC9D3DC"/></bottom><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="7"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
<xf numFmtId="49" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
<xf numFmtId="49" fontId="2" fillId="3" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="top"/></xf>
<xf numFmtId="0" fontId="1" fillId="4" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""
LIGNES_SAISIE = 3000          # plage couverte par les listes déroulantes (lignes ajoutées comprises)


def _feuille_tableau(colonnes, lignes, refs_listes):
    n = len(colonnes)
    x = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
         '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
         '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
         '</sheetView></sheetViews><sheetFormatPr defaultRowHeight="15"/><cols>']
    for i, (_, _, w, _, _) in enumerate(colonnes, 1):
        x.append(f'<col min="{i}" max="{i}" width="{w}" customWidth="1" style="2"/>')
    x.append('</cols><sheetData><row r="1" ht="30" customHeight="1">')
    x.append("".join(_cellule(f"{_col(i)}1", c[0], 1 if c[4] else 4) for i, c in enumerate(colonnes, 1)) + "</row>")
    for r, ligne in enumerate(lignes, 2):
        x.append(f'<row r="{r}">' + "".join(_cellule(f"{_col(i)}{r}", v, 2 if colonnes[i - 1][4] else 3)
                                            for i, v in enumerate(ligne, 1)) + "</row>")
    x.append("</sheetData>")
    x.append(f'<autoFilter ref="A1:{_col(n)}{max(2, len(lignes) + 1)}"/>')
    val = [(i, c[3]) for i, c in enumerate(colonnes, 1) if c[3]]
    if val:
        x.append(f'<dataValidations count="{len(val)}">')
        for i, liste in val:
            x.append(f'<dataValidation type="list" allowBlank="1" showErrorMessage="1" errorStyle="stop" '
                     f'errorTitle="Valeur non autorisée" error="Choisissez une valeur de la liste « {escape(liste)} »." '
                     f'sqref="{_col(i)}2:{_col(i)}{LIGNES_SAISIE}"><formula1>{refs_listes[liste]}</formula1></dataValidation>')
        x.append("</dataValidations>")
    x.append('<pageMargins left="0.4" right="0.4" top="0.5" bottom="0.5" header="0.3" footer="0.3"/>'
             '<pageSetup orientation="landscape" fitToHeight="0"/></worksheet>')
    return "".join(x)


def _feuille_texte(lignes):
    x = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
         '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
         '<sheetViews><sheetView workbookViewId="0" showGridLines="0"/></sheetViews>',
         '<cols><col min="1" max="1" width="30" customWidth="1"/><col min="2" max="2" width="110" customWidth="1"/></cols><sheetData>']
    for r, (a, b, style) in enumerate(lignes, 1):
        x.append(f'<row r="{r}">{_cellule(f"A{r}", a, style)}{_cellule(f"B{r}", b, 6)}</row>')
    x.append("</sheetData></worksheet>")
    return "".join(x)


def _feuille_listes():
    noms = list(LISTES)
    x = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
         '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><cols>']
    x += [f'<col min="{i}" max="{i}" width="18" customWidth="1"/>' for i in range(1, len(noms) + 1)]
    x.append('</cols><sheetData>')
    hauteur = max(len(v) for v in LISTES.values())
    x.append('<row r="1">' + "".join(_cellule(f"{_col(i)}1", n, 1) for i, n in enumerate(noms, 1)) + "</row>")
    for r in range(hauteur):
        x.append(f'<row r="{r + 2}">' + "".join(_cellule(f"{_col(i)}{r + 2}", LISTES[n][r] if r < len(LISTES[n]) else "", 2)
                                                for i, n in enumerate(noms, 1)) + "</row>")
    x.append("</sheetData></worksheet>")
    refs = {n: f"Valeurs!${_col(i)}$2:${_col(i)}${len(LISTES[n]) + 1}" for i, n in enumerate(noms, 1)}
    refs["Type"] = f"Types!$A$2:$A${LIGNES_SAISIE}"
    return "".join(x), refs


def _valeur(k, objet, ordre):
    if k == "_supprimer":
        return ""
    if k == "_ordre":
        return str(ordre)
    if k == "_id":
        return id_signal(objet)
    v = objet.get(k, "")
    if isinstance(v, bool):
        return OUI if v else "Non"
    if isinstance(v, list):
        return " ; ".join(v)
    return v


def exporter(catalogue, ref_modeles, chemin, revision=""):
    """Écrit le référentiel complet dans un classeur .xlsx (sans bibliothèque externe). Renvoie l'empreinte."""
    e = etat(catalogue, ref_modeles)
    emp = empreinte(e)
    xml_listes, refs = _feuille_listes()
    tab = lambda cols, objets: [[_valeur(c[1], o, i) for c in cols] for i, o in enumerate(objets, 1)]
    lisez = [("Référentiel métier OGIAS", "", 5), ("", "", 0),
             ("Format", FORMAT, 0), ("Révision exportée", revision or catalogue.version, 0),
             ("Empreinte", emp, 0), ("Date d'export", datetime.now().strftime("%d/%m/%Y %H:%M"), 0), ("", "", 0),
             ("Rôle de ce classeur", "Interface d'édition du référentiel. La référence reste le référentiel interne "
              "d'OGIAS : rien n'est appliqué sans contrôle ni aperçu des différences.", 0),
             ("Colonnes grises", "Identifiants calculés par OGIAS : ne pas les modifier. Une ligne nouvelle peut laisser "
              "l'identifiant vide.", 0),
             ("Supprimer", "Pour retirer un élément, écrivez « Oui » dans la colonne Supprimer. Ne supprimez pas la "
              "ligne : une ligne absente bloque l'import.", 0),
             ("Ordre", "Ordre de génération (et donc d'adressage) des signaux d'un type ; un nombre décimal permet "
              "d'insérer une ligne entre deux autres (ex. 12.5).", 0),
             ("Présence", "Obligatoire : toujours généré ; Par défaut : généré, retirable ; Option : généré si l'option "
              "de l'équipement est cochée ; Règle : proposé par une règle (onglet Règles).", 0),
             ("Règles", "« Si » et « Propose » citent des clés FAMILLE_CODE du même type (ES_FDC_OUV, TS_DISC). "
              "Mode auto : retenu d'office ; proposition : décision de l'automaticien exigée. Une règle qui demande un "
              "nouvel algorithme de traitement se décrit dans « Logique automate » ; le moteur OGIAS, lui, est modifié "
              "et testé à part.", 0),
             ("Signal propre à un modèle", "Renseigner la colonne Modèle : le signal ne concerne que ce modèle "
              "(sinon il vaut pour tout le type).", 0),
             ("Ouvrages existants", "Ils gardent le référentiel figé dans leur fichier. Une nouvelle révision ne leur "
              "est appliquée que par une décision explicite dans OGIAS.", 0)]
    feuilles = [("Lisez-moi", _feuille_texte(lisez)),
                ("Types", _feuille_tableau(C_TYPES, tab(C_TYPES, e["types"]), refs)),
                ("Signaux", _feuille_tableau(C_SIGNAUX, tab(C_SIGNAUX, e["signaux"]), refs)),
                ("Règles", _feuille_tableau(C_REGLES, tab(C_REGLES, e["regles"]), refs)),
                ("Types de modèles", _feuille_tableau(C_TYPES_MODELES, tab(C_TYPES_MODELES, e["types_modeles"]), refs)),
                ("Modèles", _feuille_tableau(C_MODELES, tab(C_MODELES, e["modeles"]), refs)),
                ("Lignes de modèles", _feuille_tableau(C_LIGNES, [[_valeur(c[1], l, i) if c[1] != "_modele" else l["_modele"]
                                                                    for c in C_LIGNES] for i, l in enumerate(e["lignes"], 1)], refs)),
                ("Lexique", _feuille_tableau(C_LEXIQUE, tab(C_LEXIQUE, e["lexique"]), refs)),
                ("Dictionnaire E-S", _feuille_tableau(C_DICTIONNAIRE, tab(C_DICTIONNAIRE, e["dictionnaire_es"]), refs)),
                ("Correspondances", _feuille_tableau(C_CORRESPONDANCES, tab(C_CORRESPONDANCES, e["correspondances"]), refs)),
                ("Valeurs", xml_listes)]
    _ecrire_paquet(chemin, feuilles)
    return emp


def _ecrire_paquet(chemin, feuilles):
    n = len(feuilles)
    ct = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
          '<Default Extension="xml" ContentType="application/xml"/>',
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
          '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>']
    ct += [f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
           for i in range(1, n + 1)]
    ct.append("</Types>")
    wb = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><bookViews><workbookView activeTab="0"/></bookViews><sheets>']
    wb += [f'<sheet name="{escape(nom)}" sheetId="{i}" r:id="rId{i}"/>' for i, (nom, _) in enumerate(feuilles, 1)]
    wb.append("</sheets></workbook>")
    rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    rels += [f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
             f'Target="worksheets/sheet{i}.xml"/>' for i in range(1, n + 1)]
    rels.append(f'<Relationship Id="rId{n + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>')
    rels.append("</Relationships>")
    provisoire = chemin + ".tmp"
    with zipfile.ZipFile(provisoire, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "".join(ct))
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                   '</Relationships>')
        z.writestr("xl/workbook.xml", "".join(wb))
        z.writestr("xl/_rels/workbook.xml.rels", "".join(rels))
        z.writestr("xl/styles.xml", STYLES)
        for i, (_, xml) in enumerate(feuilles, 1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", xml)
    os.replace(provisoire, chemin)


# ============================================================================ lecture
class Lecture:
    def __init__(self):
        self.erreurs, self.alertes = [], []

    def err(self, onglet, ligne, msg):
        self.erreurs.append(f"{onglet}, ligne {ligne} : {msg}" if ligne else f"{onglet} : {msg}")

    def alerte(self, onglet, ligne, msg):
        self.alertes.append(f"{onglet}, ligne {ligne} : {msg}" if ligne else f"{onglet} : {msg}")


def _table(lect, onglets, nom, colonnes):
    """[(numéro de ligne Excel, {clé: texte})] ; vérifie les en-têtes."""
    if nom not in onglets:
        lect.err(nom, 0, "onglet absent du classeur.")
        return []
    lignes = onglets[nom]
    if not lignes:
        lect.err(nom, 0, "onglet vide.")
        return []
    entetes = [str(x).strip() for x in lignes[0]]
    index = {}
    for titre, cle, *_ in colonnes:
        if titre not in entetes:
            lect.err(nom, 1, f"colonne « {titre} » absente.")
        else:
            index[cle] = entetes.index(titre)
    sortie = []
    for r, ligne in enumerate(lignes[1:], 2):
        valeurs = {cle: (str(ligne[i]).strip() if i < len(ligne) else "") for cle, i in index.items()}
        if any(valeurs.values()):
            sortie.append((r, valeurs))
    return sortie


def _ordre(lect, onglet, r, texte, defaut):
    if not texte:
        return defaut
    try:
        return float(texte.replace(",", "."))
    except ValueError:
        lect.err(onglet, r, f"Ordre « {texte} » : nombre attendu.")
        return defaut


def _liste(texte):
    return [x.strip() for x in texte.replace(",", ";").split(";") if x.strip()] if texte else []


def _dans(lect, onglet, r, nom, valeur, autorisees, vide_ok=True):
    if valeur == "" and vide_ok:
        return
    if valeur not in autorisees:
        lect.err(onglet, r, f"{nom} « {valeur} » non autorisé ({', '.join(a for a in autorisees if a)}).")


def lire(chemin):
    """Relit un classeur exporté puis modifié : (état normalisé proposé, Lecture, méta). Rien n'est appliqué."""
    try:
        onglets = lire_xlsx(chemin)
    except (zipfile.BadZipFile, KeyError, OSError, ValueError) as exc:
        raise ReferentielInvalide(f"Classeur illisible : {exc}") from exc
    lect = Lecture()
    meta = {}
    for ligne in onglets.get("Lisez-moi", []):
        if len(ligne) >= 2 and ligne[0]:
            meta[str(ligne[0]).strip()] = str(ligne[1]).strip()
    if meta.get("Format") != FORMAT:
        raise ReferentielInvalide("Ce classeur n'est pas un export du référentiel OGIAS (onglet Lisez-moi, Format "
                                  f"« {FORMAT} » attendu). Exportez d'abord le référentiel depuis OGIAS.")
    oui = lambda v: v.strip().lower() in ("oui", "o", "x", "1", "vrai", "true")
    nouveau: dict[str, Any] = {"types": [], "signaux": [], "regles": [], "types_modeles": [], "modeles": [], "lignes": [],
               "lexique": [], "dictionnaire_es": [], "correspondances": [],
               "supprimes": {"types": [], "signaux": [], "regles": [], "types_modeles": [], "modeles": [],
                             "lignes": [], "lexique": [], "dictionnaire_es": [], "correspondances": []}}

    for r, v in _table(lect, onglets, "Types", C_TYPES):
        code = v.get("code", "").upper()
        if not code:
            lect.err("Types", r, "ID type vide.")
            continue
        _dans(lect, "Types", r, "Catégorie", v.get("categorie", ""), CATEGORIES)
        t = {"code": code, "designation": v.get("designation", ""), "categorie": v.get("categorie", "") or "Équipement",
             "famille_biblio": v.get("famille_biblio", ""), "options": _liste(v.get("options", "")),
             "remarque": v.get("remarque", ""), "domaine": v.get("domaine", "")}
        (nouveau["supprimes"]["types"] if oui(v.get("_supprimer", "")) else nouveau["types"]).append(dict(t, _r=r))

    for r, v in _table(lect, onglets, "Signaux", C_SIGNAUX):
        s = {"type": v.get("type", "").upper(), "information": v.get("information", ""),
             "famille": v.get("famille", "").upper(), "code": v.get("code", "").upper(),
             "type_logique": v.get("type_logique", "").upper(), "unite": v.get("unite", ""), "es": v.get("es", ""),
             "alarme": oui(v.get("alarme", "")), "presence": v.get("presence", ""), "option": v.get("option", ""),
             "statut": v.get("statut", ""), "remarque": v.get("remarque", ""), "organe": v.get("organe", "").upper(),
             "suffixe_es": v.get("suffixe_es", "").upper(),
             "source": v.get("source", "").upper(), "logique": v.get("logique", ""), "_portee": v.get("_portee", ""),
             "_r": r, "_o": _ordre(lect, "Signaux", r, v.get("_ordre", ""), 10 ** 9 + r), "_id_lu": v.get("_id", "")}
        if not (s["type"] and s["famille"] and s["code"]):
            lect.err("Signaux", r, "Type, Famille et Code sont obligatoires.")
            continue
        if s["_id_lu"] and s["_id_lu"] != id_signal(s):
            lect.err("Signaux", r, f"l'identifiant {s['_id_lu']} ne correspond plus au type, au modèle, à la famille "
                                   f"ou au code ({id_signal(s)}). Pour renommer : marquez l'ancienne ligne « Supprimer » "
                                   "et ajoutez une ligne sans identifiant.")
        (nouveau["supprimes"]["signaux"] if oui(v.get("_supprimer", "")) else nouveau["signaux"]).append(s)

    for r, v in _table(lect, onglets, "Règles", C_REGLES):
        if not v.get("id"):
            lect.err("Règles", r, "ID règle vide.")
            continue
        g = {"id": v["id"], "type": v.get("type", "").upper(), "libelle": v.get("libelle", ""),
             "si": [x.upper() for x in _liste(v.get("si", ""))], "propose": [x.upper() for x in _liste(v.get("propose", ""))],
             "mode": v.get("mode", ""), "logique": v.get("logique", ""), "gouvernance": v.get("gouvernance", ""),
             "_r": r,
             "_o": _ordre(lect, "Règles", r, v.get("_ordre", ""), 10 ** 9 + r)}
        (nouveau["supprimes"]["regles"] if oui(v.get("_supprimer", "")) else nouveau["regles"]).append(g)

    lignes_types = onglets.get("Types de modèles", [])
    entetes_types = lignes_types[0] if lignes_types else []
    colonnes_types = [c for c in C_TYPES_MODELES if c[1] != "archive" or "Archivé" in entetes_types]
    for r, v in _table(lect, onglets, "Types de modèles", colonnes_types):
        if not v.get("code"):
            lect.err("Types de modèles", r, "ID type vide.")
            continue
        valeur_archive = v.get("archive", "").strip().lower()
        if valeur_archive not in ("", "oui", "non", "o", "n", "x", "1", "0", "vrai", "faux", "true", "false"):
            lect.err("Types de modèles", r, "Archivé : choisissez Oui ou Non.")
        t = {"code": v["code"].upper(), "designation": v.get("designation", ""), "domaine": v.get("domaine", ""),
             "archive": oui(v["archive"]) if "archive" in v else None, "_r": r}
        (nouveau["supprimes"]["types_modeles"] if oui(v.get("_supprimer", "")) else nouveau["types_modeles"]).append(t)

    for r, v in _table(lect, onglets, "Modèles", C_MODELES):
        if not v.get("nom"):
            lect.err("Modèles", r, "ID modèle vide.")
            continue
        m = {"nom": v["nom"], "type": v.get("type", "").upper(), "statut": v.get("statut", "") or "à valider", "_r": r,
             "_o": _ordre(lect, "Modèles", r, v.get("_ordre", ""), 10 ** 9 + r)}
        (nouveau["supprimes"]["modeles"] if oui(v.get("_supprimer", "")) else nouveau["modeles"]).append(m)

    for r, v in _table(lect, onglets, "Lignes de modèles", C_LIGNES):
        l = {"id": v.get("id", ""), "_modele": v.get("_modele", ""), "role": v.get("role", "").upper(),
             "libelle": v.get("libelle", ""), "suffixe": v.get("suffixe", "").upper(), "format": v.get("format", "").upper(),
             "unite": v.get("unite", ""), "commentaire": v.get("commentaire", ""), "_r": r,
             "_o": _ordre(lect, "Lignes de modèles", r, v.get("_ordre", ""), 10 ** 9 + r)}
        (nouveau["supprimes"]["lignes"] if oui(v.get("_supprimer", "")) else nouveau["lignes"]).append(l)

    if "Lexique" not in onglets:                       # export antérieur au lexique : lexique en service conservé
        nouveau["lexique"] = None
        lect.alerte("Lexique", 0, "onglet absent (export antérieur) : le lexique en service est conservé.")
    else:
        for r, v in _table(lect, onglets, "Lexique", C_LEXIQUE):
            e = dict(_lexique.entree(v.get("mot"), v.get("abreviation"), v.get("nature"), v.get("dictionnaire_es")), _r=r)
            (nouveau["supprimes"]["lexique"] if oui(v.get("_supprimer", "")) else nouveau["lexique"]).append(e)

    if "Dictionnaire E-S" not in onglets:               # export antérieur : dictionnaire en service conservé
        nouveau["dictionnaire_es"] = None
        lect.alerte("Dictionnaire E-S", 0, "onglet absent (export antérieur) : le dictionnaire en service est conservé.")
    else:
        for r, v in _table(lect, onglets, "Dictionnaire E-S", C_DICTIONNAIRE):
            e = dict(_dico.entree(**{k: v.get(k, "") for k in CHAMPS_DICTIONNAIRE}), _r=r)
            (nouveau["supprimes"]["dictionnaire_es"] if oui(v.get("_supprimer", ""))
             else nouveau["dictionnaire_es"]).append(e)

    if "Correspondances" not in onglets:                # export antérieur : correspondances en service conservées
        nouveau["correspondances"] = None
    else:
        for r, v in _table(lect, onglets, "Correspondances", C_CORRESPONDANCES):
            c = {k: str(v.get(k, "") or "").strip().upper() for k in CHAMPS_CORRESPONDANCE if k != "motif"}
            c["type_nouveau"] = c["type_nouveau"] or c["type"]
            c.update(motif=str(v.get("motif", "") or "").strip(), _r=r)
            (nouveau["supprimes"]["correspondances"] if oui(v.get("_supprimer", ""))
             else nouveau["correspondances"]).append(c)
    return nouveau, lect, meta


# ============================================================================ contrôle
def controler(nouveau, actuel, lect):
    """Contrôles avant import : doublons, références manquantes, types, cohérence E/S ↔ télétransmission,
    lignes disparues. Remplit lect.erreurs (bloquantes) et lect.alertes."""
    E, A = lect.err, lect.alerte
    # --- doublons
    def doublons(objets, cle, onglet):
        vus: dict = {}
        for o in objets:
            k = cle(o)
            if k in vus:
                E(onglet, o["_r"], f"{k} déjà défini ligne {vus[k]}.")
            vus.setdefault(k, o["_r"])
        return vus
    types = doublons(nouveau["types"], lambda t: t["code"], "Types")
    doublons(nouveau["signaux"], id_signal, "Signaux")
    doublons(nouveau["regles"], lambda g: g["id"], "Règles")
    types_m = doublons(nouveau["types_modeles"], lambda t: t["code"], "Types de modèles")
    modeles = doublons(nouveau["modeles"], lambda m: m["nom"], "Modèles")
    doublons([l for l in nouveau["lignes"] if l["id"]], lambda l: l["id"], "Lignes de modèles")

    # --- lignes disparues (une suppression doit être explicite)
    def disparus(cles_actuelles, cles_lues, onglet, libelle):
        manquants = [k for k in cles_actuelles if k not in cles_lues]
        if manquants:
            E(onglet, 0, f"{len(manquants)} {libelle} absent(s) du classeur (ex. {', '.join(manquants[:4])}). "
                         "Pour supprimer, gardez la ligne et écrivez « Oui » dans la colonne Supprimer.")
    sup = nouveau["supprimes"]
    disparus([t["code"] for t in actuel["types"]], {t["code"] for t in nouveau["types"] + sup["types"]}, "Types", "type(s)")
    disparus([id_signal(s) for s in actuel["signaux"]], {id_signal(s) for s in nouveau["signaux"] + sup["signaux"]},
             "Signaux", "signal(aux)")
    disparus([g["id"] for g in actuel["regles"]], {g["id"] for g in nouveau["regles"] + sup["regles"]}, "Règles", "règle(s)")
    disparus([t["code"] for t in actuel["types_modeles"]], {t["code"] for t in nouveau["types_modeles"] + sup["types_modeles"]},
             "Types de modèles", "type(s) de modèles")
    disparus([m["nom"] for m in actuel["modeles"]], {m["nom"] for m in nouveau["modeles"] + sup["modeles"]}, "Modèles", "modèle(s)")
    disparus([l["id"] for l in actuel["lignes"]], {l["id"] for l in nouveau["lignes"] + sup["lignes"] if l["id"]},
             "Lignes de modèles", "ligne(s)")
    if nouveau.get("lexique") is not None:
        cle_lex = lambda e: _lexique.normaliser(e["mot"])
        disparus([cle_lex(e) for e in actuel.get("lexique", [])],
                 {cle_lex(e) for e in nouveau["lexique"] + sup["lexique"]}, "Lexique", "entrée(s) de lexique")
        erreurs_lex, alertes_lex = _lexique.controler([{k: e[k] for k in CHAMPS_LEXIQUE} for e in nouveau["lexique"]])
        for m in erreurs_lex:
            E("Lexique", 0, m)
        for m in alertes_lex:
            A("Lexique", 0, m)
    if nouveau.get("dictionnaire_es") is not None:
        disparus([_dico.cle(e) for e in actuel.get("dictionnaire_es", [])],
                 {_dico.cle(e) for e in nouveau["dictionnaire_es"] + sup["dictionnaire_es"]},
                 "Dictionnaire E-S", "code(s) du dictionnaire")
        erreurs_dic, alertes_dic = _dico.controler([{k: e[k] for k in CHAMPS_DICTIONNAIRE}
                                                    for e in nouveau["dictionnaire_es"]])
        for m in erreurs_dic:
            E("Dictionnaire E-S", 0, m)
        for m in alertes_dic:
            A("Dictionnaire E-S", 0, m)
    ids_actuels = {l["id"] for l in actuel["lignes"]}
    for l in nouveau["lignes"] + sup["lignes"]:
        if l["id"] and l["id"] not in ids_actuels:
            E("Lignes de modèles", l["_r"], f"identifiant {l['id']} inconnu : laissez l'identifiant vide pour une ligne nouvelle.")

    # --- signaux
    options = {t["code"]: set(t["options"]) for t in nouveau["types"]}
    for s in nouveau["signaux"]:
        r = s["_r"]
        if s["type"] not in types:
            E("Signaux", r, f"type {s['type']} absent de l'onglet Types (ou marqué Supprimer).")
        if s["_portee"] and s["_portee"] not in modeles:
            E("Signaux", r, f"modèle « {s['_portee']} » absent de l'onglet Modèles.")
        _dans(lect, "Signaux", r, "Famille", s["famille"], FAMILLES_CATALOGUE, vide_ok=False)
        _dans(lect, "Signaux", r, "Nature E/S", s["es"], POINTS_ES, vide_ok=False)
        _dans(lect, "Signaux", r, "Type logique", s["type_logique"], TYPES_LOGIQUES, vide_ok=False)
        _dans(lect, "Signaux", r, "Présence", s["presence"], PRESENCES, vide_ok=False)
        _dans(lect, "Signaux", r, "Statut", s["statut"], STATUTS, vide_ok=False)
        _dans(lect, "Signaux", r, "Organe", s["organe"], ORGANES)
        if not s["information"]:
            E("Signaux", r, "Information (libellé) vide.")
        if not s["code"].replace("_", "").isalnum():
            E("Signaux", r, f"code « {s['code']} » : lettres, chiffres et _ seulement.")
        if s["famille"] == "ES" and s["es"] not in ("ET", "ST", "EA", "SA"):
            E("Signaux", r, "un signal ES (E/S physique) doit avoir une nature ET, ST, EA ou SA.")
        incoherent = sens_incoherent(s["famille"], s["es"])
        if incoherent:
            E("Signaux", r, incoherent + ".")
        tor = s["famille"] in ("TS", "TC") or (s["famille"] == "ES" and s["es"] in ("ET", "ST"))
        if tor and s["type_logique"] not in ("BOOL", "EBOOL"):
            E("Signaux", r, f"{s['famille']} / {s['es']} : information tout-ou-rien, type logique BOOL ou EBOOL attendu.")
        if (s["es"] in ("EA", "SA") or s["famille"] in ("TM", "TR", "RTR", "CP")) and s["type_logique"] in ("BOOL", "EBOOL"):
            E("Signaux", r, f"{s['famille']} / {s['es']} : valeur numérique, type logique INT, DINT ou REAL attendu.")
        if s["presence"] == "Option":
            if not s["option"]:
                E("Signaux", r, "présence Option sans nom d'option.")
            elif s["type"] in options and s["option"] not in options[s["type"]]:
                A("Signaux", r, f"option « {s['option']} » absente de la liste du type {s['type']} (onglet Types) : "
                                "elle sera tout de même proposée sur les équipements de ce type.")
        elif s["option"]:
            A("Signaux", r, f"option « {s['option']} » renseignée mais présence {s['presence']} : elle est ignorée.")
        if s["source"] and s["source"] not in {f"{x['famille']}_{x['code']}" for x in nouveau["signaux"] if x["type"] == s["type"]}:
            E("Signaux", r, f"source physique {s['source']} inconnue pour le type {s['type']}.")

    # --- règles
    cles_type: dict[str, set[str]] = {}
    for s in nouveau["signaux"]:
        if not s["_portee"]:
            cles_type.setdefault(s["type"], set()).add(f"{s['famille']}_{s['code']}")
    proposes = set()
    for g in nouveau["regles"]:
        r = g["_r"]
        _dans(lect, "Règles", r, "Mode", g["mode"], MODES, vide_ok=False)
        if g["type"] != "*" and g["type"] not in types:
            E("Règles", r, f"type {g['type']} absent de l'onglet Types.")
            continue
        if not g["si"] or not g["propose"]:
            E("Règles", r, "« Si » et « Propose » sont obligatoires.")
        _dans(lect, "Règles", r, "Gouvernance", g["gouvernance"], GOUVERNANCES)
        if g["mode"] == "proposition" and not g["logique"] and not g["gouvernance"]:
            E("Règles", r, "une règle en mode proposition doit décrire la logique automate ou porter une "
                           "gouvernance (justification).")
        if g["type"] == "*":
            if not all(c.endswith("_*") for c in g["si"] + g["propose"]):
                E("Règles", r, "règle générale (type *) : clés de la forme FAMILLE_* attendues.")
            continue
        connus = cles_type.get(g["type"], set())
        for c in g["si"] + g["propose"]:
            if c not in connus:
                E("Règles", r, f"{c} n'existe pas dans le type {g['type']} (onglet Signaux).")
        for c in g["propose"]:
            proposes.add((g["type"], c))
    for s in nouveau["signaux"]:
        if s["presence"] == "Règle" and not s["_portee"]:
            cle = (s["type"], f"{s['famille']}_{s['code']}")
            generale = any(g["type"] == "*" and f"{s['famille']}_*" in g["propose"] for g in nouveau["regles"])
            if cle not in proposes and not generale:
                E("Signaux", s["_r"], f"présence Règle mais aucune règle ne propose {cle[1]} : il ne serait jamais généré.")
    # suppression d'un élément encore référencé
    ids_sup = {(s["type"], f"{s['famille']}_{s['code']}") for s in sup["signaux"] if not s["_portee"]}
    for g in nouveau["regles"]:
        for c in g["si"] + g["propose"]:
            if (g["type"], c) in ids_sup:
                E("Règles", g["_r"], f"{c} est marqué Supprimer dans Signaux mais la règle {g['id']} l'utilise.")
    for t in sup["types"]:
        if any(s["type"] == t["code"] for s in nouveau["signaux"]):
            E("Types", t["_r"], f"type {t['code']} marqué Supprimer mais il a encore des signaux.")

    # --- modèles
    for m in nouveau["modeles"]:
        if m["type"] not in types_m and m["type"] not in types:
            E("Modèles", m["_r"], f"type {m['type']} inconnu (onglets Types ou Types de modèles).")
        _dans(lect, "Modèles", m["_r"], "Statut", m["statut"], _modeles.STATUTS_MODELE, vide_ok=False)
    suffixes: dict[tuple[str, str, str], int] = {}
    for l in nouveau["lignes"]:
        r = l["_r"]
        if l["_modele"] not in modeles:
            E("Lignes de modèles", r, f"modèle « {l['_modele']} » absent de l'onglet Modèles (ou marqué Supprimer).")
        try:
            _modeles.verifier_ligne({k: l[k] for k in ("role", "libelle", "suffixe", "format", "unite", "commentaire")})
        except Exception as exc:                       # noqa: BLE001 — message métier de modeles.py
            E("Lignes de modèles", r, str(exc))
        k = (l["_modele"], l["role"], l["suffixe"])
        if k in suffixes:
            E("Lignes de modèles", r, f"{l['role']}_{l['suffixe']} déjà défini ligne {suffixes[k]} pour ce modèle.")
        suffixes.setdefault(k, r)
    for m in sup["modeles"]:
        if any(l["_modele"] == m["nom"] for l in nouveau["lignes"]):
            E("Modèles", m["_r"], f"modèle « {m['nom']} » marqué Supprimer mais il a encore des lignes.")
    return lect


# ============================================================================ construction et différences
def construire(nouveau, actuel_catalogue, actuel_modeles):
    """(Catalogue, référentiel des modèles) issus du classeur contrôlé. Rien n'est écrit."""
    signaux_type = sorted([s for s in nouveau["signaux"] if not s["_portee"]], key=lambda s: s["_o"])
    cat = Catalogue([{k: t[k] for k in CHAMPS_TYPE} for t in nouveau["types"]],
                    [{k: s[k] for k in CHAMPS_SIGNAL} for s in signaux_type], actuel_catalogue.version,
                    [{k: g[k] for k in CHAMPS_REGLE} for g in sorted(nouveau["regles"], key=lambda g: g["_o"])])
    ref = {"version": actuel_modeles.get("version", ""), "origine": actuel_modeles.get("origine", ""),
           "types": {}, "modeles": {},
           "lexique": (copy.deepcopy(actuel_modeles.get("lexique", [])) if nouveau.get("lexique") is None
                       else [{k: e[k] for k in CHAMPS_LEXIQUE} for e in nouveau["lexique"]]),
           "dictionnaire_es": (copy.deepcopy(actuel_modeles.get("dictionnaire_es", []))
                               if nouveau.get("dictionnaire_es") is None
                               else [{k: e[k] for k in CHAMPS_DICTIONNAIRE} for e in nouveau["dictionnaire_es"]]),
           "correspondances": (copy.deepcopy(actuel_modeles.get("correspondances", []))
                               if nouveau.get("correspondances") is None
                               else [{k: c[k] for k in CHAMPS_CORRESPONDANCE} for c in nouveau["correspondances"]])}
    anciens = actuel_modeles.get("modeles", {})
    for t in nouveau["types_modeles"]:
        ancien_type = actuel_modeles.get("types", {}).get(t["code"], {})
        type_modele = copy.deepcopy(ancien_type)
        type_modele.update(code=t["code"], designation=t["designation"], domaine=t["domaine"], modeles=[])
        if t.get("archive") is not None and (t["archive"] or "archive" in ancien_type):
            type_modele["archive"] = bool(t["archive"])
        ref["types"][t["code"]] = type_modele
    for m in sorted(nouveau["modeles"], key=lambda m: m["_o"]):
        base = copy.deepcopy(anciens.get(m["nom"], {}))
        base.update({"nom": m["nom"], "type": m["type"], "statut": m["statut"], "lignes": []})
        propres = sorted([s for s in nouveau["signaux"] if s["_portee"] == m["nom"]], key=lambda s: s["_o"])
        if propres:
            base["signaux"] = [{k: s[k] for k in CHAMPS_SIGNAL} for s in propres]
        elif "signaux" in base:
            base["signaux"] = []
        else:
            base.pop("signaux", None)
        ref["modeles"][m["nom"]] = base
        if m["type"] not in ref["types"]:
            ref["types"][m["type"]] = {"code": m["type"], "designation": "", "domaine": "", "modeles": []}
        ref["types"][m["type"]]["modeles"].append(m["nom"])
    for l in sorted(nouveau["lignes"], key=lambda l: l["_o"]):
        if l["_modele"] in ref["modeles"]:
            ref["modeles"][l["_modele"]]["lignes"].append(
                {"id": l["id"] or uuid.uuid4().hex[:8], **{k: l[k] for k in CHAMPS_LIGNE if k != "id"}})
    return cat, ref


def differences(actuel, propose, ouvrages_par_type=None):
    """[{objet, id, action, champs: {champ: [avant, après]}, consequence}] entre deux états normalisés."""
    ouvrages_par_type = ouvrages_par_type or {}
    sortie = []

    def comparer(objet, avant, apres, cle, type_de=None):
        a = {cle(x): x for x in avant}
        b = {cle(x): x for x in apres}
        ordre_b = {k: i for i, k in enumerate(b)}
        for k in b:
            if k not in a:
                sortie.append({"objet": objet, "id": k, "action": "ajout", "champs": {}})
        for k in a:
            if k not in b:
                sortie.append({"objet": objet, "id": k, "action": "suppression", "champs": {}})
        for k in a:
            if k in b:
                ch = {c: [a[k].get(c), b[k].get(c)] for c in set(a[k]) | set(b[k])
                      if not c.startswith("_") and a[k].get(c) != b[k].get(c)}
                if ch:
                    sortie.append({"objet": objet, "id": k, "action": "modification", "champs": ch})
        # ordre relatif (influence l'ordre de génération et d'adressage)
        communs_a = [k for k in a if k in b]
        communs_b = sorted(communs_a, key=lambda k: ordre_b[k])
        if objet == "signal" and communs_a != communs_b:
            deplaces = [k for i, k in enumerate(communs_b) if communs_a[i] != k]
            sortie.append({"objet": objet, "id": f"{len(deplaces)} signal(aux)", "action": "ordre",
                           "champs": {"ordre": [", ".join(deplaces[:3]), "nouvel ordre de génération"]}})
        for d in sortie:
            if d["objet"] == objet and type_de and "consequence" not in d:
                t = type_de(d["id"])
                n = ouvrages_par_type.get(t, 0)
                d["consequence"] = (f"{n} ouvrage(s) enregistré(s) utilisent le type {t} : ils gardent leur référentiel "
                                    "figé ; ils n'adoptent cette révision que sur décision." if n else "")
    sig = lambda e: [dict(s) for s in e["signaux"]]
    comparer("type", actuel["types"], propose["types"], lambda t: t["code"], lambda k: k)
    comparer("signal", sig(actuel), sig(propose), id_signal, lambda k: k.split(".")[0].split("[")[0])
    comparer("règle", actuel["regles"], propose["regles"], lambda g: g["id"],
             lambda k: next((g["type"] for g in actuel["regles"] + propose["regles"] if g["id"] == k), ""))
    comparer("type de modèles", actuel["types_modeles"], propose["types_modeles"], lambda t: t["code"])
    comparer("modèle", [{k: v for k, v in m.items() if k != "_avec_signaux"} for m in actuel["modeles"]],
             [{k: v for k, v in m.items() if k != "_avec_signaux"} for m in propose["modeles"]], lambda m: m["nom"])
    comparer("ligne de modèle", actuel["lignes"], [l for l in propose["lignes"]], lambda l: l["id"] or l["libelle"])
    comparer("entrée de lexique", actuel.get("lexique", []), propose.get("lexique") or [],
             lambda e: _lexique.normaliser(e["mot"]))
    comparer("code du dictionnaire des E/S", actuel.get("dictionnaire_es", []), propose.get("dictionnaire_es") or [],
             _dico.cle)
    comparer("correspondance", actuel.get("correspondances", []), propose.get("correspondances") or [],
             lambda c: f"{c['type']}.{c['ancienne']}")
    for d in sortie:
        d.setdefault("consequence", "")
    return sortie


# Les révisions (brouillon, validation, publication, historique) sont gérées par genvar/referentiel_depot.py :
# ce module ne fait que lire, contrôler, comparer et écrire des classeurs.


# ============================================================================ ouvrages concernés
def ouvrages_par_type():
    """{type: nombre d'ouvrages enregistrés qui l'utilisent} (lecture seule des fichiers de projets)."""
    compte: dict[str, int] = {}
    try:
        from . import projets
        for f in projets.lister():
            try:
                with open(f.chemin, encoding="utf-8") as h:
                    d = json.load(h)
            except (OSError, ValueError):
                continue
            for t in {e.get("type") for e in d.get("ouvrage", d).get("equipements", [])}:
                compte[t] = compte.get(t, 0) + 1
    except Exception:                                   # noqa: BLE001 — information de confort, jamais bloquante
        return {}
    return compte
