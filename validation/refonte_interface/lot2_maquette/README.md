# Lot 2 — Maquette de la coque de bureau (à valider)

Maquette statique, construite avec les vrais jetons (`ogias.css`) et les données du projet FICTIF de démonstration
(`XTSTRV01`, groupe de pompage PM01). Rien n'est encore branché dans OGIAS : la réalisation attend la validation.

Ouvrir `maquette_coque.html` dans un navigateur, ou voir `maquette_coque_clair.png` et `maquette_coque_sombre.png`.

## Ce qui change par rapport à aujourd'hui

| Zone | Aujourd'hui | Maquette |
| --- | --- | --- |
| Navigation | Barre latérale + fil d'Ariane + frise des étapes + pied d'étape (4 navigations) | Un seul explorateur : le **parcours** (5 étapes et leur état) et l'**arborescence** de l'ouvrage |
| Commandes | Boutons dispersés dans chaque écran | **Barre de menus** et **ruban** par tâche (onglet contextuel de l'élément sélectionné) |
| Travail | Un écran à la fois | **Onglets de documents** : plusieurs équipements ou écrans ouverts |
| Identité | — | **Fil de l'information** : équipement → E/S → carte et voies → variables → supervision, avec l'état de chaque maillon |
| Détail | Fiches et fenêtres | **Inspecteur** : grille de propriétés de la sélection |
| Messages | Bulles qui disparaissent | **Panneau de sortie** (contrôles, journal) avec « Aller à la source », et barre d'état |
| Tableaux | Lignes de 44 px | Lignes de 28 px, en-têtes fixes, filtre, colonnes, copie vers Excel |

## Nouvelle vue proposée : « Fil des informations »

Pour un équipement, une ligne par information avec toute sa chaîne : E/S physique, voie, variable automate, type,
adresse, libellé de supervision et état. C'est la vue qui n'existe dans aucun autre logiciel et qui montre ce
qu'OGIAS fait d'unique.
