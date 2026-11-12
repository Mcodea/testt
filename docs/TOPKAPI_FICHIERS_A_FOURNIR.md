# TOPKAPI 6.3 — ce qu'OGIAS sait déjà, ce qu'il faut me transmettre

## 1. Ce qui existe déjà dans OGIAS (vérifié dans le code V0.26)

| Élément | État |
| --- | --- |
| Libellé TOPKAPI par variable (`libelle_topkapi`, 40 caractères au plus, contrôlé en recette) | présent |
| Onglet « Télétransmission et supervision » : nom, famille, adresse %MW, type, libellé | présent, **vue de travail** |
| Export XSY / TXT des variables au format Control Expert V14.1 | présent, conforme à vos exports CE |
| Fichiers d'import `.$$t` « Version 1 » | **lus et écrits** (V0.27), d'après le projet réel transmis le 9 novembre ; import 6.3 non essayé |

Fait utile, publié par l'éditeur : l'autoparamétrage TOPKAPI (module SOFTLINK) sait lire les fichiers
Schneider **.xsy / .scy**, un fichier **.rdl** (liste d'équipements), un fichier **.flc** (export puis
réimport des attributs de variables existantes) et un « format transparent » décrit par AREAL
([fiche AREAL / Scadalliance, 2016](https://www.scadalliance.com/media/pages/produits/logiciels/topkapi-vision/5ca0f29830-1745588752/ft_topkapi_autoparametrage-fr.pdf)).
Le XSY produit par OGIAS pourrait donc déjà servir de source à TOPKAPI. Cette possibilité reste **à vérifier**
sur votre 6.3 et votre licence, parce que SOFTLINK est un module optionnel.

> Mise à jour V0.27 : le projet réel reçu couvre les points 3 et 5 ci-dessous. Restent utiles : la
> version exacte (point 1), un essai d'import du `.$$t` produit par OGIAS dans une COPIE de l'application,
> et la signification des codes de format 102 et 105.

## 2. Fichiers à me transmettre (sur une COPIE de l'application, jamais sur le poste d'exploitation)

| # | Fichier | À quoi il sert | Priorité |
| --- | --- | --- | --- |
| 1 | Version exacte et modules : capture de la fenêtre « À propos » du configurateur, et de la liste des modules ou licences si elle est affichée | savoir si SOFTLINK et ses formats sont disponibles en 6.3 chez vous | indispensable |
| 2 | Export **.flc** des variables d'une application (ou de l'équivalent proposé par votre version) | voir le format que TOPKAPI exporte puis réimporte lui-même : c'est la cible la plus sûre pour OGIAS | indispensable |
| 3 | Les fichiers **.imp, .$$t, .txt** déjà en votre possession, chacun avec une ligne qui dit d'où il vient (menu, date, version) | savoir s'il s'agit d'exports d'une ancienne version, d'imports SOFTLINK ou de fichiers internes | utile |
| 4 | Captures de l'assistant SOFTLINK : la liste des sources proposées, puis l'écran de correspondance des champs pour une source Schneider | savoir quelles colonnes TOPKAPI attend (mnémonique, libellé, adresse, type, station) | utile |
| 5 | Le dossier complet de l'application, compressé en .zip | relier variables, stations, voies et synoptiques ; **seulement si les fichiers 2 à 4 ne suffisent pas** | en dernier |

## 3. Comment les obtenir, étape par étape

Je n'ai pas pu lire la documentation de la version 6.3 (le site de l'éditeur ne répond pas aux outils
utilisés ici). Les menus ci-dessous sont donc **à confirmer** sur votre poste ; envoyez une capture si un
intitulé diffère.

1. **Faire une copie.** Fermez l'application dans TOPKAPI. Copiez son dossier complet (celui que vous
   ouvrez dans le configurateur : son chemin s'affiche à l'ouverture de l'application) vers un dossier
   d'essai, par exemple `D:\ESSAI_OGIAS\`. Ouvrez ensuite cette copie, jamais l'original.
2. **Version.** Dans le configurateur : menu Aide › À propos, puis capture d'écran.
3. **Export des variables (.flc).** Dans le configurateur de la copie, cherchez la fonction d'export des
   variables (autoparamétrage / SOFTLINK, ou export de la table des variables). Choisissez **toutes les
   variables d'une seule station** (une station suffit) et enregistrez le fichier.
4. **SOFTLINK.** Lancez l'assistant d'import sans le valider : capturez la liste des formats sources, puis,
   pour la source Schneider (.xsy), l'écran de correspondance des champs. Annulez ensuite l'assistant.
5. **Fichiers existants.** Joignez les .imp, .$$t et .txt avec leur provenance.

## 4. Confidentialité

- Une seule station suffit ; vous pouvez remplacer les noms d'ouvrages par des codes avant l'envoi.
- Retirez les adresses IP, numéros de téléphone, identifiants et mots de passe des captures et fichiers.
  Je n'en ai pas besoin pour étudier le format.
- Les fichiers reçus servent seulement de **référence de format** dans un dossier de travail. Ils ne sont jamais
  copiés dans OGIAS ni dans ses tests : les tests utilisent des échantillons synthétiques, comme pour
  Control Expert.

## 5. Ce que je ferai avec ces fichiers

1. Je lirai le format sans perte (relecture, puis réécriture identique octet pour octet), comme pour les
   exports Control Expert.
2. J'écrirai l'export OGIAS → TOPKAPI et un test sur un échantillon synthétique.
3. L'essai reviendra à vous : import dans la **copie** de l'application TOPKAPI. Le format ne sera déclaré
   compatible qu'après cet essai réussi.
