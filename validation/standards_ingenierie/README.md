# Standards d'ingénierie (étapes 1 et 2, chartes de nommage)

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

## Étape 2 : bibliothèques, deuxième standard, application à un ouvrage

- **Bibliothèque de briques**, en bas de l'écran.
  - Deux familles : plans d'adressage (plages %MW par famille et décalage Modbus) et chaînes d'outils (supervision,
    IHM, prises dans les listes du référentiel).
  - Chaque brique est contrôlée comme une saisie sur un ouvrage : entiers, bornes, aucun recouvrement, nom unique.
  - Une brique ne se modifie pas : pour changer, on en crée une autre (« Partir de » préremplit les valeurs). Rien
    ne change donc en silence.
  - La colonne « Standards » compte les standards qui emploient chaque brique.
- **Nouveau standard** : un nom, une description et une brique par famille. Plusieurs standards peuvent partager
  une brique.
- **Nouvelle version** d'un standard : le motif est obligatoire et la version précédente reste dans l'historique.
  - Les ouvrages déjà créés ne changent pas.
  - Leur bloc « Outils d'ingénierie » signale « le standard a évolué depuis ».
  - Le bouton de ce bloc devient alors « Appliquer la version N du standard… ».
- **Archiver ou réactiver** : un standard archivé n'est plus proposé à la création. Le dernier standard actif ne
  peut pas être archivé.
- **Appliquer un standard** à un ouvrage existant, depuis le bloc « Outils d'ingénierie », seulement à la demande.
  - Un aperçu de ce qui changera s'affiche d'abord, et rien n'est écrit avant la confirmation.
  - Changent : plan mémoire, décalage, supervision, IHM et référence au standard.
  - Ne changent jamais : identification, automate, équipements, adresses validées. Les propositions d'adresses
    suivent le nouveau plan.
- « Reprendre les réglages d'un autre ouvrage » est conservé (aucune fonction retirée).
- Ancien fichier de l'étape 1 : relu sans perte, ses briques forment la bibliothèque.

Captures (données fictives) : `standards_clair.png`, `standards_sombre.png`, `nouvelle_brique.png`,
`appliquer_standard.png`, `ouvrage_cree_selon.png`.

## Chartes de nommage construites dans OGIAS (19/11)

Décision du 19/11 : chaque client est différent. La charte se construit donc dans OGIAS, sans exemple fourni, comme
une brique de la bibliothèque (« Nouvelle charte de nommage… »).

- **Le repère est une suite de segments, dans l'ordre voulu.**
  - Ouvrage : lieu, type d'ouvrage, numéro d'ouvrage, texte fixe. On règle la longueur, et les lettres et/ou
    chiffres permis.
  - Équipement : sous-ensemble éventuel, puis le code et le numéro d'équipement (motif du référentiel métier), et
    un texte fixe si besoin.
  - Un séparateur au choix : aucun, « _ », « - » ou « . ».
- **Aperçu en direct** sur un exemple fictif (XTST, RV, PM01), contrôlé par le serveur, qui donne le motif de tout
  refus :
  - segment inconnu ou en double ;
  - ni type ni numéro d'ouvrage ;
  - pas de code d'équipement ;
  - longueurs hors limites ;
  - repère d'équipement de plus de 32 caractères.
- **La Charte OGIAS** est décrite de la même façon. Elle reste celle du « Standard initial », et ses exemples sont
  identiques aux repères actuels.

Captures : `charte_editeur_clair.png`, `charte_editeur_sombre.png`.

## Repères fabriqués selon la charte de l'ouvrage (19/11)

- **Le repère d'un ouvrage créé selon un standard client suit sa charte.** Cela vaut pour l'ouvrage, les
  équipements et les noms des variables et des E/S. Exemple fictif : ouvrage `XTST_RV_EAU_02`, variable
  `TS_RV_EAU_02_HV01_OUV`. Le lieu est retiré du nom quand l'option « lieu dans le nom » est décochée.
- **La charte copiée dans l'ouvrage règle la saisie de l'identification** (lieu, type, numéro) : motifs, messages,
  longueur et proposition du numéro, aperçu du code.
  - En création, c'est la charte du standard choisi.
  - Elle s'applique aux contrôles R-OUV-02, 03 et 04.
- **Unicité.** Le code complet selon la charte est unique. En plus, un même lieu + type + numéro reste réservé
  quelle que soit la charte (même ouvrage physique). Le nom du fichier est le code de l'ouvrage.
- **Numérotation des équipements** : elle se fait par sous-ensemble si la charte place le sous-ensemble dans le
  repère, sur tout l'ouvrage sinon (comme la charte OGIAS).
- **Les listes de lieux et de types d'ouvrage** acceptent 1 à 8 lettres majuscules ou chiffres, pour servir à
  toutes les chartes. La longueur exacte est contrôlée par la charte de l'ouvrage (charte OGIAS : 4 et 2,
  inchangée). Décision assumée : l'essai `test_identification_listes` est mis à jour en conséquence.
- **Garde-fous :**
  - un standard d'une autre charte ne s'applique pas à un ouvrage déjà équipé, car tous ses repères changeraient ;
  - la longueur des noms reste contrôlée par R-NOM-01 ;
  - les exports restent « non qualifiés ».
- **Charte OGIAS et ouvrages antérieurs** : comportement strictement identique (essai
  `test_charte_ogias_strictement_inchangee` et l'ensemble des essais existants).

Captures : `creation_charte_client.png`, `variables_charte_client.png`.

## Import d'inventaire selon la charte du client (19/11)

L'import d'un inventaire (Excel ou CSV) relit chaque repère selon la charte de l'ouvrage, dans les deux chemins
d'import (aperçu puis validation explicite).

- **Lecture du repère.** Il doit commencer par le repère de l'ouvrage (sinon « autre ouvrage », refusé). Vient
  ensuite la partie équipement, segment par segment :
  - avec un séparateur, par découpage ;
  - sans séparateur, par longueur : sous-ensemble 2, texte fixe sa longueur, type et numéro d'équipement 4 (motif
    du référentiel métier).
- **Sous-ensemble.** S'il est absent de la charte, l'équipement va dans « 00 », comme pour la charte OGIAS à
  12 caractères.
- **Repère hors charte** (segment manquant, texte fixe différent, longueur) : la ligne est refusée avec son motif,
  sans recodage automatique.
- **Charte OGIAS** : lecture d'avant inchangée (12 ou 14 caractères, formats historiques).
- **Limite.** La reprise d'un programme existant (identification des variables par leur nom, mode Existant) lit
  toujours les noms à la manière d'OGIAS.

Fichier : `standards_ingenierie.json` dans le dossier de données de l'atelier. Il est écrit de façon atomique ; s'il
est illisible, il n'est jamais écrasé.

Vérifications :
- 779 essais du moteur, dont `tests/test_standards.py` (21 essais) ;
- 109 essais navigateur, dont `test_standards_ingenierie_ecran_et_creation`,
  `test_standards_bibliotheque_et_application` et `test_charte_de_nommage_construite_dans_ogias` ;
- ruff, mypy ;
- audit des données : 0 détection ;
- accessibilité, nouvel écran compris : 0 écart ;
- registre des commandes : aucune disparition non déclarée.
