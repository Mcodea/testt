# Notes de version — OGIAS 1.0

> Version préparée avant la livraison. Le numéro (`genvar/__init__.py`) est encore 0.32 ; il passera à 1.0.0 avec
> l'étiquette `v1.0.0` après la recette finale (cahier V1-10-19 à 21). Détail complet : `CHANGELOG.md`.

## Ce qu'est OGIAS

OGIAS prépare les ouvrages d'automatisme et exporte **trois familles de fichiers** : la liste des E/S physiques de
chaque automate, la télétransmission de chaque supervision, et l'IHM. Les autres documents sont les documents d'études
d'OGIAS lui-même. Le logiciel n'est lié à aucun constructeur : chaque client déclare son automate, ses gammes de
matériel et ses formats.

## Nouveautés

- **Interface industrielle** : menus, ruban, explorateur, panneau de sortie ; accessibilité WCAG AA vérifiée.
- **Formats d'export appris** : on importe une fois un fichier d'exemple (CSV, TXT, classeur Excel), OGIAS en retient la
  structure ; chaque export produit est relu, puis qualifié après un premier essai réel.
- **Gammes de matériel ouvertes** : déclarées par l'atelier pour tout automate. Schneider et Siemens (S7-1500 livrée,
  références vérifiées).
- **Livrables** : modèles à variables, génération groupée avec journal, cahiers d'essais FAT / SAT.
- **Ordre d'export** des variables par équipement, sans jamais modifier une adresse.
- **Sécurité du travail** : annuler / rétablir, copies de sauvegarde, verrou d'ouvrage, journal technique.
- **Indices de livraison** et liste des modifications entre deux indices.
- **Licences** : aucune bibliothèque AGPL livrée (lecture des PDF par pdfminer.six).

## Limites connues à la livraison

- Les exports **TIA Portal, Control Expert et TOPKAPI** n'ont pas encore été essayés sur les logiciels réels :
  `COMPATIBILITE.md` ne déclare donc aucune compatibilité. Un fichier d'exemple réel de chaque logiciel est attendu.
- **PySide6 (LGPL)** : l'ancienne interface Qt reste à retirer de la version vendue (décision attendue).
- Le tableau de conformité (`ETAT_TRAVAIL.md`) n'est pas entièrement « fait » : il fait foi de l'avancement.
- Protection de la branche principale et exécutions GitHub Windows / Linux : à vérifier côté GitHub.

## Mise à jour

Les ouvrages sont stockés hors du programme (`GUIDE_ADMINISTRATEUR.md`) : une mise à jour n'y touche pas. Faire une
copie de sauvegarde avant toute ouverture d'un ouvrage ancien.
