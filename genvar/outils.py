"""Outils d'ingénierie de l'ouvrage (orientation du 18/11/2026 : un logiciel d'ingénierie universel).

À chaque ouvrage, l'utilisateur choisit les outils réellement utilisés : automate (source d'acquisition),
télégestion, supervision, IHM. OGIAS en déduit les règles qui s'appliquent et les livrables proposés, au lieu de
supposer un seul jeu d'outils. Les conventions du maître d'ouvrage (charte de nommage, plages %MW) sont un autre
sujet : elles ne dépendent d'aucun outil.

Ce module ne décrit QUE des contraintes déjà établies dans OGIAS (aucune capacité de produit inventée) :
- M340 / M580 : une valeur 32 bits doit commencer sur une adresse %MW paire ;
- TOPKAPI : libellé de 40 caractères au plus (format relevé sur un projet réel).
Un outil non décrit n'entraîne aucune contrainte : OGIAS ne devine pas.
"""
from __future__ import annotations

SUPERVISION_DEFAUT = "TOPKAPI"          # comportement d'OGIAS avant le 18/11 : supervision TOPKAPI supposée
LIBELLE_MAX_TOPKAPI = 40


def gamme_automate(ouvrage) -> str | None:
    """Gamme reconnue de la source d'acquisition (M340, M580, S4W, STB) ou None ; « Sch - M340 » → « M340 »."""
    from .materiel import gamme
    return gamme(getattr(ouvrage, "automate", ""))


def adresse_paire_32_bits(ouvrage) -> bool:
    """Vrai si l'automate impose une adresse paire aux valeurs 32 bits (M340 et M580)."""
    return gamme_automate(ouvrage) in ("M340", "M580")


def est_topkapi(ouvrage) -> bool:
    return (getattr(ouvrage, "supervision", SUPERVISION_DEFAUT) or "").strip().upper() == "TOPKAPI"


def libelle_max(ouvrage) -> int | None:
    """Longueur maximale du libellé de supervision, si la supervision choisie en impose une."""
    return LIBELLE_MAX_TOPKAPI if est_topkapi(ouvrage) else None


def resume(ouvrage) -> dict:
    """Outils choisis et contraintes qui en découlent, pour l'interface."""
    contraintes = []
    if adresse_paire_32_bits(ouvrage):
        contraintes.append(f"{gamme_automate(ouvrage)} : valeur 32 bits sur une adresse %MW paire.")
    if libelle_max(ouvrage):
        contraintes.append(f"TOPKAPI : libellé de {libelle_max(ouvrage)} caractères au plus.")
    return {"automate": getattr(ouvrage, "automate", ""), "gamme": gamme_automate(ouvrage) or "",
            "telegestion": getattr(ouvrage, "communication", ""), "supervision": getattr(ouvrage, "supervision", ""),
            "ihm": getattr(ouvrage, "ihm", ""), "contraintes": contraintes}
