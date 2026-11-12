"""Application explicite d'une prévisualisation à une COPIE en mémoire.

Aucune écriture fichier : l'ouvrage initial et son fichier restent intacts,
y compris si une opération échoue au milieu de l'import.
"""
from __future__ import annotations

import copy

from genvar.modele import Equipement, VariableExistante
from genvar.session import RegleMetier, Session

from .schemas import ImportPreview, InputKind, InboundError, RowAction, StagedImport
from .validation import preview_import, session_digest


def _apply_inventory(session: Session, rows: list[dict[str, str]]) -> int:
    count = 0
    for row in rows:
        se = row["sous_ensemble"]
        if not any(s.code == se for s in session.ouvrage.sous_ensembles):
            session.ajouter_sous_ensemble(se)
        eq = Equipement(sous_ensemble=se, type=row["type_normalise"],
                        numero=row["numero"], libelle=row.get("libelle", "")[:32],
                        modele=row.get("modele_valide", ""))
        session.ajouter_equipement(eq)
        count += 1
    return count


def _apply_variables(session: Session, rows: list[dict[str, str]]) -> int:
    for row in rows:
        session.ouvrage.existantes.append(VariableExistante(
            nom=row["nom"], type_logique=row.get("type", ""),
            adresse=row.get("adresse", ""), commentaire=row.get("commentaire", "")))
    if rows:
        session._change()
    return len(rows)


def _apply_io(session: Session, rows: list[dict[str, str]]) -> int:
    keys = ("nom", "adresse", "equipement", "fonction", "commentaire", "variable_liee")
    for row in rows:
        # Dictionnaire JSON sérialisable : pris en charge par le modèle Ouvrage.
        session.ouvrage.entrees_physiques_importees.append({k: row.get(k, "") for k in keys})
    if rows:
        session._change()
    return len(rows)


def stage_import(preview: ImportPreview, session: Session, *, confirmed: bool = False) -> StagedImport:
    """Retourne une copie enrichie ; n'écrit et ne modifie JAMAIS `session`.

    Préconditions : confirmation explicite, aucune erreur, empreinte de projet
    inchangée, source inchangée et contrôle complet de l'aperçu au moment d'appliquer.
    """
    if not confirmed:
        raise InboundError("Validation explicite requise avant l'intégration en mémoire.")
    if preview.schema_version != 1:
        raise InboundError("Version d'aperçu inconnue.")
    if preview.errors:
        raise InboundError(f"Import refusé : {len(preview.errors)} erreur(s) bloquante(s).")
    if preview.session_digest != session_digest(session):
        raise InboundError("Le projet ou le référentiel a changé depuis l'aperçu : recommencer la prévisualisation.")
    # Double validation : un aperçu forgé ou édité, une source modifiée ou un
    # changement de règle ne peuvent pas être appliqués silencieusement.
    fresh = preview_import(preview.path, preview.kind, session, sheet=preview.sheet)
    if fresh != preview:
        raise InboundError("Le fichier ou la prévisualisation a changé : refaire l'analyse.")
    to_create = [dict(row.values) for row in fresh.rows if row.action == RowAction.CREATE]
    # Aucune modification en cas d'échec. Le caller choisit ensuite quoi faire
    # de la copie ; surtout ne PAS réutiliser automatiquement session.chemin.
    copy_session = copy.deepcopy(session)
    copy_session.chemin = None
    try:
        if fresh.kind == InputKind.INVENTORY:
            created = _apply_inventory(copy_session, to_create)
        elif fresh.kind == InputKind.PLC_VARIABLES:
            created = _apply_variables(copy_session, to_create)
        elif fresh.kind == InputKind.PHYSICAL_IO:
            created = _apply_io(copy_session, to_create)
        else:
            raise InboundError("Nature d'import inconnue.")
    except (RegleMetier, ValueError, KeyError, TypeError) as exc:
        raise InboundError(f"Intégration annulée en mémoire : {exc}") from exc
    if created != len(to_create):
        raise InboundError("Nombre de lignes intégrées incohérent : copie rejetée.")
    return StagedImport(copy_session, fresh.kind, created,
                        sum(row.action == RowAction.ALREADY_EXISTS for row in fresh.rows),
                        fresh.source_digest)
