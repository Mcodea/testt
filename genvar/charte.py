"""Charte de nommage de l'ouvrage, en un seul endroit (19/11/2026).

Ces règles étaient répétées dans une dizaine d'endroits (moteur, serveur, référentiel d'identification). Elles sont
regroupées ici SANS changer leur effet : c'est le préalable pour les rendre réglables par maître d'ouvrage, le jour
où une charte réelle d'un autre maître d'ouvrage servira d'exemple (rien n'est supposé d'ici là).

Repère d'un ouvrage : lieu (4) + code d'ouvrage (2) + numéro (2), ex. ATMS RV 01.
"""
from __future__ import annotations

import re

LIEU = r"[A-Z0-9]{4}"                        # lieu : 4 lettres majuscules ou chiffres, ex. ATMS
CODE_OUVRAGE = r"[A-Z]{2}"                   # type d'ouvrage : 2 lettres majuscules, ex. RV
NUMERO_OUVRAGE = r"(?:0[1-9]|[1-9][0-9])"    # numéro : 01 à 99
SOUS_ENSEMBLE = r"[A-Z0-9]{2}"               # sous-ensemble : 2 lettres majuscules ou chiffres
REVISION = r"[A-Z0-9]{1,4}"                  # révision documentaire : 1 à 4 caractères

# Saisie champ par champ (API /api/definir) : plus permissive que le reste, telle qu'elle existait. ÉCART CONNU
# (19/11) : un code d'ouvrage avec chiffres y est accepté, puis signalé par R-OUV-03. Conservé à l'identique.
LIEU_SAISIE = r"[A-Za-z0-9]{4}"
CODE_OUVRAGE_SAISIE = r"[A-Za-z0-9]{2}"


def conforme(motif: str, valeur) -> bool:
    return bool(re.fullmatch(motif, str(valeur or "")))
