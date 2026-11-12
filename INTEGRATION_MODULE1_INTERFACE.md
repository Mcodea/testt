# OGIAS V0.26 — Intégration du module 1 à l'interface

## Utilisation

1. Lancer `OGIAS.bat`, puis ouvrir un ouvrage créé.
2. Dans **Inventaire**, cliquer sur **Importer une liste…**.
3. Sélectionner la nature : inventaire, variables existantes ou liste d'E/S existante.
4. Charger un fichier compatible (CSV, TXT, XLSX, XLSM, ODS ou SCY textuel).
5. Examiner les totaux, les diagnostics par ligne et le statut de l'import.
6. Corriger le fichier source si des erreurs bloquantes sont présentes ; recharger le fichier.
7. Cliquer sur **Confirmer l'import** uniquement lorsque la prévisualisation est intégrable.

## Garanties et limites

- Aucun ajout au projet n'est effectué pendant l'analyse.
- Un doublon, une erreur de contenu ou une anomalie structurelle bloquante interdit toute intégration.
- Les équipements déjà enregistrés ne sont pas modifiés par un réimport.
- Les données importées sont appliquées au moyen du moteur `genvar.inbound.stage_import`, sur une copie de session.
- L'intégration est confirmée par l'utilisateur, puis enregistrée via le mécanisme existant de sauvegarde OGIAS.
- Les fichiers sources restent inchangés.
- La fenêtre affiche les 250 premières lignes et les statistiques de l'ensemble des lignes contrôlées.
- L'import est lié à l'état du projet au moment de l'aperçu ; un projet ou un fichier changé exige une nouvelle analyse.
- Un seul aperçu est conservé temporairement ; un nouveau remplace l'ancien.
- L'intégration des formats pris en charge ne prouve pas la compatibilité industrielle avec Control Expert, TOPKAPI ou S4W-Tools.
- L'interface a été vérifiée au niveau de la syntaxe JavaScript et des points de connexion Python ; la recette visuelle sur Windows est encore à effectuer.

## Tests

`python -m pytest -q`

Le nouveau fichier `tests/inbound/test_web_integration.py` vérifie l'aperçu en lecture seule,
la confirmation, le blocage des doublons, le retour arrière en cas d'échec de sauvegarde,
et la révocation des aperçus antérieurs.

## Compatibilité

Aucune donnée de démonstration ni aucun ouvrage réel n'a été préchargé. Les anciens composants d'import restent présents dans le moteur pour rétrocompatibilité mais la fenêtre Importer utilise désormais le module Inbound/Validation.
