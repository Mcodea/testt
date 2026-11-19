# Standards d'ingénierie (étape 1)

Décision du 19/11/2026. À la création d'un ouvrage, on choisit le standard d'ingénierie du client. Pour éviter la
multiplication des profils, un standard n'est pas un bloc monolithique : c'est un **assemblage nommé de briques**,
une par famille. Plusieurs clients peuvent ainsi partager une même brique.

| Famille | Brique du « Standard initial » |
| --- | --- |
| Référentiel métier | Référentiel publié de l'atelier (bibliothèque existante, versionnée) |
| Charte de nommage | Charte OGIAS : lieu sur 4, type sur 2, numéro de 01 à 99 |
| Plan d'adressage | Plan mémoire par défaut (%MW par famille), décalage Modbus 0 |
| Chaîne d'outils | Supervision TOPKAPI, aucune IHM (l'automate reste choisi pour chaque ouvrage) |

Règles validées :
- les réglages du standard sont **copiés** dans l'ouvrage à sa création, avec le nom et la version du standard ;
- un ouvrage déjà créé n'est **jamais modifié automatiquement** ;
- le bloc « Outils d'ingénierie » de l'ouvrage affiche « Créé selon le standard … », signale « le standard a évolué
  depuis » et liste les réglages modifiés localement.

Étape 1 (cette livraison) :
- l'écran « Standards d'ingénierie » (explorateur, menu Outils) ; il est en lecture seule ;
- un seul standard, le « Standard initial », qui reproduit exactement le comportement d'avant : aucun ouvrage ne
  change ;
- le choix du standard dans le formulaire de création. Un standard inconnu ou archivé est refusé sans rien écrire.
  Les ouvrages créés avant les standards sont comptés à part et restent tels quels.

Étapes suivantes :
- **Étape 2.** Bibliothèques de plans d'adressage et de chaînes d'outils, pour créer un deuxième standard. Le bouton
  « Appliquer un standard » remplacera « Reprendre les réglages d'un autre ouvrage ».
- **Étape 3.** Bibliothèque de chartes de nommage, à partir d'une charte réelle d'un autre client fournie en exemple.

Fichier : `standards_ingenierie.json` dans le dossier de données de l'atelier. Il est écrit de façon atomique ; s'il
est illisible, il n'est jamais écrasé.

Vérifications :
- 765 essais du moteur, dont `tests/test_standards.py` ;
- 107 essais navigateur, dont `test_standards_ingenierie_ecran_et_creation` ;
- ruff, mypy ;
- audit des données : 0 détection ;
- accessibilité, nouvel écran compris : 0 écart ;
- registre des commandes : aucune disparition non déclarée.
