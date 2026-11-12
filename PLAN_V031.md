# OGIAS V0.31 — Plan de refonte (base V0.30 uniquement)

## Référence et contraintes
- Trois maquettes utilisateur : tableau de bord, variables et détail de variable.
- Couche métier `genvar/` et API existantes préservées ; toute proposition d'adresse doit passer par le plan du moteur et son empreinte.
- Aucun adressage historique modifié dans un projet EXISTANT.
- Pas de livraison si un critère de recette manque.

## Audit V0.30
- Accueil : blocs de choix et table génériques, sans vraie hiérarchie ni dashboard d'un ouvrage.
- Création : surcharge de textes d'assistance et de formulaires.
- Équipements : arborescence fixe trop large, panneaux et onglets multiples.
- Liste E/S : éléments de filtre et panneaux présents, mais barre haute trop volumineuse.
- Matériel : table et configuration contraintes par trois zones permanentes.
- Variables : trois vues séparées ; l'application de propositions exige de changer d'onglet ; panneau de détail trop dense.
- Recette : contrôles fonctionnels existants mais présentation administrative.
- Référentiel : ruban et panneaux superposés, fonctions trop dispersées.
- Modales : style V0.30 à harmoniser.

## Ordre de mise en œuvre
1. Tokens et nouvelle coque de navigation, suppression du ruban documentaire.
2. Dashboard et table Variables, intégration du parcours réel calculer → aperçu → appliquer → valider.
3. Autres écrans et modales, sans fonctions perdues.
4. Tests d'interface, accessibilité, captures 1920×1080 et 1366×768.
5. Comparatif des exports, suite pytest, audit de qualité et livraison unique.

## État initial
- Archive officielle `OGIAS_V030.zip` décompressée dans un répertoire de travail séparé.
- `python -m pytest -q` : **373 passed, 25 skipped**.
- Les trois maquettes sont des références visuelles, et non des données réelles.
