# Gammes de matériel déclarées par l'atelier (22/11/2026)

Principe fixé par l'utilisateur : **chaque client a un automate différent, OGIAS doit être ouvert.** Le catalogue
livré ne décrit que Schneider (M340, M580, Advantys STB) et SOFREL S4W. Jusqu'ici, pour tout autre automate, l'étape
Matériel ne proposait rien (aucune carte d'une autre gamme n'est jamais présentée à sa place) : il fallait déclarer
les cartes une à une.

## Ce que fait OGIAS désormais

1. **Déclaration de la gamme, une fois** (Standards d'ingénierie › Gammes de matériel) : code, nom, constructeur,
   texte qui la reconnaît dans le champ Automate de l'ouvrage, emplacements pris par le processeur, racks (nombre
   d'emplacements), cartes d'E/S (référence, nature ET / ST / EA / SA, voies, description), carte par défaut quand
   une nature en a plusieurs, processeurs et alimentations facultatifs. Les listes se saisissent une ligne par
   élément ; le copier-coller depuis Excel (tabulations) est accepté.
2. **Reconnaissance** : un ouvrage dont le champ Automate contient le texte déclaré (espaces et casse ignorés)
   relève de cette gamme. Un texte d'une gamme livrée ou d'une autre gamme déclarée est refusé : un automate est
   toujours reconnu sans ambiguïté.
3. **Calcul identique à une gamme livrée** : la gamme est convertie dans la structure du catalogue livré. OGIAS
   propose racks et cartes (réserve, groupes de secours, emplacements libres), implante les E/S, contrôle les
   cartes saisies (nature et voies imposées par la gamme), établit la nomenclature, et l'écran Matériel n'affiche
   que les cartes de la gamme.
4. **Accès direct** : quand l'automate de l'ouvrage n'appartient à aucune gamme, l'écran Matériel et l'écran
   Standards proposent « Déclarer la gamme de cet automate », formulaire prérempli.

Avec les **formats d'export appris** (`validation/formats_appris/`), la chaîne est complète pour un automate de
n'importe quel constructeur : matériel calculé, E/S implantées, liste des E/S exportée au format de son outil.

## Règles

- Rien n'est deviné : les références et capacités sont celles déclarées, marquées « déclarée par l'atelier, à
  vérifier sur la documentation du constructeur » dans le catalogue, la proposition et la nomenclature.
- Une nature d'E/S nécessaire à l'ouvrage sans carte déclarée bloque le calcul avec un message précis.
- Modifier ou supprimer une gamme ne touche aucun ouvrage : les cartes déjà retenues restent.
- Les gammes livrées (Schneider, SOFREL) sont inchangées.

## Limites

- Bilan de consommation des racks non calculé (comme pour les gammes livrées).
- Les modules de communication et règles d'extension propres au constructeur ne sont pas décrits : la remarque de
  la proposition renvoie à sa documentation.

## Vérifications

- `tests/test_gammes_materiel.py` (8 tests, gamme fictive) : contrôles de déclaration (12 refus), reconnaissance,
  modification et suppression, blocage avec la marche à suivre, chaîne complète (proposition sans aucune carte
  Schneider, implantation, nomenclature, choix du processeur, nature et voies imposées, export au format appris),
  nature sans carte refusée, gammes livrées inchangées, API.
- `tests_web/test_coque_bureau.py::test_declarer_la_gamme_d_un_automate_non_decrit`.

## Captures (données fictives XTST, références fictives)

`bibliotheque_gammes.png`, `declaration_gamme.png`, `materiel_gamme_declaree.png`.
