"""Intégration UI/API Inbound — environnement fictif isolé, sans données réelles."""
from __future__ import annotations

import base64
import csv
import io
from pathlib import Path

import pytest

from genvar import chemins
from genvar.catalogue import Catalogue
from genvar.inbound import InboundError
from genvar.session import Session
from sorep_web.serveur import Application


def payload(rows: list[list[str]], *, kind: str = "inventaire") -> dict[str, str]:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["Repère", "Désignation", "Type", "Modèle"])
    writer.writerows(rows)
    return {"nom": "test.csv", "contenu": base64.b64encode(buffer.getvalue().encode()).decode(),
            "nature": kind}


@pytest.fixture
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Application:
    monkeypatch.setenv("SOREP_DATA_DIR", str(tmp_path / "donnees"))
    target = Application()
    target.s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
    target.s.nouveau(False)
    for name, value in (("lieu", "ATHM"), ("code_ouvrage", "RP"),
                        ("numero_ouvrage", "01"), ("libelle", "Ouvrage fictif")):
        target.s.definir(name, value)
    target.ouvert = True
    target.creation_en_attente = False
    return target


def test_preview_not_mutating_or_saving(app: Application, monkeypatch: pytest.MonkeyPatch):
    original = app.s.ouvrage.vers_dict()
    monkeypatch.setattr(app, "_sauver", lambda: pytest.fail("Sauvegarde interdite pendant aperçu"))
    result = app.inbound_preview(payload([["ATHMRP01HV01", "Vanne fictive", "HV", ""]]))
    assert result["integrable"] is True
    assert result["statistiques"]["a_creer"] == 1
    assert app.s.ouvrage.vers_dict() == original
    assert result["jeton"]
    app._clear_inbound()


def test_confirm_success_calls_save_once(app: Application, monkeypatch: pytest.MonkeyPatch):
    calls = []
    monkeypatch.setattr(app, "_sauver", lambda: calls.append("save"))
    result = app.inbound_preview(payload([["ATHMRP01HV01", "Vanne fictive", "HV", ""]]))
    done = app.inbound_apply({"jeton": result["jeton"], "confirmer": True})
    assert done["crees"] == 1
    assert len(app.s.ouvrage.equipements) == 1
    assert calls == ["save"]
    with pytest.raises(Exception, match="Aucun aperçu"):
        app.inbound_apply({"jeton": result["jeton"], "confirmer": True})


def test_error_blocks_apply_without_save(app: Application, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(app, "_sauver", lambda: pytest.fail("Projet modifié malgré une erreur"))
    result = app.inbound_preview(payload([["ATHMRP01HV01", "Vanne", "HV", ""],
                                          ["ATHMRP01HV01", "Doublon", "HV", ""]]))
    assert result["integrable"] is False
    assert result["statistiques"]["erreurs"] >= 1
    with pytest.raises(InboundError, match="erreur"):
        app.inbound_apply({"jeton": result["jeton"], "confirmer": True})
    assert app.s.ouvrage.equipements == []


def test_save_failure_rolls_back_memory(app: Application, monkeypatch: pytest.MonkeyPatch):
    original = app.s
    def fail():
        raise OSError("panne disque fictive")
    monkeypatch.setattr(app, "_sauver", fail)
    result = app.inbound_preview(payload([["ATHMRP01HV01", "Vanne fictive", "HV", ""]]))
    with pytest.raises(OSError, match="panne disque"):
        app.inbound_apply({"jeton": result["jeton"], "confirmer": True})
    assert app.s is original
    assert not original.ouvrage.equipements


def test_previous_preview_revoked(app: Application):
    p = payload([["ATHMRP01HV01", "Vanne fictive", "HV", ""]])
    first = app.inbound_preview(p)
    second = app.inbound_preview(p)
    assert first["jeton"] != second["jeton"]
    with pytest.raises(Exception, match="Aucun aperçu"):
        app.inbound_apply({"jeton": first["jeton"], "confirmer": True})
    app.fermer({})
    with pytest.raises(Exception, match="Aucun aperçu"):
        app.inbound_apply({"jeton": second["jeton"], "confirmer": True})
