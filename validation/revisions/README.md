# Indices de livraison et liste des modifications (22/11/2026)

Objectif 2 de la feuille de route (`docs/FEUILLE_DE_ROUTE.md`) : le marquage des révisions des outils d'ingénierie.
Quand l'indice B d'un ouvrage est livré après l'indice A, le client et l'automaticien savent exactement ce qui a
changé.

## Fonctionnement (Recette et livrables › Indices de livraison)

1. **Livrer l'indice** courant de l'ouvrage (celui de sa fiche) avec l'objet de la livraison et, si voulu, son
   auteur. OGIAS fige une **photo** de l'ouvrage, enregistrée dans son fichier avec une empreinte SHA-256 :
   identification (lieu, type, numéro, libellé, automate, supervision, IHM, décalage Modbus), équipements, E/S
   physiques (nom, nature, type, adresse, carte, voie, désignation), variables (nom, famille, type, adresse,
   registre, libellé de supervision, alarme, unité) et cartes d'E/S.
2. Un indice livré **ne change plus** : livrer de nouveau est refusé tant qu'on n'est pas passé à l'indice suivant
   (A → B, 1 → 2, A9 → A10 ; une suite non évidente se saisit dans la fiche).
3. **Liste des modifications** entre le dernier indice livré et l'état en cours, ou entre deux indices livrés au
   choix : chaque élément ajouté, supprimé ou modifié, champ par champ (valeur à l'indice de départ, valeur à
   l'arrivée), avec une synthèse par catégorie.
4. Les éléments sont rapprochés par leur **identité stable** (équipement, signal de l'équipement, emplacement de
   carte), pas par leur nom : renuméroter une vanne apparaît comme une modification de son repère et des noms de ses
   E/S, jamais comme une suppression suivie d'un ajout.
5. Livrables : classeur Excel « Liste des modifications » (feuilles Modifications, Synthèse, Indices) depuis l'écran,
   et pièce de « Tous les livrables » (`04_Documents/`). Sans indice livré, la pièce est listée au journal comme non
   produite avec son motif.

## Vérifications

- `tests/test_revisions.py` (10 tests) : livraison et refus de relivrer, indice suivant, enregistrement et relecture
  du fichier, ancien fichier sans indices, aucune modification juste après livraison, ajout / suppression /
  modification / renommage rapprochés par identité, décalage Modbus visible sur les registres, comparaison entre
  deux indices livrés, refus sans indice, Excel et génération groupée, API.
- `tests_web/test_coque_bureau.py::test_indices_de_livraison` : livrer A, passer à B, modifier un équipement, liste
  affichée et export disponible.

## Capture (ouvrage fictif de démonstration)

`indices_et_modifications.png`.
