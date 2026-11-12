"""Recette unitaire : entrées fictives et aucun accès aux projets réels."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest
from openpyxl import Workbook

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.inbound import (InboundError, InputKind, RowAction,
                            preview_import, stage_import)
from genvar.modele import Equipement
from genvar.session import RegleMetier, Session


@pytest.fixture
def session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Session:
    monkeypatch.setenv("SOREP_DATA_DIR", str(tmp_path / "donnees_isolees"))
    cat = Catalogue.charger(chemins.fichier_catalogue_origine())
    s = Session(cat)
    s.nouveau(False)
    s.definir("lieu", "ATHM")
    s.definir("code_ouvrage", "RP")
    s.definir("numero_ouvrage", "01")
    s.definir("libelle", "Poste fictif")
    return s


def table_csv(tmp_path: Path, name: str, headers: list[str], records: list[list[str]]) -> Path:
    source = tmp_path / name
    with source.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(headers)
        writer.writerows(records)
    return source


def inventaire(tmp_path: Path, rows: list[list[str]]) -> Path:
    return table_csv(tmp_path, "inventaire.csv", ["Repère", "Désignation", "Type", "Modèle"], rows)


def test_inventory_success_strict_read_only(session: Session, tmp_path: Path) -> None:
    file = inventaire(tmp_path, [["ATHMRP01HV01", "Vanne amont", "HV", ""],
                             ["ATHMRP01FT01", "Débit aval", "FT", ""]])
    before = session.ouvrage.vers_dict()
    preview = preview_import(file, InputKind.INVENTORY, session)
    assert preview.can_commit
    assert preview.counts["a_creer"] == 2
    assert preview.counts["total"] == 2
    assert session.ouvrage.vers_dict() == before
    with pytest.raises(InboundError, match="Validation explicite"):
        stage_import(preview, session)
    staged = stage_import(preview, session, confirmed=True)
    assert staged.created == 2
    assert staged.session.chemin is None
    assert len(staged.session.ouvrage.equipements) == 2
    assert {staged.session.ouvrage.repere(e) for e in staged.session.ouvrage.equipements} == {
        "ATHMRP01HV01", "ATHMRP01FT01"}
    assert session.ouvrage.vers_dict() == before


def test_inventory_duplicate_is_blocking_without_silent_drop(session: Session, tmp_path: Path) -> None:
    file = inventaire(tmp_path, [["ATHMRP01HV01", "Vanne", "HV", ""],
                             ["ATHMRP01HV01", "Vanne copiée", "HV", ""]])
    preview = preview_import(file, InputKind.INVENTORY, session)
    assert preview.counts["total"] == 2
    assert preview.counts["refuse"] == 1
    assert any(d.code == "REPERE_REPETE" for d in preview.errors)
    with pytest.raises(InboundError, match="erreur"):
        stage_import(preview, session, confirmed=True)
    assert not session.ouvrage.equipements


def test_inventory_blank_and_missing_repere_are_counted(session: Session, tmp_path: Path) -> None:
    file = inventaire(tmp_path, [["", "Désignation sans repère", "HV", ""],
                             [], ["ATHMRP01HV01", "Vanne", "HV", ""]])
    p = preview_import(file, InputKind.INVENTORY, session)
    assert p.counts["total"] == 3
    assert p.counts["ligne_vide"] == 1
    assert any(x.code == "REPERE_ABSENT" for x in p.errors)
    assert [(row.source.line, row.action) for row in p.rows] == [
        (2, RowAction.REJECT), (3, RowAction.EMPTY), (4, RowAction.CREATE)]


def test_inventory_foreign_prefix_and_old_repere_refused(session: Session, tmp_path: Path) -> None:
    file = inventaire(tmp_path, [["AUTRRP01HV01", "Étranger", "HV", ""],
                             ["ATHMRP0111HV01", "Ancien 14", "HV", ""]])
    p = preview_import(file, InputKind.INVENTORY, session)
    assert {x.code for x in p.errors} >= {"AUTRE_OUVRAGE", "CHARTE_12"}
    assert p.counts["a_creer"] == 0


def test_inventory_existing_not_changed(session: Session, tmp_path: Path) -> None:
    session.ajouter_sous_ensemble("00")
    session.ajouter_equipement(Equipement("00", "HV", "01", "Libellé d'origine"))
    file = inventaire(tmp_path, [["ATHMRP01HV01", "Libellé nouveau", "HV", ""]])
    p = preview_import(file, InputKind.INVENTORY, session)
    assert p.counts["deja_present"] == 1
    assert any(x.code == "LIBELLE_DIFFERENT" for x in p.warnings)
    staged = stage_import(p, session, confirmed=True)
    assert staged.created == 0
    assert staged.session.ouvrage.equipements[0].libelle == "Libellé d'origine"


def test_reimport_same_file_idempotent(session: Session, tmp_path: Path) -> None:
    file = inventaire(tmp_path, [["ATHMRP01HV01", "Vanne", "HV", ""]])
    first = stage_import(preview_import(file, InputKind.INVENTORY, session), session, confirmed=True)
    second_view = preview_import(file, InputKind.INVENTORY, first.session)
    assert second_view.counts["deja_present"] == 1
    second = stage_import(second_view, first.session, confirmed=True)
    assert second.created == 0
    assert len(second.session.ouvrage.equipements) == 1


def test_stale_project_rejected(session: Session, tmp_path: Path) -> None:
    file = inventaire(tmp_path, [["ATHMRP01HV01", "Vanne", "HV", ""]])
    p = preview_import(file, InputKind.INVENTORY, session)
    session.definir("libelle", "Nouvelle désignation")
    with pytest.raises(InboundError, match="projet ou le référentiel a changé"):
        stage_import(p, session, confirmed=True)


def test_changed_source_rejected(session: Session, tmp_path: Path) -> None:
    file = inventaire(tmp_path, [["ATHMRP01HV01", "Vanne", "HV", ""]])
    p = preview_import(file, InputKind.INVENTORY, session)
    inventaire(tmp_path, [["ATHMRP01HV02", "Vanne", "HV", ""]])
    with pytest.raises(InboundError, match="fichier ou la prévisualisation a changé"):
        stage_import(p, session, confirmed=True)


def test_mutated_preview_rejected(session: Session, tmp_path: Path) -> None:
    file = inventaire(tmp_path, [["ATHMRP01HV01", "Vanne", "HV", ""]])
    p = preview_import(file, InputKind.INVENTORY, session)
    p.rows[0].values["libelle"] = "Équipement falsifié"
    with pytest.raises(InboundError, match="fichier ou la prévisualisation a changé"):
        stage_import(p, session, confirmed=True)


def test_rollback_on_business_error(session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    file = inventaire(tmp_path, [["ATHMRP01HV01", "Vanne", "HV", ""],
                             ["ATHMRP01HV02", "Vanne", "HV", ""]])
    p = preview_import(file, InputKind.INVENTORY, session)
    call_count = 0
    original = Session.ajouter_equipement

    def fail_second(self: Session, eq: Equipement) -> Equipement:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RegleMetier("Injection de panne")
        return original(self, eq)

    monkeypatch.setattr(Session, "ajouter_equipement", fail_second)
    with pytest.raises(InboundError, match="Injection de panne"):
        stage_import(p, session, confirmed=True)
    assert len(session.ouvrage.equipements) == 0
    assert len(session.ouvrage.sous_ensembles) == 0


def test_source_project_file_is_never_written(session: Session, tmp_path: Path) -> None:
    existing = tmp_path / "existing.ouvrage.json"
    session.enregistrer(str(existing))
    original_bytes = existing.read_bytes()
    file = inventaire(tmp_path, [["ATHMRP01HV01", "Vanne", "HV", ""]])
    staged = stage_import(preview_import(file, InputKind.INVENTORY, session), session, confirmed=True)
    assert staged.session.chemin is None
    assert existing.read_bytes() == original_bytes
    assert list(tmp_path.glob("existing.ouvrage.json.*")) == []


def test_import_variables_existing_untouched_and_no_address_generation(session: Session, tmp_path: Path) -> None:
    session.definir("mode", "Existant")
    file = table_csv(tmp_path, "variables.csv", ["Nom", "Type", "Adresse", "Commentaire"],
                     [["V3_FER", "BOOL", "%M120", "FDC fermé"],
                      ["COMPTEUR", "DINT", "", "Sans adresse"]])
    p = preview_import(file, InputKind.PLC_VARIABLES, session)
    assert p.counts["a_creer"] == 2
    assert any(x.code == "ADRESSE_MANQUANTE" for x in p.warnings)
    staged = stage_import(p, session, confirmed=True)
    assert [v.adresse for v in staged.session.ouvrage.existantes] == ["%M120", ""]
    assert all(v.identification == "À identifier" for v in staged.session.ouvrage.existantes)
    assert not session.ouvrage.existantes


def test_import_variables_wrong_mode_blocked(session: Session, tmp_path: Path) -> None:
    file = table_csv(tmp_path, "var.csv", ["Nom", "Adresse"], [["VAR1", "%MW100"]])
    p = preview_import(file, InputKind.PLC_VARIABLES, session)
    assert any(x.code == "MODE_PROJET" for x in p.errors)


def test_import_variables_changed_source_rejected(session: Session, tmp_path: Path) -> None:
    session.definir("mode", "Existant")
    file = table_csv(tmp_path, "var.csv", ["Nom", "Type", "Adresse", "Commentaire"],
                     [["V1", "BOOL", "%M1", "V1"]])
    saved = stage_import(preview_import(file, InputKind.PLC_VARIABLES, session), session, confirmed=True)
    file = table_csv(tmp_path, "var.csv", ["Nom", "Type", "Adresse", "Commentaire"],
                     [["V1", "BOOL", "%M2", "V1"]])
    p = preview_import(file, InputKind.PLC_VARIABLES, saved.session)
    assert any(x.code == "SOURCE_VARIABLE_MODIFIEE" for x in p.errors)


def test_import_io_with_existing_reader_fields(session: Session, tmp_path: Path) -> None:
    session.definir("mode", "Existant")
    file = table_csv(tmp_path, "liste_es.csv", ["Nom", "Adresse", "Equipement", "Fonction", "Variable_liee"],
                     [["ET_VAN_01_FDC_OUV", "%I0.2.0", "HV01", "FDC ouverte", "V1"]])
    p = preview_import(file, InputKind.PHYSICAL_IO, session)
    assert p.counts["a_creer"] == 1
    out = stage_import(p, session, confirmed=True).session.ouvrage.entrees_physiques_importees
    assert out[0]["adresse"] == "%I0.2.0"
    assert out[0]["variable_liee"] == "V1"
    assert not session.ouvrage.entrees_physiques_importees


def test_import_io_duplicate_blocked(session: Session, tmp_path: Path) -> None:
    session.definir("mode", "Existant")
    file = table_csv(tmp_path, "es.csv", ["Nom", "Equipement", "Fonction"],
                     [["E_01", "HV01", "FDC"], ["e 01", "HV02", "FDC"]])
    p = preview_import(file, InputKind.PHYSICAL_IO, session)
    assert any(x.code == "ES_REPETEE" for x in p.errors)


def test_corrupt_and_empty_file(session: Session, tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.xlsx"
    corrupt.write_bytes(b"not really an xlsx")
    with pytest.raises(InboundError):
        preview_import(corrupt, InputKind.INVENTORY, session)
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(InboundError, match="vide"):
        preview_import(empty, InputKind.INVENTORY, session)


def test_missing_column_or_ambiguous_columns(session: Session, tmp_path: Path) -> None:
    p = table_csv(tmp_path, "bad.csv", ["Désignation"], [["vanne"]])
    with pytest.raises(InboundError, match="Aucune feuille"):
        preview_import(p, InputKind.INVENTORY, session)
    p = table_csv(tmp_path, "ambiguous.csv", ["Repère", "COD_EQPT", "Désignation"],
                  [["ATHMRP01HV01", "ATHMRP01HV01", "Vanne"]])
    with pytest.raises(InboundError, match="ambiguës"):
        preview_import(p, InputKind.INVENTORY, session)


def test_xlsx_formula_refused_and_lines_preserved(session: Session, tmp_path: Path) -> None:
    file = tmp_path / "formules.xlsx"
    book = Workbook()
    sheet = book.active
    sheet.title = "LISTE_EQUIPEMENTS"
    sheet.append(["Repère", "Désignation", "Type"])
    sheet.append(["ATHMRP01HV01", "=HYPERLINK(\"https://example.org\",\"X\")", "HV"])
    sheet.append([None, None, None])
    sheet.append(["ATHMRP01FT01", "Débit", "FT"])
    book.save(file)
    p = preview_import(file, InputKind.INVENTORY, session)
    assert any(x.code == "FORMULE_EXCEL" for x in p.errors)
    assert [r.source.line for r in p.rows] == [2, 3, 4]


def test_oversize_file_refused(session: Session, tmp_path: Path) -> None:
    file = tmp_path / "huge.csv"
    file.write_bytes(b"a" * (15 * 1024 * 1024 + 1))
    with pytest.raises(InboundError, match="volumineux"):
        preview_import(file, InputKind.INVENTORY, session)


def test_multiple_relevant_sheets_need_manual_choice(session: Session, tmp_path: Path) -> None:
    file = tmp_path / "sheets.xlsx"
    book = Workbook()
    for sh in (book.active, book.create_sheet("bis")):
        sh.append(["Repère", "Désignation"])
        sh.append(["ATHMRP01HV01", "Vanne"])
    book.save(file)
    with pytest.raises(InboundError, match="Plusieurs feuilles"):
        preview_import(file, InputKind.INVENTORY, session)
    p = preview_import(file, InputKind.INVENTORY, session, sheet="bis")
    assert p.sheet == "bis"


def test_historical_repere_12_and_14_not_renamed(session: Session, tmp_path: Path) -> None:
    session.ouvrage.format_repere = ""
    session.ouvrage.numero_ouvrage = ""  # ancien site au préfixe LIEU + TYPE
    file = inventaire(tmp_path, [["ATHMRP11HV01", "Vanne historique", "HV", ""]])
    p = preview_import(file, InputKind.INVENTORY, session)
    assert p.can_commit
    result = stage_import(p, session, confirmed=True).session
    assert result.ouvrage.repere(result.ouvrage.equipements[0]) == "ATHMRP11HV01"
    session.ouvrage.numero_ouvrage = "01"
    file = inventaire(tmp_path, [["ATHMRP0111HV01", "Vanne ancienne", "HV", ""]])
    p = preview_import(file, InputKind.INVENTORY, session)
    assert p.can_commit
    result = stage_import(p, session, confirmed=True).session
    assert result.ouvrage.repere(result.ouvrage.equipements[0]) == "ATHMRP0111HV01"


def test_empty_rows_are_counted_but_do_not_block(session: Session, tmp_path: Path) -> None:
    file = inventaire(tmp_path, [["ATHMRP01HV01", "Vanne", "HV", ""], [], []])
    p = preview_import(file, InputKind.INVENTORY, session)
    assert p.counts["ligne_vide"] == 2
    assert p.can_commit


def test_project_identity_required(session: Session, tmp_path: Path) -> None:
    session.definir("numero_ouvrage", "")
    file = inventaire(tmp_path, [["ATHMRP01HV01", "Vanne", "HV", ""]])
    p = preview_import(file, InputKind.INVENTORY, session)
    assert any(x.code == "OUVRAGE_NON_IDENTIFIE" for x in p.errors)


def test_row_with_only_unmapped_data_blocked(session: Session, tmp_path: Path) -> None:
    file = table_csv(tmp_path, "values.csv", ["Repère", "Note annexe"], [["", "Champ inattendu"]])
    p = preview_import(file, InputKind.INVENTORY, session)
    assert any(x.code == "COLONNES_NON_MAPPEES" for x in p.errors)


def test_nonnumeric_equipment_number_rejected(session: Session, tmp_path: Path) -> None:
    file = inventaire(tmp_path, [["ATHMRP01HVAA", "Vanne", "HV", ""]])
    p = preview_import(file, InputKind.INVENTORY, session)
    assert any(x.code == "TYPE_NUMERO_INCONNU" for x in p.errors)


def test_existing_model_unknown_does_not_get_replaced_silently(session: Session, tmp_path: Path) -> None:
    session.creer_modele("HV", "Modele valven 1")
    file = inventaire(tmp_path, [["ATHMRP01HV01", "Vanne", "HV", "MODELE_INEXISTANT"]])
    p = preview_import(file, InputKind.INVENTORY, session)
    assert any(x.code == "MODELE_INCONNU" for x in p.warnings)
    assert p.rows[0].values["modele_valide"] == ""
    assert stage_import(p, session, confirmed=True).session.ouvrage.equipements[0].modele == ""


def test_long_label_is_rejected_instead_of_truncated(session: Session, tmp_path: Path) -> None:
    file = inventaire(tmp_path, [["ATHMRP01HV01", "Libellé délibérément long de trente-deux caractères ou plus", "HV", ""]])
    p = preview_import(file, InputKind.INVENTORY, session)
    assert any(x.code == "LIBELLE_TROP_LONG" for x in p.errors)


def test_ods_preserves_repeated_rows_and_source_line(session: Session, tmp_path: Path) -> None:
    import zipfile
    # Fichier fictif minimal au format ODF ; aucune lecture ou écriture industrielle.
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
    <office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
      xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
      xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">
      <office:body><office:spreadsheet><table:table table:name="Inventaire">
      <table:table-row><table:table-cell><text:p>Repère</text:p></table:table-cell>
       <table:table-cell><text:p>Désignation</text:p></table:table-cell></table:table-row>
      <table:table-row table:number-rows-repeated="2"><table:table-cell/></table:table-row>
      <table:table-row><table:table-cell><text:p>ATHMRP01HV01</text:p></table:table-cell>
       <table:table-cell><text:p>Vanne</text:p></table:table-cell></table:table-row>
      </table:table></office:spreadsheet></office:body></office:document-content>'''
    source = tmp_path / "inventaire.ods"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("content.xml", xml)
    p = preview_import(source, InputKind.INVENTORY, session)
    assert [r.source.line for r in p.rows] == [2, 3, 4]
    assert p.counts["ligne_vide"] == 2
    assert p.can_commit


def test_scy_textual_reader_keeps_historical_addresses(session: Session, tmp_path: Path) -> None:
    session.definir("mode", "Existant")
    source = tmp_path / "export.scy"
    source.write_bytes("Adresse;Nom;Commentaire\n%M10;VAN_OUV;Fin course ouvert\n%MW200;VOL;Volume\n".encode("cp1252"))
    p = preview_import(source, InputKind.PLC_VARIABLES, session)
    assert p.counts["a_creer"] == 2
    staged = stage_import(p, session, confirmed=True)
    assert [v.adresse for v in staged.session.ouvrage.existantes] == ["%M10", "%MW200"]


def test_unhandled_file_extension_is_refused(session: Session, tmp_path: Path) -> None:
    source = tmp_path / "export.xsy"
    source.write_text("not validated format", encoding="utf-8")
    with pytest.raises(InboundError, match="Format non pris en charge"):
        preview_import(source, InputKind.PLC_VARIABLES, session)


def test_preview_report_is_json_serializable(session: Session, tmp_path: Path) -> None:
    import json
    file = inventaire(tmp_path, [["ATHMRP01HV01", "Vanne", "HV", ""]])
    preview = preview_import(file, InputKind.INVENTORY, session)
    payload = json.loads(json.dumps(preview.to_report(), ensure_ascii=False))
    assert payload["statistiques"]["total"] == 1
    assert payload["lignes"][0]["ligne"] == 2
    assert preview.to_report(include_rows=False).get("lignes") is None


def test_invalid_excel_formula_in_unmapped_column_is_refused(session: Session, tmp_path: Path) -> None:
    file = tmp_path / "formula_unmapped.xlsx"
    book = Workbook()
    book.active.append(["Repère", "Désignation", "Note libre"])
    book.active.append(["ATHMRP01HV01", "Vanne", '=1+1'])
    book.save(file)
    p = preview_import(file, InputKind.INVENTORY, session)
    assert any(x.code == "FORMULE_EXCEL" for x in p.errors)
