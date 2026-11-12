"""Entrées rejetées et aller-retour synthétique ; aucune qualification constructeur."""
import pytest

from genvar import formats_control_expert as ce
from genvar import formats_topkapi as tk


@pytest.mark.parametrize("variable", [
    ce.VariableCE("A" * 33, "", "BOOL"),
    ce.VariableCE("XTST", "%adresse_invalide", "BOOL"),
    ce.VariableCE("XTST", "", ""),
    ce.VariableCE("", "", "BOOL"),
])
def test_xsy_refuse_variables_invalides(variable):
    with pytest.raises(ce.FormatInvalide):
        ce.xsy([variable], "XTST")


def test_lecture_refuse_taille_encodage_xml_et_scy_invalides(tmp_path, monkeypatch):
    source = tmp_path / "fictif.txt"
    monkeypatch.setattr(ce, "TAILLE_MAX", 4)
    source.write_bytes(b"12345")
    with pytest.raises(ce.FormatInvalide, match="volumineux"):
        ce.lire_txt(source)
    source.write_bytes(b"\x81")
    with pytest.raises(ce.FormatInvalide, match="Encodage"):
        ce.lire_txt(source)
    source.write_bytes(b"<bad")
    with pytest.raises(ce.FormatInvalide, match="XSY illisible"):
        ce.lire_xsy(source)
    source.write_bytes(b"bad")
    with pytest.raises(ce.FormatInvalide, match="VAR_GLOBAL"):
        ce.lire_scy(source)


def test_lecture_cp1252_txt_lignes_vides_et_champs_manquants(tmp_path):
    source = tmp_path / "fictif.txt"
    source.write_bytes('\r\nXTST\t%M1\tBOOL\t"État fictif"\t(1)\r\n'.encode("cp1252"))
    assert ce.lire_txt(source) == [ce.VariableCE("XTST", "%M1", "BOOL", "État fictif", "1")]
    source.write_text("incomplet", encoding="utf-8")
    with pytest.raises(ce.FormatInvalide, match="tabulations"):
        ce.lire_txt(source)
    with pytest.raises(ce.FormatInvalide, match="Format attendu"):
        ce.lire(source.with_suffix(".inconnu"))


@pytest.mark.parametrize("address", ["1$10", "1$G", "invalide"])
def test_topkapi_refuse_adresses_malformees(address):
    with pytest.raises(tk.FormatTopkapiInvalide):
        _ = tk.PointTopkapi("XTST", address, "0", "Fictif").mot_bit


def test_topkapi_refuse_entete_nombre_de_champs_et_caracteres():
    with pytest.raises(tk.FormatTopkapiInvalide, match="en-tête"):
        tk.lire_octets(b"Version\t2\r\n")
    malformed = ("Version\t1\r\n" + "\t".join(tk.ENTETE) + "\r\nXTST\t1\r\n").encode()
    with pytest.raises(tk.FormatTopkapiInvalide, match="champs"):
        tk.lire_octets(malformed)
    for value in ("Fictif\n", "Fictif\t", "Fictif\r", "\u4e2d"):
        with pytest.raises(tk.FormatTopkapiInvalide):
            tk.ecrire_octets([tk.PointTopkapi("XTST", "1$0", "0", value)])


def test_topkapi_detecte_doublons_et_recouvrements():
    points = [tk.PointTopkapi("XTST", "10", "102", "Fictif"),
              tk.PointTopkapi("XTST", "10$0", "0", "Fictif"),
              tk.PointTopkapi("XTST2", "10$0", "0", "Fictif"),
              tk.PointTopkapi("XTST3", "11", "2", "Fictif"),
              tk.PointTopkapi("XTST4", "10", "2", "Fictif")]
    errors = tk.controler(points)
    assert any("mnémonique en double" in error for error in errors)
    assert any("déjà utilisé par" in error for error in errors)
    assert any("mot déjà utilisé" in error for error in errors)
    assert any("mot 11 déjà utilisé" in error for error in errors)
    assert any("déjà découpé en bits" in error for error in errors)


def test_topkapi_lecture_fichier_preserve_contenu_et_identifiant(tmp_path):
    point = tk.PointTopkapi("TS_XTSTRV01HV01_FER", "10$A", "0", "État fictif")
    source = tmp_path / "fictif.$$t"
    octets = tk.ecrire_octets([point])
    source.write_bytes(octets)
    assert tk.lire(source) == [point]
    assert tk.lire(source)[0].mot_bit == (10, 10)
    assert source.read_bytes() == octets
