"""Décision P3 : un code NOUVEAU du dictionnaire qui ne fait pas exactement 3 lettres produit une alerte.

Les codes livrés (2 à 9 caractères, V1-3-12) sont conservés sans alerte ; une alerte n'est jamais une erreur
(un code composé reste admis quand l'information l'exige, ex. DEF_EXT)."""
import json

from genvar import dictionnaire_es as de, modeles
from genvar.referentiel_depot import controler_modeles


def _livre():
    with open(modeles.fichier_origine(), encoding="utf-8") as f:
        return json.load(f)


def test_codes_livres_sans_alerte():
    d = _livre()["dictionnaire_es"]
    assert de.codes_hors_regle_3_lettres(d, d) == []


def test_nouveau_code_hors_trois_lettres_alerte_seulement():
    ref = _livre()["dictionnaire_es"]
    d = ref + [de.entree("ARRET", "ST", "Arrêt dédié"), de.entree("ARR", "ST", "Arrêt câblé"),
               de.entree("D_EXT", "ET", "Défaut externe déporté"), de.entree("AB", "ET", "Code court")]
    alertes = de.codes_hors_regle_3_lettres(d, ref)
    assert [a.split(" ")[4] for a in alertes] == ["ST.ARRET", "ET.D_EXT", "ET.AB"]
    assert all("3 lettres" in a for a in alertes)
    assert de.controler(d)[0] == []                                   # format V1 respecté : aucune erreur


def test_alerte_remontee_par_le_controle_du_referentiel():
    ref = _livre()
    ref["dictionnaire_es"] = ref["dictionnaire_es"] + [de.entree("ARRET", "ST", "Arrêt dédié")]
    erreurs, alertes = controler_modeles(ref, None)
    assert not any("ARRET" in e for e in erreurs)
    assert any("ST.ARRET" in a and "3 lettres" in a for a in alertes)
