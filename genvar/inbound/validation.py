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
    charte = o.format_repere == "12"
    if not inventaire.RE_REPERE.fullmatch(rep):
        issues.append(_diag("REPERE_FORMAT", "Repère invalide : 12 ou 14 caractères alphanumériques attendus.",
                            Severity.ERROR, row))
        return PreviewRow(row, values, RowAction.REJECT, tuple(issues))
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
                   *, sheet: str | None = None) -> ImportPreview:
    """Prévisualise sans écrire. Une anomalie bloquante interdit toute intégration."""
    try:
        kind = InputKind(kind)
    except ValueError as exc:
        raise InboundError("Type d'import inconnu.") from exc
    source = read_source(path)
    table, header_index, mapping = choose_table(source, kind, sheet)
    rows: list[PreviewRow] = []
    seen: dict[str, SourceRow] = {}
    validator = {InputKind.INVENTORY: _inventory,
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
    return ImportPreview(kind, source.path, source.digest, session_digest(session),
                         table.name, tuple(rows), tuple(global_issues))
