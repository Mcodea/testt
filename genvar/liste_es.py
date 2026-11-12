"""Import prudent d'une liste d'E/S existante, source documentaire facultative.

Aucune déduction des liens logiques automate : cette liste fournit seulement
repère, fonction, adresse physique et éventuellement référence croisée explicite.
"""
from pathlib import Path
from .import_sources import charger_table
from .rapprochement import EntreePhysiqueSource, normaliser

ALIASES = {
    "nom": ("nom", "nom_es", "variable_es", "symbole", "point_es", "repere_es"),
    "adresse": ("adresse", "adresse_es", "adresse_physique", "voie", "localisation"),
    "equipement": ("equipement", "repere_equipement", "equipement_lie", "repere"),
    "fonction": ("fonction", "signal", "information", "designation"),
    "commentaire": ("commentaire", "libelle", "description"),
    "variable_liee": ("variable_liee", "variable_automate", "reference_croisee"),
}


def charger_liste_es(chemin):
    if Path(chemin).suffix.lower() not in (".xlsx", ".csv", ".txt"):
        raise ValueError("Liste d'E/S : seul Excel (.xlsx) ou CSV/TXT est accepté.")
    entetes, lignes = charger_table(chemin)
    # Le lecteur de variables suppose une colonne adresse ; elle est facultative
    # pour une liste d'E/S documentaire. Récupérer alors les véritables en-têtes.
    if entetes and all(x.startswith('Colonne ') for x in entetes) and lignes:
        possibles = {normaliser(x) for x in lignes[0]}
        if {'nom', 'equipement', 'fonction'}.issubset(possibles):
            entetes, lignes = lignes[0], lignes[1:]
    normalized = [normaliser(x) for x in entetes]
    positions = {}
    for key, aliases in ALIASES.items():
        hits = [i for i, name in enumerate(normalized) if name in aliases]
        if len(hits) > 1:
            raise ValueError(f"Liste E/S : plusieurs colonnes correspondent à {key}.")
        if hits:
            positions[key] = hits[0]
    if not {"nom", "equipement", "fonction"}.issubset(positions):
        raise ValueError("Liste E/S : colonnes Nom, Equipement et Fonction obligatoires ; aucune E/S n'a été importée.")
    resultat, vus = [], set()
    for i, row in enumerate(lignes, 2):
        values = {champ: (str(row[idx]).strip() if idx < len(row) else "")
                  for champ, idx in positions.items()}
        nom, equip, fonction = (values.get(k, "") for k in ("nom", "equipement", "fonction"))
        if not (nom and equip and fonction):
            raise ValueError(f"Liste E/S ligne {i} : nom, équipement ou fonction manquant.")
        if normaliser(nom) in vus:
            raise ValueError(f"Liste E/S ligne {i} : nom de point en double ({nom}).")
        vus.add(normaliser(nom))
        resultat.append(EntreePhysiqueSource(**values))
    if not resultat:
        raise ValueError("Liste E/S : aucune ligne exploitable.")
    return resultat
