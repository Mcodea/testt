"""Évaluation reproductible des méthodes sur un ouvrage fictif annoté.

Mesures strictes sur *la première proposition* et sur les signaux réellement
présents; les absences sont mesurées à part. Aucune validation automatique.
"""
import csv
import json
import sys
from pathlib import Path
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parents[1]))
from genvar.catalogue import Catalogue
from genvar.chemins import fichier_catalogue_origine
from genvar.modele import Ouvrage, Equipement, SousEnsemble, VariableExistante
from genvar.liste_es import charger_liste_es
from genvar.rapprochement import proposer, METHODES, SEUIL_CONFIANCE, CONFIANCE_ELEVEE



def scenario(repertoire=BASE):
    repertoire = Path(repertoire)
    cat = Catalogue.charger(fichier_catalogue_origine())
    o = Ouvrage(mode="Existant", code_ouvrage="RV", automate="TSX57")
    o.sous_ensembles = [SousEnsemble("11")]
    for code, no in [("MV", "03"), ("PM", "01"), ("FT", "02"), ("PT", "01"), ("LT", "01")]:
        o.equipements.append(Equipement("11", code, no))
    with (repertoire / "programme_fictif.csv").open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            o.existantes.append(VariableExistante(row["Nom"], row["Type"], row["Adresse"], row["Commentaire"]))
    o.entrees_physiques_importees = [v.__dict__ for v in charger_liste_es(repertoire / "liste_es_fictive.csv")]
    truth = json.loads((repertoire / "verite_reference.json").read_text(encoding="utf8"))
    eqs = {e.code_court():e for e in o.equipements}
    return o, cat, truth, eqs


def evaluer(repertoire=BASE):
    ouvrage, cat, truth, equip = scenario(repertoire)
    rapport = {"jeu": {"variables_source": len(ouvrage.existantes),
                         "equipements": len(ouvrage.equipements),
                         "es_documentaires": len(ouvrage.entrees_physiques_importees),
                         "liens_attendus": len(truth["liens"]),
                         "signaux_absents": len(truth["sans_variable"])}, "methodes": {}, "details": {}}
    for method in METHODES:
        propositions = proposer(ouvrage, cat, method)
        correctes, errones, non_trouvees, ambigu = 0, 0, 0, 0
        details = []
        for nom_eq, signal, attendu in truth["liens"]:
            cand = propositions[(equip[nom_eq].ident, signal)]
            top = cand[0] if cand else None
            if top is None:
                non_trouvees += 1
                outcome = "non_proposé"
            elif top.variable_nom == attendu:
                correctes += 1
                outcome = "correct"
            else:
                errones += 1
                outcome = "incorrect"
            if top and top.ambiguite:
                ambigu += 1
            details.append({"equipement": nom_eq, "signal": signal,
                            "attendu": attendu, "propose": top.variable_nom if top else "",
                            "score": top.score if top else 0, "decision": outcome,
                            "ambigu": bool(top.ambiguite) if top else False})
        absents_faux = 0
        for nom_eq, signal in truth["sans_variable"]:
            if propositions[(equip[nom_eq].ident, signal)]:
                absents_faux += 1
        n = len(truth["liens"])
        precision = 100 * correctes / (correctes + errones) if correctes + errones else None
        rappel = 100 * correctes / n
        f1 = 2 * precision * rappel / max(precision + rappel, 1e-9) if precision is not None else 0.0
        rapport["methodes"][method] = {
            "corrects": correctes, "faux": errones, "non_proposes": non_trouvees,
            "precision_pct": round(precision, 1) if precision is not None else None, "rappel_pct": round(rappel, 1),
            "f1_pct": round(f1, 1),
            "couverture_pct": round(100 * (correctes + errones) / n, 1),
            "premiers_candidats_ambigus": ambigu, "faux_positifs_sur_absents": absents_faux,
        }
        rapport["details"][method] = details
    return rapport


JEUX = (("Jeu initial", BASE), ("Jeu difficile", BASE / "jeu_difficile"))


def mesures_seuil(repertoire=BASE, seuil=SEUIL_CONFIANCE):
    """Mesures au seuil de confiance : premières propositions « élevées » (confirmables en lot) et plus haut
    score de toute proposition fausse connue (tous les candidats, signaux absents compris)."""
    ouvrage, cat, truth, equip = scenario(repertoire)
    sortie = {}
    for method in METHODES:
        props = proposer(ouvrage, cat, method)
        attendus = {att: (equip[n].ident, s) for n, s, att in truth["liens"]}
        faux = []
        for nom_eq, signal, attendu in truth["liens"]:
            faux += [p.score for p in props[(equip[nom_eq].ident, signal)] if p.variable_nom != attendu]
        for nom_eq, signal in truth["sans_variable"]:
            faux += [p.score for p in props[(equip[nom_eq].ident, signal)]]
        for cle, liste in props.items():           # variable attendue proposée pour une autre information
            faux += [p.score for p in liste if p.variable_nom in attendus and attendus[p.variable_nom] != cle]
        corrects = errones = 0
        for nom_eq, signal, attendu in truth["liens"]:
            liste = props[(equip[nom_eq].ident, signal)]
            if liste and liste[0].score >= seuil and liste[0].confiance == CONFIANCE_ELEVEE:
                corrects += liste[0].variable_nom == attendu
                errones += liste[0].variable_nom != attendu
        absents = sum(1 for n, s in truth["sans_variable"]
                      if any(p.score >= seuil for p in props[(equip[n].ident, s)]))
        n = len(truth["liens"])
        sortie[method] = {"eleves_corrects": corrects, "eleves_faux": errones, "faux_sur_absents": absents,
                          "precision_pct": round(100 * corrects / (corrects + errones), 1) if corrects + errones else None,
                          "rappel_pct": round(100 * corrects / n, 1), "liens": n,
                          "faux_connus": len(faux), "score_max_faux": max(faux, default=0)}
    return sortie


def rapport_seuil(seuil=SEUIL_CONFIANCE):
    """Texte publié dans validation/hybride/SEUIL_CONFIANCE.md (régénéré et comparé par les tests)."""
    l = ["# Seuil de confiance du rapprochement hybride — mesures publiées", "",
         "Fichier généré par `validation/hybride/evaluer.py` (`rapport_seuil`) et vérifié par",
         "`tests/test_seuil_confiance_rapprochement.py` : il ne peut pas diverger du code.", "",
         f"**Seuil de confiance : {seuil}/100** (`genvar.rapprochement.SEUIL_CONFIANCE`). Au-dessus, et si le premier",
         "candidat n'est pas ambigu (écart d'au moins 8 points avec le suivant), la proposition est de confiance",
         "« élevée » et peut être confirmée **en lot** par l'automaticien ; sinon la ligne est « à rapprocher",
         "manuellement ». Aucune correspondance n'est appliquée sans confirmation humaine ; un lot est tracé et",
         "annulable. Le score est un classement, pas une probabilité.", "",
         "Décision du 11/11/2026 : seuil strict conservé pour la 1.0 (l'utilisateur s'en remet à la recommandation).",
         "",
         "Règle de réglage : aucune proposition fausse connue (tous les candidats, y compris sur les signaux",
         "volontairement absents) n'atteint le seuil, sur tous les jeux de validation et pour toutes les méthodes.",
         "", "| Jeu | Méthode | Liens | Élevées correctes | Élevées fausses | Précision | Rappel | "
         "Faux connus | Score max. d'un faux |", "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    total = {m: [0, 0, 0] for m in METHODES}
    for nom, rep in JEUX:
        for m, r in mesures_seuil(rep, seuil).items():
            prec = "n.d." if r["precision_pct"] is None else f"{r['precision_pct']} %"
            l.append(f"| {nom} | {m} | {r['liens']} | {r['eleves_corrects']} | {r['eleves_faux']} | {prec} | "
                     f"{r['rappel_pct']} % | {r['faux_connus']} | {r['score_max_faux']} |")
            total[m][0] += r["eleves_corrects"]; total[m][1] += r["eleves_faux"]; total[m][2] += r["liens"]
    l += ["", "| Méthode (deux jeux) | Élevées correctes / liens | Précision | Rappel |", "|---|---:|---:|---:|"]
    for m, (c, f, n) in total.items():
        prec = f"{round(100 * c / (c + f), 1)} %" if c + f else "n.d."
        l.append(f"| {m} | {c}/{n} | {prec} | {round(100 * c / n, 1)} % |")
    l += ["", "Limites : deux jeux fictifs construits pour le développement, non représentatifs d'ouvrages réels ;",
          "le rappel au seuil est volontairement bas (la précision passe avant le rappel). Les autres",
          "correspondances restent proposées sous le seuil, à confirmer une par une. À remesurer sur des exports",
          "industriels anonymisés dont la vérité est établie avant l'exécution.", ""]
    return "\n".join(l)


if __name__ == "__main__":
    resultat = evaluer()
    print(json.dumps(resultat, ensure_ascii=False, indent=2))
