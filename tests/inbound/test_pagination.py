"""Recette : les erreurs après la première page restent consultables et bloquantes."""
from __future__ import annotations

import base64
import csv
import io

import pytest

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.inbound import InboundError
from genvar.session import Session, RegleMetier
from sorep_web.serveur import Application, ROUTES_GET, ROUTES_POST


@pytest.fixture
def application(tmp_path, monkeypatch):
    monkeypatch.setenv("SOREP_DATA_DIR", str(tmp_path / "donnees"))
    instance = Application()
    instance.s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
    instance.s.nouveau(False)
    instance.s.definir("lieu", "ATHM")
    instance.s.definir("code_ouvrage", "RP")
    instance.s.definir("numero_ouvrage", "01")
    instance.ouvert = True
    return instance


def payload_longue(*, duplicated_last: bool) -> dict[str, str]:
    # 99 vannes, puis 21 débitmètres ; en dernière ligne, doublon éventuel de HV01.
    codes = ([f"ATHMRP01HV{i:02}" for i in range(1, 100)]
             + [f"ATHMRP01FT{i:02}" for i in range(1, 22)])
    if duplicated_last:
        codes[-1] = codes[0]
    out = io.StringIO(newline="")
    writer = csv.writer(out, delimiter=";")
    writer.writerow(["Repère", "Désignation", "Type", "Modèle"])
    writer.writerows([[c, "Exemple fictif", c[8:10], ""] for c in codes])
    return {"nom": "inventaire_fictif.csv", "nature": "inventaire",
            "contenu": base64.b64encode(out.getvalue().encode("utf-8")).decode("ascii")}


def test_anomalie_en_page_2_bloque_import(application, monkeypatch):
    before = application.s.ouvrage.vers_dict()
    monkeypatch.setattr(application, "_sauver", lambda: pytest.fail("Enregistrement interdit"))
    preview = application.inbound_preview(payload_longue(duplicated_last=True))
    assert preview["statistiques"]["total"] == 120
    assert preview["statistiques"]["erreurs"] >= 1
    assert len(preview["lignes_affichees"]) == 100
    assert preview["pagination"]["pages"] == 2
    assert preview["integrable"] is False
    page2 = application.inbound_page({"jeton": preview["jeton"], "page": "2"})
    assert len(page2["lignes_affichees"]) == 20
    assert page2["lignes_affichees"][-1]["ligne"] == 121
    assert any(x["code"] == "REPERE_REPETE" for x in page2["lignes_affichees"][-1]["diagnostics"])
    with pytest.raises(InboundError, match="erreur"):
        application.inbound_apply({"jeton": preview["jeton"], "confirmer": True})
    assert application.s.ouvrage.vers_dict() == before


def test_pages_valides_and_bad_token_are_refused(application):
    preview = application.inbound_preview(payload_longue(duplicated_last=False))
    assert preview["statistiques"]["erreurs"] == 0
    assert preview["integrable"] is True
    page2 = application.inbound_page({"jeton": preview["jeton"], "page": "2"})
    assert page2["pagination"]["page"] == 2
    assert len(page2["lignes_affichees"]) == 20
    with pytest.raises(RegleMetier, match="Aucun aperçu"):
        application.inbound_page({"jeton": "mauvais", "page": "1"})
    for bad in ("0", "3", "-1", "aaa"):
        with pytest.raises(RegleMetier):
            application.inbound_page({"jeton": preview["jeton"], "page": bad})
    application._clear_inbound()
    with pytest.raises(RegleMetier, match="Aucun aperçu"):
        application.inbound_page({"jeton": preview["jeton"], "page": "1"})


def test_suppression_routes_legacy_non_controlees():
    assert "/api/inbound/apercu" in ROUTES_POST
    assert "/api/inbound/appliquer" in ROUTES_POST
    assert "/api/inbound/lignes" in ROUTES_GET
    assert ROUTES_POST["/api/inventaire/appliquer"] == "import_inventaire_ancien_desactive"
    assert ROUTES_POST["/api/inventaire/apercu"] == "import_inventaire_ancien_desactive"
    with pytest.raises(RegleMetier, match="Ancienne procédure"):
        Application().import_inventaire_ancien_desactive({"lignes": []})
