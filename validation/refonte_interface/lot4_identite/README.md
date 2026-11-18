# Lot 4 — Identité : le fil de l'information (18/11/2026)

La signature d'OGIAS : une information se suit sans rupture de l'équipement jusqu'à la supervision.

## Fil de l'information

Sous les onglets de documents, dès qu'un équipement est sélectionné (fiche équipement) ou qu'une variable est ouverte
(Variables), une barre montre sa chaîne complète, avec l'état de chaque maillon :

| Maillon | Exemple (projet fictif) | Clic |
| --- | --- | --- |
| Équipement | Équipement PM01 · paramétrage validé | Fiche de l'équipement |
| E/S physiques | 3 E/S physiques · contenu validé | Liste des E/S filtrée sur l'équipement |
| Carte et voies | Carte 0.2 · voies 30 à 32 · 3 voie(s) à valider | Matériel, voies de l'équipement |
| Variables | 10 variables · 10 adresse(s) à valider | Variables de l'équipement |
| Supervision | 10 libellés | Variables de l'équipement |

Vert = validé, orange = à reprendre, gris = pas encore concerné ; le maillon de l'écran affiché est surligné.
Lecture seule côté serveur (`/api/fil`) : aucun calcul d'adressage n'est lancé, seules les adresses posées et validées
sont comptées (`tests/test_fil_information.py`).

## Symboles OGIAS

Cinq pictogrammes propres, dérivés du motif du logo (nœud – bloc – nœud) : équipement, E/S, carte, variable,
supervision, plus la recette. Ils marquent les maillons du fil, les étapes du parcours dans l'explorateur et les
onglets de documents.

## Vérification

- Tests moteur : 732 réussis (dont 3 pour le fil) ; essais navigateur : 99 réussis (dont `test_fil_de_l_information`) ;
  ruff ; mypy ; contrôle des scripts.
- Registre des commandes comparé au lot 0 : aucune commande disparue.
