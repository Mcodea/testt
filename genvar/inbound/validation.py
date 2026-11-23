"""Validation métier et confrontation non destructives avec la session OGIAS."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from genvar import import_sources, inventaire
from genvar.session import Session
from genvar.modeles import code_type
from genvar.rapprochement import normaliser as normaliser_io

from .normalization import choose_table, get_values
from .readers import read_source
from .schemas import (Diagnostic, ImportPreview, InputKind, InboundError,
                      PreviewRow, RowAction, Severity, SourceRow)


def session_digest(session: Session) -> str:
    """Empreinte d'état incluant l'ouvrage et les référentiels actifs.

    Ne contient pas le chemin du projet : une opération de prévisualisation ne
    saurait transformer un projet ni modifier sa localisation.
    """
    o = session.ouvrage
    data = {"ouvrage": o.vers_dict(), "modeles": session.modeles,
            "catalogue": {"types": session.catalogue.types,
                          "signaux": session.catalogue.signaux,
                          "regles": session.catalogue.regles,
                          "version": session.catalogue.version}}
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _diag(code: str, message: str, severity: Severity, row: SourceRow) -> Diagnostic:
    return Diagnostic(code, message, severity, row.sheet, row.line)


def _row_issue(row: SourceRow, values: dict[str, str]) -> list[Diagnostic]:
    issues: list[Diagnostic] = []
    if row.formula_columns:
        issues.append(_diag("FORMULE_EXCEL", "Formule Excel détectée : ne pas calculer ni importer une formule.",
                            Severity.ERROR, row))
    if any(value.lstrip().startswith("=") for value in values.values()):
        if not row.formula_columns:
            issues.append(_diag("FORMULE_TEXTE", "Valeur ressemblant à une formule : refus prudent.",
                                Severity.ERROR, row))
    return issues


def _ogias(row: SourceRow, rep: str, o, issues: list) -> tuple:
    """Repère à la charte OGIAS (formats historiques) : (sous-ensemble, fin) ; (None, None) si rejet immédiat."""
    charte = o.format_repere == "12"
    if not inventaire.RE_REPERE.fullmatch(rep):
        issues.append(_diag("REPERE_FORMAT", "Repère invalide : 12 ou 14 caractères alphanumériques attendus.",
                            Severity.ERROR, row))
        return None, None
    if charte and len(rep) != 12:
        issues.append(_diag("CHARTE_12", "La charte de cet ouvrage requiert 12 caractères ; aucun recodage automatique.",
                            Severity.ERROR, row))
    prefix, se, end = inventaire.decouper_repere(rep, charte)
    if not o.lieu or not o.code_ouvrage or (charte and not o.numero_ouvrage):
        issues.append(_diag("OUVRAGE_NON_IDENTIFIE", "Identifier le lieu, le type et le numéro de l'ouvrage avant l'import.",
                            Severity.ERROR, row))
    elif prefix != o.prefixe():
        issues.append(_diag("AUTRE_OUVRAGE", f"Préfixe {prefix} différent de {o.prefixe()} : refus.",
                            Severity.ERROR, row))
    return se, end


def _inventory(row: SourceRow, values: dict[str, str], session: Session,
               seen: dict[str, SourceRow]) -> PreviewRow:
    o = session.ouvrage
    issues = _row_issue(row, values)
    rep = values.get("repere", "").upper()
    values = {**values, "repere": rep}
    if not rep:
        issues.append(_diag("REPERE_ABSENT", "Ligne renseignée sans repère d'équipement.", Severity.ERROR, row))
        return PreviewRow(row, values, RowAction.REJECT, tuple(issues))
    if rep in seen:
        first = seen[rep]
        issues.append(_diag("REPERE_REPETE", f"Repère répété : déjà déclaré ligne {first.line} ({first.sheet}).",
                            Severity.ERROR, row))
    else:
        seen[rep] = row
    c = o.charte_client()
    if c is not None:                                 # 19/11 : repère relu selon la charte du client
        from genvar import charte as chartes
        lu = chartes.decouper(c, o, rep)
        if isinstance(lu, str):
            code = ("AUTRE_OUVRAGE" if lu.startswith("autre ouvrage") else
                    "OUVRAGE_NON_IDENTIFIE" if lu.startswith("ouvrage non identifié") else "REPERE_FORMAT")
            issues.append(_diag(code, lu[0].upper() + lu[1:] + ".", Severity.ERROR, row))
            return PreviewRow(row, values, RowAction.REJECT, tuple(issues))
        se, end = lu
    else:
        se, end = _ogias(row, rep, o, issues)
        if se is None:
            return PreviewRow(row, values, RowAction.REJECT, tuple(issues))
    known = set(session.modeles["types"]) | {t["code"] for t in session.catalogue.types}
    supplied = code_type(values.get("type", ""))
    typ, num = inventaire._type_depuis_repere(end, [supplied] if supplied else known)
    if not typ or typ not in known or not num or num == "00":
        issues.append(_diag("TYPE_NUMERO_INCONNU", "Type ou numéro absent/incompatible avec le repère et le référentiel.",
                            Severity.ERROR, row))
    values = {**values, "sous_ensemble": se, "type_normalise": typ or "", "numero": num or ""}
    if supplied and typ != supplied:
        issues.append(_diag("TYPE_CONTRADICTOIRE", "Le type indiqué ne correspond pas au repère.", Severity.ERROR, row))
    modele = values.get("modele", "")
    model_requested = bool(modele)
    t = session.modeles["types"].get(typ or "", {})
    choices = t.get("modeles", [])
    if modele and modele not in choices:
        issues.append(_diag("MODELE_INCONNU", f"Modèle « {modele} » non référencé : choisir un modèle dans OGIAS.",
                            Severity.WARNING, row))
        modele = ""
    if not modele and not model_requested and len(choices) == 1:
        modele = choices[0]
    if not modele and len(choices) > 1:
        issues.append(_diag("MODELE_A_CHOISIR", "Plusieurs modèles possibles ; sélectionner dans l'inventaire.",
                            Severity.WARNING, row))
    values = {**values, "modele_valide": modele}
    if len(values.get("libelle", "")) > 32:
        issues.append(_diag("LIBELLE_TROP_LONG", "Désignation supérieure à 32 caractères : correction requise avant import.",
                            Severity.ERROR, row))
    existing = {o.repere(eq): eq for eq in o.equipements}.get(rep)
    if existing is not None:
        if values.get("libelle", "") and existing.libelle != values["libelle"]:
            issues.append(_diag("LIBELLE_DIFFERENT", "Libellé différent : équipement existant conservé sans modification.",
                                Severity.WARNING, row))
        action = RowAction.ALREADY_EXISTS
    else:
        action = RowAction.CREATE
    if any(i.severity == Severity.ERROR for i in issues):
        action = RowAction.REJECT
    return PreviewRow(row, values, action, tuple(issues))


def _adresses_validees(eq) -> bool:
    """Vrai si l'équipement porte une adresse d'échange ou une E/S validée : protégé contre l'import."""
    return bool(eq.validees) or any(isinstance(m, dict) and m.get("validee") for m in (eq.es_meta or {}).values())


CHAMPS_ALLER_RETOUR = (("libelle", "libelle", "Désignation"), ("modele", "modele", "Modèle"),
                       ("uf", "uf", "UF"), ("local", "local", "Local"))


def _sync(row: SourceRow, values: dict[str, str], session: Session,
          seen: dict[str, SourceRow]) -> PreviewRow:
    """Aller-retour (19/11) : la ligne est lue comme un inventaire, puis comparée à l'équipement existant.

    Cellule vide ou colonne absente : valeur conservée (jamais d'effacement implicite). Le repère est la clé ; il
    ne se modifie pas par fichier (l'identifiant OGIAS sert à le détecter). Un changement de modèle est refusé sur
    un équipement dont des adresses sont validées (elles ne bougent jamais par import)."""
    base = _inventory(row, values, session, seen)
    if base.action != RowAction.ALREADY_EXISTS:
        ident = str(values.get("ident", "")).strip()
        connu = next((e for e in session.ouvrage.equipements if e.ident == ident), None) if ident else None
        if connu is not None:
            issue = _diag("REPERE_MODIFIE", f"Le repère de l'équipement {session.ouvrage.repere(connu)} a été modifié dans "
                          "le fichier : renommez-le dans OGIAS (les noms et adresses en dépendent).", Severity.ERROR, row)
            return PreviewRow(row, base.values, RowAction.REJECT, (*base.diagnostics, issue))
        return base
    o = session.ouvrage
    vals = dict(base.values)
    eq = next(e for e in o.equipements if o.repere(e) == vals["repere"])
    issues = [d for d in base.diagnostics if d.code not in ("LIBELLE_DIFFERENT", "MODELE_INCONNU", "MODELE_A_CHOISIR")]
    ident = str(vals.get("ident", "")).strip()
    if ident and ident != eq.ident:
        issues.append(_diag("IDENTIFIANT_DIFFERENT", "L'identifiant OGIAS ne correspond pas à ce repère : ligne copiée "
                            "d'un autre équipement ? Corrigez le fichier.", Severity.ERROR, row))
    changements = []
    for cle, attribut, nom in CHAMPS_ALLER_RETOUR:
        nouveau = str(vals.get(cle, "")).strip()
        if not nouveau or nouveau == (getattr(eq, attribut) or ""):
            continue
        if cle == "modele":
            t = session.modeles["types"].get(eq.type, {})
            if nouveau not in t.get("modeles", []):
                issues.append(_diag("MODELE_INCONNU", f"Modèle « {nouveau} » absent du type {eq.type} dans le référentiel.",
                                    Severity.ERROR, row))
                continue
            if _adresses_validees(eq):
                issues.append(_diag("MODELE_ADRESSES_VALIDEES", "Changement de modèle refusé : l'équipement a des adresses "
                                    "validées (elles ne bougent jamais par import). Changez le modèle dans OGIAS.",
                                    Severity.ERROR, row))
                continue
        if cle == "uf" and nouveau not in {u.code for u in o.unites}:
            issues.append(_diag("UF_INCONNUE", f"Unité fonctionnelle « {nouveau} » absente de l'ouvrage : créez-la d'abord.",
                                Severity.ERROR, row))
            continue
        changements.append((attribut, nom, getattr(eq, attribut) or "", nouveau))
    # Attributs de l'atelier (lot 4) : contrôlés selon leur définition ; cellule vide = valeur conservée
    from genvar import attributs
    for cle in [k for k in vals if k.startswith("attr:")]:
        code, brut = cle[5:], str(vals.get(cle, "")).strip()
        if not brut or brut == "—":                    # « — » : sans objet pour ce type (écrit par l'export)
            continue
        a = attributs.trouver(code)
        if a is None or a.get("archive") or (a.get("types") and eq.type not in a["types"]):
            issues.append(_diag("ATTRIBUT_NON_APPLICABLE", f"Attribut {code} inconnu, archivé ou sans objet pour le type "
                                f"{eq.type}.", Severity.ERROR, row))
            continue
        try:
            v = attributs.valider(a, brut)
        except attributs.AttributRefuse as exc:
            issues.append(_diag("ATTRIBUT_INVALIDE", str(exc), Severity.ERROR, row))
            continue
        if v != (eq.attributs or {}).get(code, ""):
            changements.append((cle, a["nom"], (eq.attributs or {}).get(code, ""), v))
    vals["ident_eq"] = eq.ident
    vals["changements"] = " ; ".join(f"{nom} : « {avant} » → « {apres} »" for _, nom, avant, apres in changements)
    vals["_modifs"] = json.dumps({a: apres for a, _, _, apres in changements}, ensure_ascii=False, sort_keys=True)
    if any(i.severity == Severity.ERROR for i in issues):
        action = RowAction.REJECT
    else:
        action = RowAction.UPDATE if changements else RowAction.ALREADY_EXISTS
    return PreviewRow(row, vals, action, tuple(issues))


def _obsoletes(session: Session, rows: list[PreviewRow]) -> tuple:
    """Équipements de l'ouvrage absents du fichier : gardés par défaut ; protégés si des adresses sont validées."""
    o = session.ouvrage
    presents = {str(r.values.get("repere", "")).upper() for r in rows if r.action != RowAction.EMPTY}
    sortie = []
    for e in o.equipements:
        rep = o.repere(e)
        if rep in presents:
            continue
        protege = _adresses_validees(e)
        sortie.append({"ident": e.ident, "repere": rep, "libelle": e.libelle, "protege": protege,
                       "motif": "adresses validées : suppression impossible par import" if protege else ""})
    return tuple(sorted(sortie, key=lambda x: x["repere"]))


def _variable(row: SourceRow, values: dict[str, str], session: Session,
              seen: dict[str, SourceRow]) -> PreviewRow:
    issues = _row_issue(row, values)
    nom = values.get("nom", "")
    if session.ouvrage.mode != "Existant":
        issues.append(_diag("MODE_PROJET", "Les variables historiques s'importent uniquement en mode Existant.",
                            Severity.ERROR, row))
    if not nom or not import_sources.SYMBOL.fullmatch(nom):
        issues.append(_diag("NOM_VARIABLE", "Nom de variable absent ou invalide.", Severity.ERROR, row))
    key = nom.casefold()
    if key in seen:
        issues.append(_diag("VARIABLE_REPETEE", f"Variable répétée (ligne {seen[key].line}).", Severity.ERROR, row))
    else:
        seen[key] = row
    adresse = values.get("adresse", "")
    typ = values.get("type", "")
    if not adresse:
        issues.append(_diag("ADRESSE_MANQUANTE", "Adresse absente : confirmer le mode d'acquisition.",
                            Severity.WARNING, row))
    if not typ:
        issues.append(_diag("TYPE_VARIABLE_MANQUANT", "Type logique non renseigné.", Severity.WARNING, row))
    existing = next((v for v in session.ouvrage.existantes if v.nom.casefold() == key), None)
    if existing:
        if (existing.nom, existing.type_logique, existing.adresse, existing.commentaire) != (
                nom, typ, adresse, values.get("commentaire", "")):
            issues.append(_diag("SOURCE_VARIABLE_MODIFIEE", "Variable déjà importée avec des données différentes : décision manuelle requise.",
                                Severity.ERROR, row))
        action = RowAction.ALREADY_EXISTS
    else:
        action = RowAction.CREATE
    if any(i.severity == Severity.ERROR for i in issues):
        action = RowAction.REJECT
    return PreviewRow(row, values, action, tuple(issues))


def _io(row: SourceRow, values: dict[str, str], session: Session,
        seen: dict[str, SourceRow]) -> PreviewRow:
    issues = _row_issue(row, values)
    if session.ouvrage.mode != "Existant":
        issues.append(_diag("MODE_PROJET", "Une liste E/S historique s'importe en mode Existant.",
                            Severity.ERROR, row))
    nom = values.get("nom", "")
    equip = values.get("equipement", "")
    fonction = values.get("fonction", "")
    if not nom or not equip or not fonction:
        issues.append(_diag("ES_CHAMPS_ABSENTS", "Nom, équipement et fonction sont obligatoires.",
                            Severity.ERROR, row))
    key = normaliser_io(nom)
    if key in seen:
        issues.append(_diag("ES_REPETEE", f"Point E/S déjà déclaré ligne {seen[key].line}.", Severity.ERROR, row))
    else:
        seen[key] = row
    saved = next((p for p in session.ouvrage.entrees_physiques_importees
                  if normaliser_io(p.get("nom", "") if isinstance(p, dict) else p.nom) == key), None)
    if saved is not None:
        existing = saved if isinstance(saved, dict) else vars(saved)
        if any(str(existing.get(field, "")) != values.get(field, "")
               for field in ("nom", "adresse", "equipement", "fonction", "commentaire", "variable_liee")):
            issues.append(_diag("ES_SOURCE_MODIFIEE", "Point E/S déjà importé avec des données différentes : contrôle requis.",
                                Severity.ERROR, row))
        action = RowAction.ALREADY_EXISTS
    else:
        action = RowAction.CREATE
    if any(i.severity == Severity.ERROR for i in issues):
        action = RowAction.REJECT
    return PreviewRow(row, values, action, tuple(issues))


def preview_import(path: str | Path, kind: InputKind | str, session: Session,
                   *, sheet: str | None = None, profil: dict | None = None) -> ImportPreview:
    """Prévisualise sans écrire. Une anomalie bloquante interdit toute intégration."""
    try:
        kind = InputKind(kind)
    except ValueError as exc:
        raise InboundError("Type d'import inconnu.") from exc
    source = read_source(path)
    table, header_index, mapping = choose_table(source, kind, sheet, profil)
    rows: list[PreviewRow] = []
    seen: dict[str, SourceRow] = {}
    validator = {InputKind.INVENTORY: _inventory, InputKind.EQUIPMENT_SYNC: _sync,
                 InputKind.PLC_VARIABLES: _variable,
                 InputKind.PHYSICAL_IO: _io}[kind]
    for raw in table.rows[header_index + 1:]:
        if not any(cell.strip() for cell in raw.cells):
            rows.append(PreviewRow(raw, {}, RowAction.EMPTY, (
                _diag("LIGNE_VIDE", "Ligne entièrement vide, comptabilisée sans import.", Severity.INFO, raw),)))
            continue
        values = get_values(raw.cells, mapping)
        if not any(values.values()):
            rows.append(PreviewRow(raw, values, RowAction.REJECT, (
                _diag("COLONNES_NON_MAPPEES", "Données présentes hors des colonnes identifiées.", Severity.ERROR, raw),)))
            continue
        rows.append(validator(raw, values, session, seen))
    global_issues = list(source.notices)
    if header_index:
        global_issues.append(Diagnostic("LIGNES_AVANT_ENTETE",
                          f"{header_index} ligne(s) d'introduction avant l'en-tête (non importées).",
                          Severity.INFO, table.name, table.rows[header_index].line))
    excluded = [t.name for t in source.tables if t.name != table.name]
    if excluded:
        global_issues.append(Diagnostic("FEUILLES_NON_SELECTIONNEES",
                           "Feuilles non importées : " + ", ".join(excluded), Severity.INFO))
    if not rows or not any(r.action != RowAction.EMPTY for r in rows):
        global_issues.append(Diagnostic("AUCUNE_DONNEE", "Aucune donnée importable.", Severity.ERROR,
                                        table.name, 0))
    obsoletes = _obsoletes(session, rows) if kind == InputKind.EQUIPMENT_SYNC else ()
    return ImportPreview(kind, source.path, source.digest, session_digest(session),
                         table.name, tuple(rows), tuple(global_issues), obsoletes=obsoletes)
