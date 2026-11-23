"""Charte de nommage regroupée (genvar/charte.py, 19/11) : effet identique à celui des règles dispersées qu'elle
remplace. Toute évolution de la charte devra modifier ces cas de façon visible."""
from pathlib import Path
import re

from genvar import charte

RACINE = Path(__file__).resolve().parents[1]

CAS = {
    charte.LIEU: (["ATMS", "XTST", "A1B2", "1234"], ["ATM", "ATMSX", "atms", "AT-S", ""]),
    charte.CODE_OUVRAGE: (["RV", "PR"], ["R1", "rv", "RVX", "R", ""]),
    charte.NUMERO_OUVRAGE: (["01", "09", "10", "99"], ["00", "1", "100", "0A", ""]),
    charte.SOUS_ENSEMBLE: (["00", "A1", "ZZ"], ["0", "000", "a1", ""]),
    charte.REVISION: (["A", "B2", "ABCD"], ["", "ABCDE", "a"]),
    charte.LIEU_SAISIE: (["ATMS", "atms"], ["ATM"]),
    charte.CODE_OUVRAGE_SAISIE: (["RV", "R1", "rv"], ["R", "RVX"]),       # écart connu, conservé
}


def test_effet_de_la_charte():
    for motif, (bons, mauvais) in CAS.items():
        for v in bons:
            assert charte.conforme(motif, v), (motif, v)
        for v in mauvais:
            assert not charte.conforme(motif, v), (motif, v)


def test_plus_aucune_copie_de_la_charte_hors_du_module():
    """Les motifs du lieu, du code et du numéro d'ouvrage ne sont plus écrits ailleurs que dans genvar/charte.py."""
    copies = []
    for p in [*(RACINE / "genvar").glob("*.py"), *(RACINE / "sorep_web").glob("*.py")]:
        if p.name == "charte.py":
            continue
        for n, ligne in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r're\.(fullmatch|match)\(r"\^?(\[A-Z0-9\]\{4\}|\[A-Z\]\{2\}\$?"|\(\?:0\[1-9\])', ligne):
                copies.append(f"{p.name}:{n}")
    assert copies == []
