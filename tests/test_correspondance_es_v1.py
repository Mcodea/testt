"""Correspondance catalogue livré ↔ bibliothèque V1 : complète, sans ambiguïté."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("correspondance_es_v1", ROOT / "outils/correspondance_es_v1.py")
outil = importlib.util.module_from_spec(spec)
spec.loader.exec_module(outil)


def test_chaque_es_du_catalogue_a_sa_ligne_v1_et_seuls_les_ajouts_manquent():
    signaux, bibliotheque = outil.charger()
    paires, seuls_catalogue, seuls_classeur = outil.rapprocher(signaux, bibliotheque)
    assert len(paires) == 143                                    # 144 − CT.CP_VOL (CT supprimé, décision V2 D2)
    # Seule E/S postérieure au classeur V1 : sortie d'arrêt dédiée du profil VANNE_MV (décision P5).
    assert {f"{s['type']}.{s['famille']}_{s['code']}" for s in seuls_catalogue.values()} == {"MV.ES_ARR"}
    assert len({ident for _, ident, _ in paires}) == 143
    ajouts = {i for i, x in seuls_classeur.items() if x["Évolution"] == "Ajouté"}
    assert len(ajouts) == 49
    assert set(seuls_classeur) - ajouts == {"CT.ET.IMP"}
