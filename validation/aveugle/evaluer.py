"""Évaluation à l'aveugle du pré-remplissage de la table de télétransmission.

Ordre strict : 1) le moteur construit la table et propose ses associations à partir des
seuls fichiers d'entrée (équipements, programme, liste E/S) ; 2) SEULEMENT ENSUITE le
corrigé (dossier corrige/) est ouvert pour compter bonnes, fausses et omises.
Le corrigé a été écrit à la main avant la première exécution ; les règles du moteur
n'ont pas été modifiées après avoir vu ces résultats.

    py validation/aveugle/evaluer.py
"""
import csv
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parents[1]))

from genvar.catalogue import Catalogue
from genvar.modele import Ouvrage, Equipement, SousEnsemble, VariableExistante
from genvar.liste_es import charger_liste_es
from genvar import teletransmission as tt


def _lire(nom):
    with (BASE / nom).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def preparer():
    # Catalogue figé à la date d'écriture du corrigé : les évolutions du catalogue livré
    # ne doivent pas rendre la mesure incomparable.
    cat = Catalogue.charger(str(BASE / "catalogue_reference.json"))
    o = Ouvrage(mode="Existant", lieu="", code_ouvrage="RV", libelle="Jeu aveugle", automate="M340")
    for r in _lire("equipements.csv"):
        if not any(s.code == r["SousEnsemble"] for s in o.sous_ensembles):
            o.sous_ensembles.append(SousEnsemble(r["SousEnsemble"]))
        o.equipements.append(Equipement(r["SousEnsemble"], r["Type"], r["Numero"], r["Libelle"],
                                         options=[x for x in r["Options"].split("|") if x]))
    for r in _lire("programme.csv"):
        o.existantes.append(VariableExistante(r["Nom"], r["Type"], r["Adresse"], r["Commentaire"]))
    o.entrees_physiques_importees = [e.__dict__ for e in charger_liste_es(BASE / "liste_es.csv")]
    return o, cat


def evaluer():
    o, cat = preparer()
    tt.construire(o, cat)
    proposees = tt.proposer_associations(o, cat)
    candidats = tt.candidats(o, cat)
    code = {e.ident: f"{e.sous_ensemble}{e.type}{e.numero}" for e in o.equipements}
    obtenu = {(code[l.ident_eq], l.cle): l.variable_source for l in o.table_tt}
    top = {(code[i], c): (p[0].variable_nom if p else "") for (i, c), p in candidats.items()}

    # ----- ouverture du corrigé : après les propositions uniquement
    corrige = json.loads((BASE / "corrige" / "corrige.json").read_text(encoding="utf-8"))
    res = {"lignes_table": len(o.table_tt), "associations_proposees": proposees,
           "liens_attendus": len(corrige["liens"]), "bonnes": 0, "fausses": 0, "omises": 0,
           "faux_sur_absents": 0, "pieges_associes": [], "candidat_juste_dans_la_liste": 0, "details": []}
    for eq, cle, attendu in corrige["liens"]:
        recu = obtenu.get((eq, cle), "")
        decision = "bonne" if recu == attendu else ("omise" if not recu else "fausse")
        res[{"bonne": "bonnes", "fausse": "fausses", "omise": "omises"}[decision]] += 1
        ident = next(i for i, c in code.items() if c == eq)
        dans_liste = any(p.variable_nom == attendu for p in candidats.get((ident, cle), []))
        res["candidat_juste_dans_la_liste"] += dans_liste
        res["details"].append({"equipement": eq, "signal": cle, "attendu": attendu, "propose": recu,
                               "decision": decision, "candidat_juste_dans_la_liste": dans_liste})
    for eq, cle in corrige["sans_variable"]:
        if obtenu.get((eq, cle)):
            res["faux_sur_absents"] += 1
            res["details"].append({"equipement": eq, "signal": cle, "attendu": "", "propose": obtenu[(eq, cle)],
                                   "decision": "faux sur absent"})
    utilisees = set(obtenu.values())
    res["pieges_associes"] = sorted(n for n in corrige["pieges"] if n in utilisees)
    n = res["liens_attendus"]
    emis = res["bonnes"] + res["fausses"] + res["faux_sur_absents"]
    res["rappel_pct"] = round(100 * res["bonnes"] / n, 1)
    res["precision_pct"] = round(100 * res["bonnes"] / emis, 1) if emis else None
    return res


if __name__ == "__main__":
    r = evaluer()
    detail = r.pop("details")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    print("\nÉcarts :")
    for d in detail:
        if d["decision"] != "bonne":
            print(f"  {d['decision']:16} {d['equipement']} {d['signal']:10} attendu={d['attendu'] or '—':24} "
                  f"proposé={d['propose'] or '—'}")
    (BASE / "resultats.json").write_text(json.dumps({**r, "details": detail}, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
