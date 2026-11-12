# Module 2 « Référentiel métier » — remplacé par le dépôt unifié (V0.28)

Le module `genvar/referentiel_v2` (cycle brouillon → validation → publication limité aux modèles) a été fusionné
le 9 novembre 2026 dans **un seul dépôt** : `genvar/referentiel_depot.py`. Ce dépôt applique le même cycle à tout
le référentiel (types, signaux, règles, modèles, lignes).

Les garde-fous du module 2 sont repris et testés dans `tests/test_referentiel_excel.py` (classe `TestCycle`) :
- brouillon unique ;
- validation annulée par toute modification ;
- publication sous verrou, avec retour arrière en cas d'échec ;
- fichier en service modifié hors du cycle détecté et bloquant ;
- classeur avec formule, macro ou lien externe refusé ;
- restauration sous forme de nouveau brouillon ;
- éditeur historique en lecture seule une fois le cycle commencé ;
- paramètres d'installation interdits dans un modèle.

L'API `/api/referentiel-v2/*` et la ligne de commande du module 2 sont retirées. Les remplacent :
- l'écran Référentiel ;
- `/api/referentiel/cycle` et `/api/referentiel/cycle/action` ;
- `/api/referentiel/vue`.
