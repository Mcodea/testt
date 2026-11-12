"""Normalisation des seules clés métier (jamais des adresses historiques)."""
from __future__ import annotations

from genvar import import_sources, inventaire, liste_es
from genvar.rapprochement import normaliser as normaliser_io

from .schemas import InputKind, InboundError, SourceData, SourceTable


def _aliases(kind: InputKind) -> dict[str, set[str]]:
    if kind == InputKind.INVENTORY:
        return {name: {inventaire._norm(label) for label in labels}
                for name, labels in inventaire.SYNONYMES.items()}
    if kind == InputKind.PLC_VARIABLES:
        return {name: {import_sources._normaliser(label) for label in labels}
                for name, labels in import_sources.ALIASES.items()}
    if kind == InputKind.PHYSICAL_IO:
        return {name: {normaliser_io(label) for label in labels}
                for name, labels in liste_es.ALIASES.items()}
    raise InboundError("Nature d'import non reconnue.")


def _header_key(kind: InputKind, header: str) -> str:
    if kind == InputKind.INVENTORY:
        return inventaire._norm(header)
    if kind == InputKind.PLC_VARIABLES:
        return import_sources._normaliser(header)
    return normaliser_io(header)


def columns(kind: InputKind, headers: tuple[str, ...]) -> dict[str, int]:
    aliases = _aliases(kind)
    result: dict[str, int] = {}
    for idx, cell in enumerate(headers):
        key = _header_key(kind, cell)
        for name, options in aliases.items():
            if key in options:
                if name in result:
                    raise InboundError(f"Colonnes ambiguës : le champ « {name} » apparaît plusieurs fois.")
                result[name] = idx
    required = {InputKind.INVENTORY: {"repere"},
                InputKind.PLC_VARIABLES: {"nom"},
                InputKind.PHYSICAL_IO: {"nom", "equipement", "fonction"}}[kind]
    missing = required - set(result)
    if missing:
        raise InboundError("Colonnes obligatoires absentes : " + ", ".join(sorted(missing)))
    return result


def choose_table(data: SourceData, kind: InputKind, sheet: str | None = None) -> tuple[SourceTable, int, dict[str, int]]:
    """Exige une sélection explicite si plusieurs feuilles pertinentes coexistent."""
    possible: list[tuple[SourceTable, int, dict[str, int]]] = []
    tables = [x for x in data.tables if sheet is None or x.name == sheet]
    if sheet is not None and not tables:
        raise InboundError(f"Feuille « {sheet} » introuvable.")
    for table in tables:
        for index, row in enumerate(table.rows[:15]):
            if not any(cell.strip() for cell in row.cells):
                continue
            try:
                mapping = columns(kind, row.cells)
            except InboundError as exc:
                if "ambiguës" in str(exc):
                    raise
                continue
            if row.formula_columns:
                raise InboundError("En-tête contenant une formule Excel : import refusé.")
            possible.append((table, index, mapping))
            break
    if not possible:
        raise InboundError("Aucune feuille avec les colonnes attendues pour cet import.")
    if len(possible) != 1:
        raise InboundError("Plusieurs feuilles exploitables : préciser explicitement le nom de la feuille.")
    return possible[0]


def get_values(cells: tuple[str, ...], mapping: dict[str, int]) -> dict[str, str]:
    return {name: cells[index].strip() if index < len(cells) else ""
            for name, index in mapping.items()}
