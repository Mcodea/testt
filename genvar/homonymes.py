"""Homonymes entre ouvrages d'un même programme automate (décisions P8 / R9).

Quand le lieu n'est pas dans le nom (`lieu_dans_le_nom` faux, charte 12), deux ouvrages de lieux différents
produisent les mêmes noms (`TS_RV01MV01_OUV`). S'ils sont déclarés dans le même projet Control Expert
(`nom_projet`), ces noms se heurtent dans le programme : c'est une erreur qui demande un arbitrage de
l'utilisateur (mettre le lieu dans les noms, ou renuméroter l'un des ouvrages). Rien n'est renommé ici.

Périmètre retenu : le projet Control Expert déclaré (`nom_projet`, sans tenir compte de la casse ni des espaces).
Un ouvrage sans projet déclaré n'a pas de périmètre commun connu : aucune comparaison. Une table d'échange
commune à plusieurs programmes n'est pas modélisée à ce jour et n'est donc pas contrôlée.
"""
from __future__ import annotations

from typing import Iterable

from .modele import Anomalie, generer, generer_internes, generer_points


def perimetre(ouvrage) -> str:
    return " ".join((getattr(ouvrage, "nom_projet", "") or "").split()).upper()


def noms_ouvrage(ouvrage, catalogue) -> dict[str, str]:
    """{nom: ident de l'équipement} des variables d'échange, des E/S physiques et des variables internes
    déclarées de l'ouvrage."""
    noms: dict[str, str] = {}
    for v in generer(ouvrage, catalogue):
        noms.setdefault(v.nom, v.ident_eq)
    for p in generer_points(ouvrage, catalogue):
        noms.setdefault(p.nom, p.ident_eq)
    for x in generer_internes(ouvrage, catalogue):
        noms.setdefault(x.nom, x.ident_eq)
    for x in getattr(ouvrage, "existantes", []) or []:
        if getattr(x, "nom", ""):
            noms.setdefault(x.nom, getattr(x, "ident_eq", "") or "")
    return noms


def homonymes(ouvrage, catalogue, autres: Iterable[tuple[str, object, object]]) -> list[Anomalie]:
    """Anomalies « Erreur » pour chaque nom de `ouvrage` déjà employé par un autre ouvrage du même programme.

    `autres` : [(repère affiché, ouvrage, catalogue)]. L'ouvrage lui-même (même `ident_projet`) est ignoré.
    """
    cible = perimetre(ouvrage)
    if not cible:
        return []
    concurrents = [(rep, o, c) for rep, o, c in autres
                   if perimetre(o) == cible and getattr(o, "ident_projet", None) != ouvrage.ident_projet]
    if not concurrents:
        return []
    mes_noms = noms_ouvrage(ouvrage, catalogue)
    deja: dict[str, list[str]] = {}
    for rep, o, c in concurrents:
        for nom in sorted(set(noms_ouvrage(o, c)) & set(mes_noms)):
            deja.setdefault(nom, []).append(rep)
    # Une anomalie par équipement et par ouvrage concurrent, avec la liste complète des noms en collision.
    groupes: dict[tuple[str, str], list[str]] = {}
    for nom, reps in deja.items():
        for rep in sorted(set(reps)):
            groupes.setdefault((mes_noms[nom], rep), []).append(nom)
    reperes = {eq.ident: ouvrage.repere(eq) for eq in ouvrage.equipements}
    anomalies = []
    for (ident, rep), noms in sorted(groupes.items(), key=lambda g: (reperes.get(g[0][0], ""), g[0][1])):
        anomalies.append(Anomalie(
            "Erreur", reperes.get(ident, "Ouvrage"),
            f"{len(noms)} nom(s) aussi employé(s) par l'ouvrage {rep} du même programme automate "
            f"« {ouvrage.nom_projet.strip()} » : {', '.join(sorted(noms))}. Arbitrage nécessaire : mettre le lieu "
            "dans les noms ou renuméroter l'un des ouvrages. Aucun renommage automatique.", ident, "Variables"))
    return anomalies
