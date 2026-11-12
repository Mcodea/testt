"""Écriture d'un classeur Excel (.xlsx) sans bibliothèque externe.

Un fichier .xlsx est un dossier zippé de fichiers XML. On n'écrit ici que le
nécessaire : plusieurs feuilles, une ligne d'en-tête mise en forme, des
largeurs de colonnes, un filtre automatique et la première ligne figée.
"""

import re
import zipfile
from xml.sax.saxutils import escape

# Caractères interdits en XML 1.0 : écrits tels quels, ils rendent le classeur illisible par Excel.
# Ils sont remplacés par U+FFFD (caractère de remplacement, visible) plutôt que supprimés en silence.
_INTERDITS_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")
# Date fixe des membres de l'archive : même contenu → mêmes octets (empreintes SHA-256 reproductibles).
DATE_ZIP = (1980, 1, 1, 0, 0, 0)


def _texte_xml(valeur):
    return escape(_INTERDITS_XML.sub("\ufffd", str(valeur)))


def ecrire_membre(z, nom, contenu):
    """Membre d'archive zip à date fixe (octets reproductibles)."""
    info = zipfile.ZipInfo(nom, DATE_ZIP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    z.writestr(info, contenu)


def _col(n):
    """1 -> A, 27 -> AA."""
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _cellule(ref, valeur, style):
    st = f' s="{style}"' if style else ""
    if valeur is None or valeur == "":
        return f'<c r="{ref}"{st}/>'
    if isinstance(valeur, bool):
        valeur = "Oui" if valeur else ""
    if isinstance(valeur, (int, float)):
        return f'<c r="{ref}"{st}><v>{valeur}</v></c>'
    texte = _texte_xml(valeur).replace("\n", "&#10;")
    return f'<c r="{ref}"{st} t="inlineStr"><is><t xml:space="preserve">{texte}</t></is></c>'


def _feuille(entetes, lignes, largeurs):
    n_col = len(entetes)
    derniere = f"{_col(n_col)}{len(lignes) + 1}"
    x = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
         '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
         'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
         '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
         '</sheetView></sheetViews>',
         '<sheetFormatPr defaultRowHeight="15"/>', "<cols>"]
    for i, w in enumerate(largeurs, 1):
        x.append(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>')
    x.append("</cols><sheetData>")
    x.append('<row r="1">' + "".join(_cellule(f"{_col(i)}1", h, 1) for i, h in enumerate(entetes, 1)) + "</row>")
    for r, ligne in enumerate(lignes, 2):
        x.append(f'<row r="{r}">' + "".join(_cellule(f"{_col(i)}{r}", v, 2) for i, v in enumerate(ligne, 1)) + "</row>")
    x.append("</sheetData>")
    if lignes:
        x.append(f'<autoFilter ref="A1:{derniere}"/>')
    x.append('<pageMargins left="0.5" right="0.5" top="0.6" bottom="0.6" header="0.3" footer="0.3"/>')
    x.append('<pageSetup orientation="landscape" fitToHeight="0"/>')
    x.append("</worksheet>")
    return "".join(x)


STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="2"><font><sz val="10"/><name val="Calibri"/></font><font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF193854"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border>
<border><left style="thin"><color rgb="FFC9D3DC"/></left><right style="thin"><color rgb="FFC9D3DC"/></right>
<top style="thin"><color rgb="FFC9D3DC"/></top><bottom style="thin"><color rgb="FFC9D3DC"/></bottom><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment vertical="top"/></xf></cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""


def ecrire_xlsx(chemin, feuilles):
    """feuilles : liste de (nom, entêtes, lignes, largeurs)."""
    n = len(feuilles)
    types = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
             '<Default Extension="xml" ContentType="application/xml"/>',
             '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
             '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>']
    types += [f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
              for i in range(1, n + 1)]
    types.append("</Types>")
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>')
    classeur = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>']
    classeur += [f'<sheet name="{_texte_xml(nom[:31]).replace('"', '&quot;')}" sheetId="{i}" r:id="rId{i}"/>' for i, (nom, *_) in enumerate(feuilles, 1)]
    classeur.append("</sheets>")
    filtres = [f'<definedName name="_xlnm._FilterDatabase" localSheetId="{i - 1}" hidden="1">\'{_texte_xml(nom[:31]).replace("'", "''")}\'!$A$1:${_col(len(ent))}${len(lig) + 1}</definedName>'
               for i, (nom, ent, lig, _) in enumerate(feuilles, 1) if lig]
    if filtres:
        classeur.append("<definedNames>" + "".join(filtres) + "</definedNames>")
    classeur.append("</workbook>")
    rels_classeur = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                     '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    rels_classeur += [f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
                      for i in range(1, n + 1)]
    rels_classeur.append(f'<Relationship Id="rId{n + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>')
    rels_classeur.append("</Relationships>")

    with zipfile.ZipFile(chemin, "w", zipfile.ZIP_DEFLATED) as z:
        ecrire_membre(z, "[Content_Types].xml", "".join(types))
        ecrire_membre(z, "_rels/.rels", rels)
        ecrire_membre(z, "xl/workbook.xml", "".join(classeur))
        ecrire_membre(z, "xl/_rels/workbook.xml.rels", "".join(rels_classeur))
        ecrire_membre(z, "xl/styles.xml", STYLES)
        for i, (nom, entetes, lignes, largeurs) in enumerate(feuilles, 1):
            ecrire_membre(z, f"xl/worksheets/sheet{i}.xml", _feuille(entetes, lignes, largeurs))


def exporter_table(chemin, ouvrage, catalogue, variables, anomalies, points=()):
    """Table d'échange de l'ouvrage : variables, entrées-sorties, contrôles."""
    from .modele import registre_modbus, zone, ORDRE_ZONES
    v_ent = ["Repère", "Sous-ensemble", "Équipement", "Information", "Famille", "Nom de variable", "Type",
             "Adresse", "Adresse validée", "Registre Modbus", "Unité", "Alarme", "Commentaire automate", "Libellé Topkapi",
             "Point E/S", "Variable d'E/S", "Origine", "UF", "Logique automate à programmer"]
    v_lig = [[v.repere, ouvrage.libelle_sous_ensemble(ouvrage.equipement(v.ident_eq).sous_ensemble),
              v.designation, v.information, v.famille, v.nom, v.type_logique, v.adresse,
              "Oui" if v.adresse_validee else ("Proposée" if v.adresse else ""),
              registre_modbus(v.adresse, ouvrage.decalage_modbus), v.unite,
              "Oui" if v.alarme else "", v.commentaire, v.libelle_topkapi, v.es, v.nom_es, v.origine, v.uf,
              v.logique] for v in variables]
    es_ent = ["Repère", "Point", "Nom de l'E/S", "Type", "Adresse physique", "Dans le XSY", "Variable d'échange", "Commentaire"]
    es_lig = [[p.repere, p.point, p.nom, p.type_logique, p.adresse, "Oui" if p.adresse else "Non : sans adresse",
               p.variable or "(E/S locale)", p.commentaire] for p in points]
    c_ent = ["Niveau", "Repère", "Message"]
    c_lig = [[a.niveau, a.repere, a.message] for a in anomalies]
    o_ent = ["Rubrique", "Valeur"]
    o_lig = [["Lieu", ouvrage.lieu], ["Ouvrage", ouvrage.code_ouvrage], ["Libellé", ouvrage.libelle],
             ["Automate", ouvrage.automate], ["Projet Control Expert", ouvrage.nom_projet],
             ["Lieu dans le nom des variables", "Oui" if ouvrage.lieu_dans_le_nom else "Non"]]
    o_lig += [[f"Plage {f}", "%MW{} à %MW{}".format(*zone(ouvrage, f))] for f in ORDRE_ZONES]
    o_lig += [["Registre Modbus", f"mot %MW + {ouvrage.decalage_modbus}"]]
    o_lig += [[f"Sous-ensemble {s.code}", s.libelle] for s in ouvrage.sous_ensembles]
    o_lig += [["Équipements", len(ouvrage.equipements)], ["Variables d'échange", len(variables)],
              ["Entrées-sorties", len(es_lig)], ["Erreurs", sum(1 for a in anomalies if a.niveau == "Erreur")],
              ["Alertes", sum(1 for a in anomalies if a.niveau == "Alerte")]]
    ecrire_xlsx(chemin, [
        ("Variables", v_ent, v_lig, [16, 18, 22, 28, 8, 26, 8, 11, 10, 10, 8, 7, 44, 36, 9, 26, 16, 8, 70]),
        ("Entrées-sorties", es_ent, es_lig, [16, 7, 26, 8, 14, 18, 26, 44]),
        ("Contrôles", c_ent, c_lig, [9, 16, 90]),
        ("Ouvrage", o_ent, o_lig, [30, 40]),
    ])
