# Lot 0 — État de l'interface avant la refonte (18/11/2026)

Référence pour tous les lots suivants. Rien de visible n'a changé dans ce lot.

## Mesures (`inventaire_styles.json`)

| Mesure | Valeur | Cible fin de refonte |
| --- | --- | --- |
| Feuilles de style | 3 (app.css 868 lignes, industrial-ui.css 633, v031.css 350) | 1 |
| Sélecteurs redéfinis dans plusieurs feuilles | 184 | 0 |
| Couleurs écrites en dur dans les feuilles | 487 | 0 hors définition des jetons |
| Couleurs distinctes | 319 | une palette de jetons |
| `!important` | 240 | 0 |
| Tailles de police distinctes | 24 (de 10 à 32 px) | une échelle de 6 |
| Rayons d'angle distincts | 37 | 3 |
| Styles en ligne dans les scripts | 52 | 0 |
| Messages éphémères (`toast`) | 76 appels | remplacés par la barre d'état et le panneau de sortie |

## Captures (`captures/`)

Huit écrans plus la fiche d'un équipement, en thème clair et sombre, 1600 × 900, ouvrage fictif `XTSTRV01`.

## Registre des commandes (`actions.json`)

| Écran | Commandes visibles |
| --- | --- |
| Ouvrages | 5 |
| Tableau de bord | 6 |
| Équipements | 17 |
| Fiche d'un équipement | 15 |
| Liste des E/S | 57 |
| Matériel | 75 |
| Variables | 14 |
| Recette | 14 |
| Référentiel | 8 |

## Défauts constatés, à traiter dans les lots

- **Matériel** : le panneau « Propriétés / Contrôles » recouvre la section Plateforme, Cartes du calcul et Réserve
  (`05_materiel_clair.png`).
- **Variables** : la colonne « Règle » est tronquée à chaque ligne ; le bloc « À vérifier » est coupé en bas
  d'écran (`06_variables_sombre.png`).
- **Tous les écrans** : trois navigations superposées (barre latérale, fil d'Ariane, frise des étapes) et un pied
  d'étape ; la barre latérale répète des entrées (« Ouvrages » et « Équipements » ont la même icône).
- **Liste des E/S** : boutons du ruban grisés sans explication visible.
