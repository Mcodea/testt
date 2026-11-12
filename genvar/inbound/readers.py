"""Lecture déterministe, bornée et en lecture seule des sources tabulaires.

Les chemins des fichiers ne sont jamais créés ni modifiés. Les formules Excel
restent du texte et sont refusées par la validation. Les SCY et ODS sont lus
via les lecteurs déjà présents dans OGIAS, avec avis sur la numérotation logique.
"""
from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from pathlib import Path

from .schemas import (Diagnostic, InboundError, Severity, SourceData,
                      SourceRow, SourceTable)

MAX_BYTES = 15 * 1024 * 1024
MAX_UNPACKED_BYTES = 100 * 1024 * 1024
MAX_ROWS = 50000
MAX_COLUMNS = 256
MAX_CELL_LENGTH = 8192
FORMATS = frozenset({".csv", ".txt", ".xlsx", ".xlsm", ".ods", ".scy"})


def _cell(value: object) -> str:
    result = "" if value is None else str(value)
    if len(result) > MAX_CELL_LENGTH:
        raise InboundError(f"Cellule de plus de {MAX_CELL_LENGTH} caractères : source refusée.")
    if "\x00" in result:
        raise InboundError("Caractère NUL dans une cellule : source refusée.")
    return result


def _verify_zip(contents: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(contents)) as archive:
            if sum(z.file_size for z in archive.infolist()) > MAX_UNPACKED_BYTES:
                raise InboundError("Classeur trop volumineux après décompression.")
            if any(z.flag_bits & 1 for z in archive.infolist()):
                raise InboundError("Classeur chiffré non pris en charge.")
            if archive.testzip() is not None:
                raise InboundError("Classeur ZIP corrompu.")
    except (zipfile.BadZipFile, EOFError, OSError) as exc:
        raise InboundError("Classeur illisible ou corrompu.") from exc


def _csv_rows(path: Path, contents: bytes) -> tuple[SourceTable, ...]:
    from genvar.import_sources import _decodage
    try:
        text = _decodage(contents)
    except ValueError as exc:
        raise InboundError(str(exc)) from exc
    if not text.strip():
        raise InboundError("Fichier texte vide.")
    try:
        sep = csv.Sniffer().sniff(text[:8192], delimiters=";,\t|").delimiter
    except csv.Error:
        sep = "\t" if "\t" in text else ";"
    items: list[SourceRow] = []
    parser = csv.reader(io.StringIO(text, newline=""), delimiter=sep, strict=True)
    try:
        for row in parser:
            if len(row) > MAX_COLUMNS:
                raise InboundError("Trop de colonnes dans le fichier.")
            items.append(SourceRow(path.stem, parser.line_num, tuple(_cell(c) for c in row)))
            if len(items) > MAX_ROWS:
                raise InboundError("Trop de lignes dans le fichier.")
    except csv.Error as exc:
        raise InboundError(f"CSV mal formé près de la ligne {parser.line_num}.") from exc
    return (SourceTable(path.stem, tuple(items)),)


def _xlsx_rows(contents: bytes) -> tuple[SourceTable, ...]:
    try:
        from openpyxl import load_workbook
        from openpyxl.cell.cell import TYPE_FORMULA
    except ImportError as exc:
        raise InboundError("Lecture XLSX : bibliothèque openpyxl requise.") from exc
    try:
        workbook = load_workbook(io.BytesIO(contents), read_only=True, data_only=False, keep_links=False)
        try:
            if sum((sheet.max_row or 0) for sheet in workbook.worksheets) > MAX_ROWS:
                raise InboundError("Classeur dépassant la limite de lignes.")
            tables = []
            for sheet in workbook.worksheets:
                if (sheet.max_column or 0) > MAX_COLUMNS:
                    raise InboundError(f"Feuille {sheet.title} : trop de colonnes.")
                items = []
                for physical_line, cells in enumerate(sheet.iter_rows(), start=1):
                    if not cells:
                        continue
                    values = tuple(_cell(cell.value) for cell in cells)
                    formulas = tuple(i for i, cell in enumerate(cells)
                                     if cell.data_type == TYPE_FORMULA)
                    items.append(SourceRow(sheet.title, physical_line, values, formulas))
                tables.append(SourceTable(sheet.title, tuple(items)))
            return tuple(tables)
        finally:
            workbook.close()
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        if isinstance(exc, InboundError):
            raise
        raise InboundError("Classeur XLSX mal formé ou illisible.") from exc


def _ods_rows(contents: bytes) -> tuple[SourceTable, ...]:
    """Lecture ODS stricte conservant les rangs de lignes et répétitions.

    Contrairement à l'ancien lecteur, les lignes entièrement vides sont
    comptabilisées. Une feuille démesurée est refusée et non tronquée.
    """
    import xml.etree.ElementTree as ET
    from genvar import tableur
    tag_t = tableur.NS_T
    tag_tx = tableur.NS_TX
    formula_name = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}formula"
    try:
        with zipfile.ZipFile(io.BytesIO(contents)) as archive:
            root = ET.fromstring(archive.read("content.xml"))
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        raise InboundError("ODS corrompu ou contenu XML introuvable.") from exc
    tables: list[SourceTable] = []
    total_rows = 0
    for sheet in root.iter(tag_t + "table"):
        name = sheet.get(tag_t + "name", "")
        if name.startswith("'") and "#" in name:
            continue
        rows: list[SourceRow] = []
        for xml_row in sheet.iter(tag_t + "table-row"):
            cells: list[str] = []
            formula_cols: list[int] = []
            for cell in xml_row:
                if cell.tag not in (tag_t + "table-cell", tag_t + "covered-table-cell"):
                    continue
                try:
                    repeated = int(cell.get(tag_t + "number-columns-repeated", "1"))
                except ValueError as exc:
                    raise InboundError("ODS : répétition de colonnes invalide.") from exc
                if repeated < 1 or len(cells) + repeated > MAX_COLUMNS:
                    raise InboundError("ODS : limite de colonnes dépassée.")
                paragraphs = ["".join(p.itertext()) for p in cell.iter(tag_tx + "p")]
                text_value = _cell("\n".join(paragraphs) if paragraphs else cell.get(
                    "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}value", ""))
                if formula_name in cell.attrib:
                    formula_cols.extend(range(len(cells), len(cells) + repeated))
                cells.extend([text_value] * repeated)
            try:
                repeated_rows = int(xml_row.get(tag_t + "number-rows-repeated", "1"))
            except ValueError as exc:
                raise InboundError("ODS : répétition de lignes invalide.") from exc
            if repeated_rows < 1 or total_rows + repeated_rows > MAX_ROWS:
                raise InboundError("ODS : limite de lignes dépassée.")
            while cells and not cells[-1]:
                cells.pop()
            for _ in range(repeated_rows):
                total_rows += 1
                rows.append(SourceRow(name, len(rows) + 1, tuple(cells), tuple(formula_cols)))
        tables.append(SourceTable(name, tuple(rows)))
    return tuple(tables)


def _scy_rows(path: Path, contents: bytes) -> tuple[SourceTable, ...]:
    """SCY textuel traité selon le lecteur legacy, sans inventer un format binaire."""
    from genvar import import_sources
    try:
        text = import_sources._decodage(contents)
        try:
            sep = csv.Sniffer().sniff(text[:8192], delimiters=";,\t|").delimiter
        except csv.Error:
            sep = "\t" if "\t" in text else ";"
        raw = list(csv.reader(io.StringIO(text), delimiter=sep, strict=True))
        if not raw:
            raise ValueError("SCY vide")
        mapping = import_sources._colonnes(raw[0])
        if "nom" not in mapping or "adresse" not in mapping:
            raw = import_sources._scy_lignes(raw)
        else:
            idx = mapping["adresse"]
            if any(idx >= len(r) or not import_sources.ADR.fullmatch(r[idx].strip())
                   for r in raw[1:]):
                raise ValueError("SCY : adresse absente ou ambiguë")
    except (ValueError, csv.Error) as exc:
        raise InboundError("Source SCY texte illisible ou ambiguë.") from exc
    if len(raw) > MAX_ROWS:
        raise InboundError("SCY : trop de lignes.")
    return (SourceTable(path.stem, tuple(SourceRow(path.stem, i, tuple(_cell(x) for x in r))
                                          for i, r in enumerate(raw, 1))),)


def read_source(path: str | Path) -> SourceData:
    """Charge une source sans effet de bord et conserve son empreinte SHA-256."""
    source = Path(path).resolve(strict=False)
    if source.suffix.lower() not in FORMATS:
        raise InboundError("Format non pris en charge : utiliser CSV, TXT, XLSX, XLSM, ODS ou SCY texte.")
    if not source.is_file():
        raise InboundError("Fichier source introuvable.")
    try:
        stat = source.stat()
        if stat.st_size > MAX_BYTES:
            raise InboundError("Fichier trop volumineux pour cet import.")
        contents = source.read_bytes()
    except OSError as exc:
        raise InboundError("Lecture du fichier source impossible.") from exc
    if not contents:
        raise InboundError("Fichier source vide.")
    kind = source.suffix.lower()
    if kind in {".xlsx", ".xlsm", ".ods"}:
        _verify_zip(contents)
    if kind in {".csv", ".txt"}:
        tables = _csv_rows(source, contents)
    elif kind in {".xlsx", ".xlsm"}:
        tables = _xlsx_rows(contents)
    elif kind == ".ods":
        tables = _ods_rows(contents)
    else:
        tables = _scy_rows(source, contents)
    if not tables:
        raise InboundError("Aucune feuille lisible trouvée.")
    notices: tuple[Diagnostic, ...] = ()
    if kind == ".scy":
        notices = (Diagnostic(
            "LIGNES_LOGIQUES", "Format SCY normalisé : la conversion peut renuméroter les lignes logiques.",
            Severity.WARNING),)
    return SourceData(source, hashlib.sha256(contents).hexdigest(), tables, notices)
