# Refonte visuelle industrielle — 12 novembre 2026

Consigne du chat exécutée après le lot Variables `7466f35`, sur `Mcodea/testt`, branche `claude/referentiel-v2`.
Ce dossier conserve les captures non retouchées de la vraie application HTTP.
Les ouvrages fictifs isolés sont ceux des tests, servis par le backend existant ;
aucun tableau, tag ni état de démonstration n’a été injecté dans les composants.

## Décisions de présentation

- La demande du 12/11 remplace la palette lavande et les formes décoratives des
  anciennes maquettes. Les originaux ne sont pas modifiés. `comparaison.html`
  présente les trois références et les captures sombres, puis les autres écrans.
- Le thème choisi et son stockage existants sont conservés. Le bouton lune
  donne la palette sombre demandée ; le bouton soleil retrouve une variante
  claire technique. Aucun changement de la préférence par défaut ni de l’état.
- Palette sombre exacte : fond #0B0F19, navigation/détails #0F1623, cartes
  #111827, bordures #1E293B. Aucun dégradé décoratif ni ombre floue. Le graphique
  de recette, quand un taux réel existe, garde sa représentation des données.
- Navigation de 188 px avec libellés sur grand écran, rail de 80 px à 1366 px,
  mêmes routes et gestionnaires. Les commandes restent dans leurs conteneurs
  existants et leurs menus ; aucune commande métier dupliquée.
- Variables : lignes de 44 px et sélection de 24 px, en-têtes fixes, panneaux
  de détail de 320/290 px. Tableaux métier resserrés, nombres tabulaires.
- Inter et JetBrains Mono déjà embarquées sont réutilisées. Types, sources,
  adresses, voies, cartes, codes et aperçus utilisent la chasse fixe.
- Vert Schneider uniquement sur les exports Control Expert identifiés, cyan
  sur les panneaux S4W déjà identifiés, ambre sur l’export TOPKAPI. Violet pour
  les propositions/points à vérifier, rouge pour les erreurs. Des nuances de
  texte plus claires assurent la lisibilité sur fond sombre. Aucune IA ajoutée.
- Racks : grille existante, positions libres en pointillés, jauges conservées,
  dépassement signalé par bordure rouge à partir de l’état existant. La modale
  des voies différencie les voies occupées/libres et conserve la réaffectation.
  Aucun conflit n’est fabriqué pour la capture ; le cas de dépassement matériel
  n’est pas revendiqué comme scénario de qualification.

## Périmètre strict de ce lot

- `sorep_web/static/industrial-ui.css` : nouvelle couche de présentation.
- `index.html` : chargement de la feuille, uniquement.
- `v031-ui.js` : libellés et liens des routes existantes dans le gabarit latéral,
  sans changement des fonctions, événements, identifiants ou états.
- `app.js` : deux attributs class de présentation, fondés sur les booléens S4W
  déjà calculés. Aucun appel API, calcul ni structure modifié.
- `tests_web/test_design_industriel.py` : sept tests sur le serveur réel, avec
  projets temporaires ; captures de sept écrans et du détail en trois tailles.
- `test_variables_v031.py` : seule attente visuelle adaptée, 188 px au lieu
  des anciens 80 à 1920 px. Les assertions métier sont conservées.

Le moteur, le serveur, les données, les exports, les dépendances, les tests
unitaires et les workflows restent identiques à `7466f35`. Le lot Variables
précédent est un commit distinct : ses correctifs de focus et d’Échap ne font
pas partie de cette refonte visuelle. Les noms historiques issus du référentiel
restent affichés tels qu’ils sont fournis ; aucun renommage A1 n’est appliqué.

## Report sur le dépôt public

La première destination avait été confondue avec une branche de l’ancien dépôt.
Le report applique uniquement des différences de fichiers UI et tests ; aucun
historique privé n’est importé. La base publique de Claude `085b1c7` est conservée,
avec les nouveaux catalogues matériels, composition, nomenclature et correctifs
d’exports. Le commit racine public reste `4d084b4`. Le domaine moteur est inchangé.

Le nouveau test de composition vérifie aussi la grille, les références réelles
des cartes, la nomenclature et les blocs « à choisir » sans écriture ; les deux
captures supplémentaires montrent la composition et le rack de cette version.

## Preuves

`test_design_industriel.py` vérifie les couleurs réellement calculées, bordures,
polices tabulaires, absence d’ombres, thème persistant, sept écrans sans
débordement global, commandes visibles, raccourcis, en-tête fixe après
défilement, voies occupées/libres, couleurs S4W/Control Expert/TOPKAPI et mention
« non qualifié » conservée. Les projets restent identiques à l’octet après les
interactions ; aucun POST lors des interactions de thème/détail.

Les tests Variables existants gardent les protections contre l’application
d’un aperçu périmé et contrôlent les destinations, valeurs, validations et
colonnes. Les tests d’adoption et du référentiel sont conservés.

Les 730 tests Python et 60 tests navigateur passent ; aucun ignoré.
28 captures sont conservées. Statique, audit données (0/0), dépendances et
sept seuils de performance inchangés passent.

Les résultats finaux figurent dans `verification.json` ; `performance.json`
conserve les mesures et les sept seuils inchangés. Les captures sont indexées
dans `captures.sha256`. Ces preuves Linux/Chromium sont locales : La CI publique complète est active :
https://github.com/Mcodea/testt/actions?query=branch%3Aclaude%2Freferentiel-v2.
La base de Claude a passé le run 43276436661 ; le push de ce lot déclenche sa
propre vérification Windows/Linux, navigateur, qualité et portable.
Aucune qualification Control Expert 14.1, TOPKAPI ou S4W-Tools n’en découle.
