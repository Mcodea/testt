# Comparaison de trois stratégies de rapprochement — ouvrage fictif

**Méthode d'évaluation :** vérité de référence enregistrée dans les fichiers `verite_reference.json` ; pour chaque signal présent, seule la première proposition est comparée au nom source attendu.

- **Précision** : bonnes propositions / toutes les premières propositions émises sur des signaux réellement présents.
- **Rappel / taux de réussite** : bonnes propositions / total des correspondances réelles attendues.
- **Couverture** : signaux présents pour lesquels au moins un candidat a été proposé.
- **F1** : moyenne harmonique de la précision et du rappel.
- **Faux positifs sur absents** : suggestions faites pour des signaux volontairement absents de la vérité de référence.
- **Ambiguïté** : premier candidat très proche d'un deuxième (différence de score < 8 points).

Le score de classement des candidats **n'est pas une probabilité** de réussite ; chaque correspondance reste à confirmer par un automaticien.

## Résultats par jeu

### Jeu initial
5 équipements, 27 déclarations source, 4 E/S documentaires, 18 liens réels et 3 signaux absents.

| Méthode | Bonnes | Fausses | Non retrouvées | Réussite / rappel | Précision | F1 | Faux sur absents |
|---|---:|---:|---:|---:|---:|---:|---:|
| Programme seul | 5 | 0 | 13 | 27.8% | 100.0% | 43.5% | 0 |
| Catalogue → programme | 15 | 0 | 3 | 83.3% | 100.0% | 90.9% | 0 |
| Méthode hybride | 18 | 0 | 0 | 100.0% | 100.0% | 100.0% | 0 |

### Jeu difficile
5 équipements, 29 déclarations source, 3 E/S documentaires, 18 liens réels et 3 signaux absents.

| Méthode | Bonnes | Fausses | Non retrouvées | Réussite / rappel | Précision | F1 | Faux sur absents |
|---|---:|---:|---:|---:|---:|---:|---:|
| Programme seul | 0 | 0 | 18 | 0.0% | n.d. | 0.0% | 0 |
| Catalogue → programme | 10 | 1 | 7 | 55.6% | 90.9% | 69.0% | 2 |
| Méthode hybride | 12 | 1 | 5 | 66.7% | 92.3% | 77.4% | 2 |

## Bilan agrégé (sur les deux jeux fictifs)

| Méthode | Bonnes / liens réels | Taux de réussite | Précision | F1 | Faux sur signaux absents |
|---|---:|---:|---:|---:|---:|
| Programme seul | 5/36 | 13.9% | 100.0% | 24.4% | 0/6 |
| Catalogue → programme | 25/36 | 69.4% | 96.2% | 80.6% | 2/6 |
| Méthode hybride | 30/36 | 83.3% | 96.8% | 89.6% | 2/6 |

## Interprétation et limites

- Les méthodes sont comparées sur **les mêmes variables sources, le même catalogue et les mêmes signaux attendus**. Seule la méthode hybride utilise en plus la liste documentaire d'E/S.
- Les deux jeux ont été **construits pour le développement** : ce ne sont pas des échantillons aléatoires représentatifs d'ouvrages réels ; une note de performance industrielle ne peut pas en être déduite.
- Les nombreux signaux optionnels du catalogue non présents dans la vérité de référence ne sont pas comptés comme des omissions ; seules les 18 correspondances attendues par jeu sont évaluées.
- L'approche hybride détecte davantage de correspondances, mais les **faux positifs et les absences persistent** sur le jeu difficile ; les commandes et réglages exigent une validation renforcée.
- Le score n'est pas une probabilité calibrée ; 100/100 ne signifie pas validation à 100 %.
- Un export de variables n'établit pas à lui seul la chaîne logique entre une E/S et une variable mémoire, ni l'accessibilité TOPKAPI.
- Une validation indépendante devra utiliser plusieurs véritables exports industriels anonymisés, avec une vérité de référence établie manuellement **avant** l'exécution de la comparaison.

## Reproduction

Depuis la racine du projet : `py comparer_les_methodes.py`, puis `py -m unittest discover -s tests -v`.
