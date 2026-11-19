# Grille d'ingénierie (lot 5)

C'est la fenêtre « Engineering » de Typical Manager (grille façon tableur, colonnes d'attributs, modification en
masse), à la mesure d'OGIAS.

On l'ouvre par l'explorateur › Ouvrage › Grille d'ingénierie, ou par le menu Ouvrage.

- **Contenu.** Une ligne par équipement de l'ouvrage, dans l'ordre des repères. Colonnes : repère (lien vers la
  fiche), type, désignation, modèle, UF, local, attributs de l'atelier, contrôles. Les contrôles comptent erreurs et
  alertes, avec le détail au survol.
- **Vues.** Identification, Attributs, ou Tout. Un filtre texte (repère, désignation, local, valeurs) et un filtre
  par type.
- **Saisie dans la cellule.** Désignation, UF, local et attributs sont enregistrés au changement. Une valeur
  refusée est rétablie, avec son motif. Un attribut sans objet pour le type affiche « — ».
- **Modification en masse.** On coche des lignes (ou tout, selon le filtre), on choisit une colonne et une valeur,
  puis « Appliquer à la sélection ».
  - Une confirmation dit ce qui va changer.
  - C'est tout ou rien : chaque équipement est contrôlé avant la première écriture.
  - Le compte-rendu indique les modifiés, ceux déjà à cette valeur, et ceux sans objet pour leur type.
- **Excel.** « Exporter » et « Importer une liste… » ouvrent l'aller-retour comparé du lot 2, avec les colonnes
  d'attributs.

Règles de sécurité :

- **Colonnes en lecture seule.** Type, numéro et modèle ne se modifient pas dans la grille : ils changent signaux,
  noms et adresses. Ils se changent sur la fiche de l'équipement.
- **Validation des équipements.** Les changements de la grille ne font jamais repasser un équipement « à valider ».
- **Ouvrage validé.** Une désignation, une UF ou un local modifié le fait repasser « à contrôler », car ces
  champs figurent dans des documents ; un attribut, non.
- **Aller-retour Excel.** Il suit maintenant la même voie pour ces champs. Seul un changement de modèle y remet
  l'équipement « à valider ».

Vérifications :

- 807 essais du moteur, dont `tests/test_grille.py` (3 essais) ;
- 114 essais navigateur, dont `test_grille_d_ingenierie` ;
- ruff, mypy ;
- audit des données : 0 détection ;
- accessibilité, grille comprise : 0 écart.

Captures (ouvrage et attributs fictifs) : `grille_clair.png`, `grille_sombre.png`, `confirmation_masse.png`,
`apres_masse.png`.
