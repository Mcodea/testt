# OGIAS V0.29 — Refonte de l'étape 4 Variables / Adressage

## Base et périmètre

- Base unique : `OGIAS_Liste_ES_Interface_Validee.zip`, issue de V0.28 avec l'étape 2 validée.
- L'étape 4 reste constituée de **trois onglets** : **Table d'échange**, **Télétransmission**, **Adressage automatique**. Aucune mémoire indépendante dans un quatrième onglet.
- Référentiel, liste des E/S, Matériel, Recette et moteur Python préexistants conservés.
- **Aucune donnée industrielle réelle** ajoutée à l'application ou aux tests ; exemples fictifs XTST.

## Modifications réellement effectuées

1. `sorep_web/serveur.py` : les GET `/api/variables` et `/api/supervision` exposent, en lecture seule, les informations du moteur central `session.plan_adressage()` : statut, adresse actuelle, proposition, origine, justification, motif et traçabilité lorsqu'elle existe. Aucun calcul de vue ne déclenche une application d'adresse.
2. L'API des variables n'ajoute **aucune E/S physique en tant que variable d'échange**. La source E/S et son éventuelle voie sont présentées séparément, en lecture seule.
3. L'API télétransmission distingue identifiant de point, variable source, adresse mémoire de la source, adresse protocolaire éventuelle et correspondance TR/RTR. **Aucune adresse n'est fabriquée si la convention n'est pas connue.**
4. `sorep_web/static/app.js` : nouveaux tableaux éditoriaux, recherche, filtres par famille/équipement/état, sélection de la ligne entière ou au clavier (Entrée/Espace), panneau de détail repliable, navigation vers la fiche équipement, ruban local simplifié et conservation du pied précédent/suivant.
5. **Adressage automatique** : les fonctions déjà disponibles dans la V0.28 sont conservées (trois niveaux, conflits, besoins matériels simulés, réservations, convention déclarée, empreinte, confirmation avant application, validation tracée). Le bouton « Proposer l'adressage » ouvre la prévisualisation **sans POST**.
6. Adaptation S4W de la présentation : « Identification S4W-Tools non connue », pas de réglage de convention `%MW` Schneider ni de réservation mémoire Schneider proposée sur cet écran. En mode existant, les adresses importées restent en lecture seule.
7. Les contrôles d'étape et la barre des cinq étapes sont préservés, y compris après ouverture/fermeture des panneaux de détail.

## Contrôles

- `python -m pytest -q` : **368 tests réussis, 25 ignorés** (tests ignorés inchangés). Cinq nouveaux tests Python de structure et de non-régression spécifiques à l'étape 4.
- `node --check sorep_web/static/app.js` : syntaxe JavaScript vérifiée.
- Chromium, données exclusivement fictives et réponses API simulées : vues **1280 et 1440 px** pour Table d'échange, Télétransmission et Adressage automatique, ouverture du détail au clavier, filtre texte, maintien du pied de navigation, absence de débordement horizontal et d'erreur JavaScript constatée.
- Scénario S4W vérifié dans Chromium à 1440 px : réglages mémoire `%MW` masqués, identification non connue affichée.
- Test de navigation jusqu'à l'aperçu : **aucun POST généré** (aucune affectation modifiée).

## Limites et qualifications

- Captures navigateur sous Linux/Chromium avec jeu de données et réponses API simulés, **pas** une validation sur poste Windows réel.
- L'application continue à utiliser son interface web locale ; la refonte de l'ensemble des écrans V0.29 reste distincte.
- **Aucun export n'est déclaré qualifié** pour Control Expert, SOFREL S4W-Tools ni TOPKAPI 6.3. L'import des fichiers réels doit être testé dans une copie des logiciels industriels.
- Les affectations ne sont réputées validées industriellement qu'après une vérification humaine et les essais correspondants.

## Reprise et sécurité

Décompresser dans un nouveau dossier ; sauvegarder les fichiers d'ouvrages avant de tester. Les tests ont été réalisés sur des sessions fictives et des répertoires temporaires. Les anciens ouvrages ne sont pas migrés et les adresses historiques ne sont pas réaffectées.
