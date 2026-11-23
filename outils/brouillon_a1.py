"""Brouillon du référentiel avec les SEULS renommages approuvés par l'utilisateur (décision A1 du 23/11/2026).

    py outils/brouillon_a1.py             # écrit validation/referentiel/brouillon_a1/ (candidat) et son rapport
    py outils/brouillon_a1.py --verifier  # échoue si le candidat ne correspond plus aux sources

Rien n'est publié : `genvar/data/` (référentiel livré) n'est jamais modifié, aucun ajout n'est appliqué, aucun ouvrage n'est
touché. Le candidat se relit, puis la publication attend l'accord explicite de l'utilisateur.
Les renommages sont ceux de l'aperçu (`outils/apercu_a1.py`) moins les refus de `validation/referentiel/decision_a1.json`.
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "outils"))
import apercu_a1  # noqa: E402
from genvar.modele import suffixe_physique  # noqa: E402

DECISION = RACINE / "validation" / "referentiel" / "decision_a1.json"
SORTIE = RACINE / "validation" / "referentiel" / "brouillon_a1"
MOTIF = "A1 approuvé le 23/11/2026 : renommage pour harmoniser le code de l'E/S avec la bibliothèque V1."


def code_nouveau_de(cle):
    return cle.split("_", 1)[1]


def construire():
    """(donnees du candidat, rapport) : renommages approuvés appliqués à une COPIE du référentiel livré."""
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    refuses = set(decision["renommages_refuses"])
    catalogue = json.loads((RACINE / "genvar/data/catalogue_defaut.json").read_text(encoding="utf-8"))
    modeles = json.loads((RACINE / "genvar/data/referentiel_modeles.json").read_text(encoding="utf-8"))
    cat, sig, _, bibliotheque, _ = apercu_a1._donnees()
    apercu = apercu_a1.calculer()
    candidat = {"catalogue": copy.deepcopy(catalogue), "modeles": copy.deepcopy(modeles)}
    signaux = candidat["catalogue"]["signaux"]
    appliques, ecarts, exceptions_d4 = [], [], []
    for r in apercu["renommages"]:
        ident = f"{r['type']}.{r['nature']}.{r['code_actuel']}"
        if ident in refuses:
            continue
        s = next(x for x in signaux if (x["type"], x["es"], x["code"]) == (r["type"], r["nature"], r["code_actuel"]))
        lib = next((b for b in bibliotheque.values() if (b["Type"], b["Nature"], b["Code"]) == (r["type"], r["nature"], r["code_propose"])), None)
        tele = (lib or {}).get("Télétransmission") or ""
        cles = [k.strip() for k in tele.split("/") if "_" in k] or [f"{s['famille']}_{r['code_propose']}"]
        ok = True
        for nouvelle in cles:                                   # ex. « TR_TAU / RTR_TAU » : la sortie et son retour suivent
            famille_nouvelle, code_nouveau = nouvelle.split("_", 1)
            cible = next((x for x in signaux if (x["type"], x["famille"], x["code"]) == (r["type"], famille_nouvelle, r["code_actuel"])
                          and (x["es"] == r["nature"] or x["es"] == "Interne")), None)
            if cible is None:
                ecarts.append(f"{ident} : aucun signal du catalogue pour la clé {nouvelle} (non appliqué, à examiner).")
                ok = False
                break
        if not ok:
            continue
        for nouvelle in cles:
            famille_nouvelle = nouvelle.split("_", 1)[0]
            cible = next(x for x in signaux if (x["type"], x["famille"], x["code"]) == (r["type"], famille_nouvelle, r["code_actuel"])
                         and (x["es"] == r["nature"] or x["es"] == "Interne"))
            ancienne = f"{cible['famille']}_{cible['code']}"
            cible["code"] = code_nouveau_de(nouvelle)
            if cible["es"] == r["nature"]:                       # E/S physique : le nom physique suit la bibliothèque V1
                attendu = r["physique_propose"].split("_", 2)[2]
                if suffixe_physique(cible) != attendu:
                    cible["suffixe_es"] = attendu                # exception D4 décidée le 23/11/2026 (CONS_TAU, CONS_FRQ)
                    exceptions_d4.append({"ident": ident, "cle": nouvelle, "suffixe_es": attendu})
            appliques.append({"ident": ident, "type": r["type"], "nature": cible["es"], "ancienne": ancienne, "nouvelle": nouvelle,
                              "physique_propose": r["physique_propose"] if cible["es"] == r["nature"] else "—"})
    renommes = {(a["type"], a["ancienne"]): a["nouvelle"] for a in appliques}
    for s2 in signaux:                                          # un signal peut citer sa source physique par sa clé
        if s2.get("source"):
            s2["source"] = renommes.get((s2["type"], s2["source"]), s2["source"])
    for regle in candidat["catalogue"]["regles"]:           # les règles citent les signaux par leur clé FAMILLE_CODE
        for champ in ("si", "propose"):
            regle[champ] = [renommes.get((regle["type"], k), k) for k in regle.get(champ, [])]
    for a in appliques:
        candidat["modeles"].setdefault("correspondances", []).append(
            {"type": a["type"], "ancienne": a["ancienne"], "type_nouveau": a["type"], "nouvelle": a["nouvelle"], "motif": MOTIF})
    candidat["catalogue"]["version"] = f"{catalogue['version']} + A1 ({len(appliques)} renommages approuvés)"
    physiques_divergents = []
    for a in appliques:
        if a["physique_propose"] == "—" or a["nouvelle"].split("_", 1)[0] == "RTR":
            continue
        signal = next(x for x in signaux if x["type"] == a["type"] and x["es"] == a["nature"] and f"{x['famille']}_{x['code']}" == a["nouvelle"])
        attendu = a["physique_propose"].split("_", 2)[2]
        if suffixe_physique(signal) != attendu:
            physiques_divergents.append({"ident": a["ident"], "candidat": suffixe_physique(signal), "bibliotheque": attendu,
                                         "cause": "suffixe_es explicite (décision D4)" if signal.get("suffixe_es") else "autre"})
    return candidat, {"appliques": appliques, "ecarts": ecarts, "exceptions_d4": exceptions_d4, "physiques_divergents": physiques_divergents, "refuses": sorted(refuses), "decision": decision,
                      "ajouts_non_appliques": len(apercu["ajouts"])}


def controler(candidat) -> dict:
    """Contrôles du dépôt de référentiel, unicité des clés par type et nom physique attendu après renommage."""
    from genvar.modele import suffixe_physique
    from genvar.referentiel_depot import Depot
    with tempfile.TemporaryDirectory(prefix="ogias-a1-") as tmp:
        controles = Depot(tmp).controler(candidat)
    doublons = []
    vues = set()
    for s in candidat["catalogue"]["signaux"]:
        cle = (s["type"], s["famille"], s["code"])
        if cle in vues:
            doublons.append(f"{s['type']}.{s['famille']}_{s['code']}")
        vues.add(cle)
    physiques = {(s["type"], s["es"], s["code"]): suffixe_physique(s) for s in candidat["catalogue"]["signaux"]}
    return {"erreurs": controles["erreurs"], "alertes": controles["alertes"], "doublons": doublons, "physiques": physiques}


def _rapport(candidat, rapport, c) -> str:
    l = ["# Brouillon A1 : renommages approuvés", "",
         "Généré par `outils/brouillon_a1.py` : ne pas modifier à la main. **Candidat non publié** : le référentiel livré "
         "(`genvar/data/`) est inchangé, aucun ajout n'est appliqué, aucun ouvrage n'est touché.", "",
         f"- Clés de signaux renommées dans le candidat : **{len(rapport['appliques'])}** (pour les 38 renommages approuvés sur 57 ; refusés : {len(rapport['refuses'])}).",
         f"- Ajouts : **{rapport['ajouts_non_appliques']} non appliqués** (aucune réponse de l'utilisateur).",
         f"- Contrôles du dépôt de référentiel : {len(c['erreurs'])} erreur(s), {len(c['alertes'])} alerte(s) ; "
         f"{len(c['doublons'])} clé(s) en double.", "",
         "## Renommages appliqués", "", "| Type | Nature | Clé actuelle → nouvelle | Nom physique après renommage (exemple) |", "| --- | --- | --- | --- |"]
    for a in rapport["appliques"]:
        l.append(f"| {a['type']} | {a['nature']} | `{a['ancienne']}` → `{a['nouvelle']}` | `{a['physique_propose']}` |")
    l += ["", "## Renommages refusés (conservés tels quels)", "", ", ".join(f"`{x}`" for x in rapport["refuses"]), ""]
    if rapport["exceptions_d4"]:
        l += ["## Exceptions D4 décidées le 23/11/2026", "",
              "Le nom physique de la bibliothèque V1 diffère du code fonctionnel : il est porté par `suffixe_es`.", "",
              "| Renommage | Clé fonctionnelle | Suffixe d'E/S |", "| --- | --- | --- |"]
        l += [f"| `{x['ident']}` | `{x['cle']}` | `{x['suffixe_es']}` |" for x in rapport["exceptions_d4"]] + [""]
    if rapport["physiques_divergents"]:
        l += ["## Noms physiques qui restent différents de la bibliothèque", "",
              "Le renommage change la clé fonctionnelle ; le nom de l'E/S physique garde son suffixe explicite (`suffixe_es`, décision D4). "
              "La bibliothèque V1 proposait un autre suffixe : à confirmer.", "", "| Renommage | Suffixe physique du candidat | Suffixe de la bibliothèque |", "| --- | --- | --- |"]
        l += [f"| `{x['ident']}` | `{x['candidat']}` | `{x['bibliotheque']}` |" for x in rapport["physiques_divergents"]] + [""]
    if rapport["ecarts"]:
        l += ["## À examiner", ""] + [f"- {x}" for x in rapport["ecarts"]] + [""]
    if c["erreurs"]:
        l += ["## Erreurs de contrôle", ""] + [f"- {x}" for x in c["erreurs"][:30]] + [""]
    l += ["## Effet sur les ouvrages", "",
          "Chaque renommage est déclaré dans les **correspondances** du référentiel : à l'adoption d'une révision par un ouvrage "
          "existant (action volontaire, ligne à ligne, avec sauvegarde), adresses %MW, voies et commentaires sont reportés de "
          "l'ancienne clé vers la nouvelle (tests/test_brouillon_a1.py). Les nouveaux ouvrages utilisent directement les nouveaux codes.", ""]
    return "\n".join(l)


def main(argv) -> int:
    candidat, rapport = construire()
    c = controler(candidat)
    textes = {"catalogue_defaut.json": json.dumps(candidat["catalogue"], ensure_ascii=False, indent=1) + "\n",
              "referentiel_modeles.json": json.dumps(candidat["modeles"], ensure_ascii=False, indent=1) + "\n",
              "RAPPORT.md": _rapport(candidat, rapport, c)}
    if "--verifier" in argv:
        for nom, texte in textes.items():
            f = SORTIE / nom
            if not f.is_file() or f.read_text(encoding="utf-8") != texte:
                print(f"{nom} n'est plus à jour : py outils/brouillon_a1.py")
                return 1
        return 0
    SORTIE.mkdir(parents=True, exist_ok=True)
    for nom, texte in textes.items():
        (SORTIE / nom).write_text(texte, encoding="utf-8", newline="\n")
    print(f"Écrit : {SORTIE} ({len(rapport['appliques'])} renommages, {len(c['erreurs'])} erreur(s), {len(c['alertes'])} alerte(s))")
    return 1 if c["erreurs"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
