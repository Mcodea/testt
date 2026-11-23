"""Aller-retour Excel de la liste des équipements (19/11) : export, réimport comparé, obsolètes, protections.
Ouvrage fictif (lieu XTST)."""
from __future__ import annotations

from pathlib import Path

import pytest

from genvar import aller_retour, chemins, tableur
from genvar.catalogue import Catalogue
from genvar.inbound import InboundError, InputKind, RowAction, preview_import, stage_import
from genvar.modele import Equipement, UniteFonctionnelle
from genvar.session import Session


@pytest.fixture
def session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Session:
    monkeypatch.setenv("SOREP_DATA_DIR", str(tmp_path / "donnees_isolees"))
    s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
    s.nouveau(False)
    s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.definir("numero_ouvrage", "01")
    s.definir("libelle", "Réservoir fictif")
    s.ajouter_sous_ensemble("00")
    s.ouvrage.unites.append(UniteFonctionnelle("UF01", "Alimentation fictive"))
    for t, n, lib in (("HV", "01", "Vanne amont"), ("HV", "02", "Vanne aval"), ("FT", "01", "Débit")):
        s.ajouter_equipement(Equipement("00", t, n, lib))
    return s


def classeur(tmp_path: Path, session: Session, modifier=lambda lignes: lignes) -> Path:
    """Exporte la liste, applique `modifier` aux lignes (comme dans Excel), réécrit le classeur."""
    chemin = tmp_path / "equipements.xlsx"
    aller_retour.exporter(chemin, session.ouvrage)
    feuille = tableur.lire_classeur(chemin)["Équipements"]
    lignes = modifier([list(map(str, x)) for x in feuille[1:]])
    from genvar.export_xlsx import ecrire_xlsx
    ecrire_xlsx(chemin, [("Équipements", feuille[0], lignes, [20] * len(feuille[0]))])
    return chemin


def ligne(lignes, repere):
    return next(x for x in lignes if x[0] == repere)


def test_export_puis_reimport_sans_changement(session, tmp_path):
    apercu = preview_import(classeur(tmp_path, session), InputKind.EQUIPMENT_SYNC, session)
    assert [r.action for r in apercu.rows] == [RowAction.ALREADY_EXISTS] * 3
    assert apercu.obsoletes == () and not apercu.can_commit


def test_modifications_creations_obsoletes(session, tmp_path):
    def modifier(lignes):
        ligne(lignes, "XTSTRV01HV01")[1] = "Vanne amont rénovée"   # désignation modifiée
        ligne(lignes, "XTSTRV01HV01")[4] = "UF01"                  # rangée dans une UF existante
        lignes.remove(ligne(lignes, "XTSTRV01HV02"))               # ligne retirée : obsolète
        lignes.append(["XTSTRV01HV03", "Vanne fictive ajoutée", "HV", "", "", "", ""])
        return lignes
    avant = session.ouvrage.vers_dict()
    apercu = preview_import(classeur(tmp_path, session, modifier), InputKind.EQUIPMENT_SYNC, session)
    actions = {r.values["repere"]: r.action for r in apercu.rows}
    assert actions["XTSTRV01HV01"] == RowAction.UPDATE
    assert actions["XTSTRV01FT01"] == RowAction.ALREADY_EXISTS
    assert actions["XTSTRV01HV03"] == RowAction.CREATE
    maj = next(r for r in apercu.rows if r.action == RowAction.UPDATE)
    assert "Désignation : « Vanne amont » → « Vanne amont rénovée »" in maj.values["changements"]
    assert [o["repere"] for o in apercu.obsoletes] == ["XTSTRV01HV02"]
    assert session.ouvrage.vers_dict() == avant                    # l'aperçu n'écrit rien
    # Obsolète gardé par défaut
    garde = stage_import(apercu, session, confirmed=True)
    reps = {garde.session.ouvrage.repere(e): e for e in garde.session.ouvrage.equipements}
    assert (garde.created, garde.modified, garde.deleted) == (1, 1, 0)
    assert "XTSTRV01HV02" in reps and reps["XTSTRV01HV01"].libelle == "Vanne amont rénovée"
    assert reps["XTSTRV01HV01"].uf == "UF01"
    # Suppression sur choix explicite
    ident = apercu.obsoletes[0]["ident"]
    supprime = stage_import(apercu, session, confirmed=True, suppressions=[ident])
    assert supprime.deleted == 1
    assert "XTSTRV01HV02" not in {supprime.session.ouvrage.repere(e) for e in supprime.session.ouvrage.equipements}
    assert session.ouvrage.vers_dict() == avant


def test_cellule_vide_ne_vide_rien(session, tmp_path):
    def vider(lignes):
        lignes[0][1] = ""
        return lignes
    apercu = preview_import(classeur(tmp_path, session, vider), InputKind.EQUIPMENT_SYNC, session)
    assert apercu.rows[0].action == RowAction.ALREADY_EXISTS


def test_adresses_validees_protegees(session, tmp_path):
    hv1 = session.ouvrage.equipements[0]
    hv1.validees.append("TS_OUV")
    def retirer(lignes):
        return [x for x in lignes if x[0] != "XTSTRV01HV01"]
    apercu = preview_import(classeur(tmp_path, session, retirer), InputKind.EQUIPMENT_SYNC, session)
    assert apercu.obsoletes[0] == {"ident": hv1.ident, "repere": "XTSTRV01HV01", "libelle": "Vanne amont",
                                   "protege": True, "motif": "adresses validées : suppression impossible par import"}
    with pytest.raises(InboundError, match="Suppression refusée"):
        stage_import(apercu, session, confirmed=True, suppressions=[hv1.ident])


def test_refus_motives(session, tmp_path):
    hv1 = session.ouvrage.equipements[0]
    def fautes(lignes):
        ligne(lignes, "XTSTRV01HV01")[0] = "XTSTRV01HV09"         # repère modifié (identifiant connu)
        ligne(lignes, "XTSTRV01HV02")[4] = "UF99"                 # UF inexistante
        ligne(lignes, "XTSTRV01FT01")[3] = "MODELE_FICTIF_INCONNU"  # modèle hors référentiel
        return lignes
    apercu = preview_import(classeur(tmp_path, session, fautes), InputKind.EQUIPMENT_SYNC, session)
    codes = {d.code for d in apercu.errors}
    assert {"REPERE_MODIFIE", "UF_INCONNUE", "MODELE_INCONNU"} <= codes
    assert not apercu.can_commit
    assert hv1.ident in {o["ident"] for o in apercu.obsoletes}      # l'ancien repère n'est plus dans le fichier


def test_changement_de_modele(session, tmp_path):
    pm = session.ajouter_equipement(Equipement("00", "PM", "01", "Pompe fictive", modele="Groupe de pompage simple"))
    def changer(lignes):
        ligne(lignes, "XTSTRV01PM01")[3] = "Groupe de pompage avec compteur"
        return lignes
    apercu = preview_import(classeur(tmp_path, session, changer), InputKind.EQUIPMENT_SYNC, session)
    assert next(r for r in apercu.rows if r.values["repere"] == "XTSTRV01PM01").action == RowAction.UPDATE
    staged = stage_import(apercu, session, confirmed=True)
    assert next(e for e in staged.session.ouvrage.equipements if e.ident == pm.ident).modele == "Groupe de pompage avec compteur"
    pm.validees.append("TS_MAR")                                  # une adresse validée : modèle verrouillé
    apercu = preview_import(classeur(tmp_path, session, changer), InputKind.EQUIPMENT_SYNC, session)
    assert "MODELE_ADRESSES_VALIDEES" in {d.code for d in apercu.errors}
