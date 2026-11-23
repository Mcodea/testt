# Lot 3 — Composants de bureau (18/11/2026)

Fichier : `sorep_web/static/ogias-composants.js` ; styles dans `ogias.css`. Composants réutilisables par tous les
écrans ; chaque écran les adopte à son tour au lot 5.

| Composant | Ce qu'il apporte |
| --- | --- |
| **Tableau dense** (`data-o-tableau`) | Tri par colonne en trois temps (croissant, décroissant, ordre d'origine) ; filtres par colonne ; colonnes redimensionnables ; sélection multiple (clic, Ctrl, Maj, flèches, Espace, Ctrl A) ; **copie vers Excel** (Ctrl C, texte tabulé, colonne d'actions ignorée) ; lignes de 28 px, en-têtes fixes |
| **Menu contextuel** | Clic droit, touche Menu ou Maj F10 ; copie, tri, filtres ; navigable au clavier |
| **Grille de propriétés** | Groupes repliables, libellé / valeur, chasse fixe pour les repères et adresses, lecture seule distinguée |
| **Raccourcis clavier** | Liste complète par Aide › Raccourcis clavier ou Ctrl / |

Amélioration progressive : les lignes d'un tableau sont déplacées, jamais recréées ; leurs boutons gardent leur
comportement. Les tableaux de saisie (cases à cocher, champs) ne sont pas touchés dans ce lot.

## Tableaux déjà concernés (lecture seule)

Recette (contrôles consolidés) ; Équipements (à valider, répartition par domaine) ; Référentiel (E/S physiques,
informations fonctionnelles, utilisation, différences de révision, codes) ; Matériel (nomenclature, besoins par nature).

## Vérification

- Tests moteur : 729 réussis ; essais navigateur : 98 réussis (dont 5 dans `test_composants_bureau.py` : tri, sélection,
  copie, menu contextuel, filtres, redimensionnement, grille, raccourcis ; aucune écriture dans le projet) ; ruff ;
  contrôle des scripts.
- Registre des commandes comparé au lot 0 : aucune commande disparue.
