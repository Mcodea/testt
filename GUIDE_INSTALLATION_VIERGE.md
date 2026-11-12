# SOREP — Installation propre, sans donnée de projet

## Contenu de cette livraison

- Au premier démarrage : **0 ouvrage**, **0 équipement saisi**, **0 variable enregistrée**, **0 adresse affectée** et **aucun résultat de test affiché**.
- Aucun projet d'exemple, aucune table d'exemple, aucun fichier de validation ou PDF fictif dans le ZIP de l'application.
- Un **référentiel générique** de types et signaux reste fourni pour permettre de créer rapidement des équipements. Il ne constitue pas un ouvrage, une donnée de terrain ou une affectation d'adresse.
- Le moteur métier, les contrôles, le parcours neuf/existant et les fonctionnalités restent présents.

## Pour ouvrir SOREP sous Windows

1. Décompresser le dossier complet.
2. Dans PowerShell, depuis le dossier qui contient `lancer_qt.py` :

```powershell
py -m pip install -r requirements-qt.txt
py lancer_qt.py
```

Ou double-cliquer sur `OGIAS.bat`.

## Où sont enregistrés les NOUVEAUX ouvrages ?

Par défaut : `%LOCALAPPDATA%\SOREP\GenerateurVariables_Atelier\Projets`.

Cette racine est indépendante du précédent espace `%LOCALAPPDATA%\SOREP\GenerateurVariables`.
Au premier démarrage, le nouveau dossier est vide. Au fil du travail, les projets nouvellement créés y restent enregistrés : l'application ne les réinitialise **pas** à chaque ouverture.

Les anciens fichiers ne sont **pas effacés**. Pour récupérer un ancien projet volontairement, utiliser **Mes ouvrages → Importer d'anciens projets**, après l'avoir vérifié.

Si la variable d'environnement `SOREP_DATA_DIR` est définie sur le PC, elle sélectionne explicitement un autre espace de travail ; SOREP y affiche les projets déjà présents. Pour démarrer dans un espace vide, supprimez cette surcharge ou choisissez un dossier vide.

## Séparation des données

- `genvar/data/catalogue_defaut.json` : **modèles génériques** du logiciel, modifiables et jamais appliqués comme ouvrage réel par défaut.
- `Projets/*.ouvrage.json` : ouvrages créés par l'utilisateur, jamais inclus dans la distribution vierge.
- `Exports/` : fichiers produits par l'utilisateur, jamais inclus.
- Les jeux fictifs, corrigés et rapports de test sont conservés uniquement dans l'archive **SOREP_QUALITE_TESTS_SEPARES.zip** et **ne sont pas installés avec l'application**.

## Limites de validation

Les tests du moteur Python sont exécutables dans la distribution de développement séparée. L'affichage PySide6 et les exports constructeurs restent à vérifier sur le poste Windows et dans les applications industrielles cibles.
