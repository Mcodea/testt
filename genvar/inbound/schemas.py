"""Contrats immuables du pipeline d'entrée OGIAS.

Aucun objet de ce module ne sait écrire un fichier ni modifier un ouvrage.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Mapping, TYPE_CHECKING

if TYPE_CHECKING:
    from genvar.session import Session


class InputKind(str, Enum):
    INVENTORY = "inventaire"
    PLC_VARIABLES = "variables_existantes"
    PHYSICAL_IO = "liste_es_existante"


class Severity(str, Enum):
    ERROR = "erreur"
    WARNING = "avertissement"
    INFO = "information"


class RowAction(str, Enum):
    CREATE = "a_creer"
    ALREADY_EXISTS = "deja_present"
    REJECT = "refuse"
    EMPTY = "ligne_vide"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    severity: Severity
    sheet: str = ""
    line: int = 0


@dataclass(frozen=True)
class SourceRow:
    sheet: str
    line: int
    cells: tuple[str, ...]
    formula_columns: tuple[int, ...] = ()


@dataclass(frozen=True)
class SourceTable:
    name: str
    rows: tuple[SourceRow, ...]


@dataclass(frozen=True)
class SourceData:
    path: Path
    digest: str
    tables: tuple[SourceTable, ...]
    notices: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True)
class PreviewRow:
    source: SourceRow
    values: Mapping[str, str]
    action: RowAction
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True)
class ImportPreview:
    """Résultat vérifiable d'une analyse sur une session et un fichier précis."""
    kind: InputKind
    path: Path
    source_digest: str
    session_digest: str
    sheet: str
    rows: tuple[PreviewRow, ...]
    diagnostics: tuple[Diagnostic, ...] = ()
    schema_version: int = 1

    def to_report(self, *, include_rows: bool = True, offset: int = 0,
                  limit: int | None = None) -> dict[str, object]:
        """Compte rendu simple consommable par l'interface ou sérialisable en JSON."""
        def diagnostic(issue: Diagnostic) -> dict[str, object]:
            return {"code": issue.code, "message": issue.message,
                    "gravite": issue.severity.value, "feuille": issue.sheet,
                    "ligne": issue.line}

        result: dict[str, object] = {
            "nature": self.kind.value, "fichier": str(self.path),
            "feuille": self.sheet, "empreinte_sha256": self.source_digest,
            "statistiques": self.counts,
            "integrable": self.can_commit,
            "diagnostics_globaux": [diagnostic(d) for d in self.diagnostics],
        }
        if offset < 0 or (limit is not None and limit <= 0):
            raise ValueError("Pagination invalide : décalage positif et limite strictement positive requis.")
        pagination: dict[str, int | None] = {"total": len(self.rows), "offset": offset,
                                           "limite": limit, "affichees": 0}
        result["pagination"] = pagination
        if include_rows:
            selected = self.rows[offset: offset + limit if limit is not None else None]
            pagination["affichees"] = len(selected)
            result["lignes"] = [
                {"feuille": row.source.sheet, "ligne": row.source.line,
                 "action": row.action.value, "donnees": dict(row.values),
                 "diagnostics": [diagnostic(d) for d in row.diagnostics]}
                for row in selected
            ]
        return result

    @property
    def errors(self) -> tuple[Diagnostic, ...]:
        all_issues = list(self.diagnostics)
        for row in self.rows:
            all_issues.extend(row.diagnostics)
        return tuple(d for d in all_issues if d.severity == Severity.ERROR)

    @property
    def warnings(self) -> tuple[Diagnostic, ...]:
        all_issues = list(self.diagnostics)
        for row in self.rows:
            all_issues.extend(row.diagnostics)
        return tuple(d for d in all_issues if d.severity == Severity.WARNING)

    @property
    def can_commit(self) -> bool:
        return not self.errors and any(r.action == RowAction.CREATE for r in self.rows)

    @property
    def counts(self) -> dict[str, int]:
        out = {state.value: 0 for state in RowAction}
        for row in self.rows:
            out[row.action.value] += 1
        out["total"] = len(self.rows)
        out["erreurs"] = len(self.errors)
        out["avertissements"] = len(self.warnings)
        return out


@dataclass(frozen=True)
class StagedImport:
    """Un résultat *en mémoire*, jamais enregistré sur disque automatiquement."""
    session: Session = field(repr=False, compare=False)
    kind: InputKind
    created: int
    unchanged: int
    source_digest: str


class InboundError(ValueError):
    """Erreur contrôlée, sans modification des données des projets."""
