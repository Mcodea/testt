# Formats d'export appris — lot 1 : liste des E/S physiques (22/11/2026)

Orientation validée par l'utilisateur le 22/11 : **OGIAS est ouvert à tout constructeur.** Vers les logiciels des
constructeurs, OGIAS n'exporte que trois natures de fichiers : la **liste des E/S physiques** (pour chaque automate),
la **télétransmission** (pour chaque supervision) et l'**IHM**. Les autres pièces (nomenclature, cartes, cahiers
FAT / SAT, liste de travail…) sont des documents d'études propres à OGIAS et ne changent pas.

Plutôt que de coder le format de chaque constructeur, l'atelier fait **apprendre** le format à OGIAS une fois, à
partir d'un vrai fichier exporté par l'outil du constructeur. Ce lot couvre la liste des E/S physiques.

## Parcours (Standards d'ingénierie › Formats d'export appris › Apprendre un format)

1. **Fichier exemple** exporté par l'outil de l'automate, d'un projet quelconque (texte à colonnes : CSV, TXT).
2. **Structure lue par OGIAS** : encodage (UTF-8 ou Windows), séparateur, guillemets, fin de ligne, lignes avant
   l'en-tête (recopiées telles quelles), ligne d'en-tête (modifiable).
3. **Contenu de chaque colonne**, proposé d'après les titres et les valeurs, confirmé par l'utilisateur : nom,
   adresse, type, sens, désignation, repère, module, voie, variable liée, valeur fixe (celle de l'exemple) ou vide.
   Une colonne non reconnue reste **vide** et c'est signalé : rien n'est deviné.
4. **Conversions**, par nature de voie (ET, ST, EA, SA) :
   - **adresse** décrite avec des jetons : `{RACK}`, `{EMPLACEMENT}`, `{VOIE}` (forme rack.emplacement.voie) ou
     `{OCTET}`, `{BIT}`, `{MOT}` (forme octet.bit, calculés avec le décalage et la taille d'emplacement déclarés),
     ou `{ADRESSE}` (celle d'OGIAS). La forme est proposée d'après l'exemple quand elle est reconnue ;
   - **type** et **sens** : la valeur que l'outil attend (ex. `Bool`, `Int`), proposée d'après l'exemple.
5. **Aperçu** : l'exemple et les E/S de l'ouvrage ouvert dans ce format, côte à côte, avec le résultat de la relecture.
6. **Enregistrement** avec le logiciel ou l'automate cible. Un format appris ne se modifie pas : pour le changer, on
   en apprend un autre.

## Export et contrôle automatique

- Le format sert aux ouvrages dont l'automate correspond (même règle que les modèles de livrables : automate saisi,
  ou Control Expert pour M340 / M580). Un format d'un autre automate est « non retenu », avec son motif.
- Mêmes refus que l'export Control Expert (projet existant, E/S sans voie, cartes incohérentes), plus : adresses en
  double après conversion, adresse impossible à calculer, caractère impossible dans l'encodage du format.
- **Chaque fichier produit est relu avec le format** : en-tête identique, une ligne par E/S, noms et adresses
  identiques à l'ouvrage. Un fichier qui ne se relit pas exactement n'est jamais livré.
- Écran Recette › Formats appris, et « Tous les livrables » (dossier `01_Automate/`, journal).

## Qualification

- Un format appris est **non qualifié** tant qu'un premier fichier produit n'a pas été importé dans le logiciel
  cible. L'utilisateur confirme l'essai dans la fiche du format : version du logiciel, compte rendu, auteur.
- Il devient alors **qualifié** pour sa structure (empreinte SHA-256 de la définition). Chaque export suivant est
  déclaré « conforme au format qualifié » par le contrôle automatique, sans nouvel essai.
- La qualification peut être retirée. Aucun programme ne peut prouver à la place de l'utilisateur qu'un logiciel qu'il
  n'exécute pas accepte un fichier : d'où ce premier essai réel, une seule fois par format.

## Formats livrés

Control Expert E/S (XSY, TXT) restent disponibles tels quels et figurent dans la bibliothèque comme formats livrés.

## Limites de ce lot

- Fichiers texte à colonnes seulement. Les exports XML viendront dans un lot suivant.
- La règle octet / bit (décalage + emplacement × taille) est déclarée par l'atelier : elle doit correspondre à la
  configuration matérielle réelle de l'automate, à vérifier lors de l'essai de qualification.
- Lots suivants : télétransmission (chaque supervision), IHM.

## Vérifications

- `tests/test_formats_appris.py` (14 tests, exemples fictifs de trois formes) : analyse, refus motivés,
  rack.emplacement.voie reproduit, octet.bit avec guillemets, préambule et valeurs fixes, adresses en double
  refusées, valeur contenant le séparateur relue exactement, fichier altéré détecté, encodage, qualification et
  empreinte, choix par l'automate et génération groupée, API complète, ouvrage inchangé.
- `tests_web/test_coque_bureau.py::test_apprendre_un_format_d_export` : parcours d'apprentissage et qualification.

## Captures (données fictives XTST)

`apprentissage.png`, `bibliotheque_formats.png`, `recette_formats.png`.
