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

## Gamme livrée Siemens S7-1500 (22/11/2026, demande de l'utilisateur : Schneider et Siemens)

Livrée en lecture seule (`genvar/data/gammes_livrees.json`), au même format qu'une gamme déclarée, avec ses sources.
Références vérifiées sur le Siemens Industry Mall :

| Rôle | Référence | Description |
| --- | --- | --- |
| Entrées TOR (défaut) | 6ES7521-1BL00-0AB0 | DI 32x24VDC HF |
| Entrées TOR | 6ES7521-1BH00-0AB0 | DI 16x24VDC HF |
| Sorties TOR (défaut) | 6ES7522-1BL01-0AB0 | DQ 32x24VDC/0.5A HF |
| Sorties TOR | 6ES7522-1BH01-0AB0 | DQ 16x24VDC/0.5A HF |
| Entrées analogiques | 6ES7531-7KF00-0AB0 | AI 8xU/I/RTD/TC ST |
| Sorties analogiques | 6ES7532-5HD00-0AB0 | AQ 4xU/I ST |
| Processeur | 6ES7511-1AL03-0AB0 | CPU 1511-1 PN (successeur de 6ES7511-1AK02-0AB0, en fin de commercialisation) |
| Rails | 6ES7590-1AB60-0AA0 / -1AE80- / -1BC00- | 160 mm, 482,6 mm, 2000 mm à couper |

- Emplacements : 0 alimentation, 1 processeur, 2 à 31 modules (document Siemens « S7-1500 in a Nutshell »).
- Capacité des rails **estimée** d'après la largeur des modules (35 mm) : 3, 12 et 30 modules. À confirmer dans TIA
  Portal ; le statut de la gamme le dit.
- Pas de rack d'extension en S7-1500 : au-delà de 30 modules, périphérie décentralisée (ET 200MP / ET 200SP),
  non calculée par OGIAS (signalé dans la proposition).
- Connecteurs frontaux et alimentation (PS / PM) non décrits : à commander et à choisir.
- Reconnue par « S7-1500 », « S7 1500 » ou une référence de CPU S7-1500 (6ES7511… à 6ES7518…) dans le champ
  Automate ; « Sie - S7-1500 » est ajouté à la liste des automates (ajout sans rien retirer).
- **S7-1200 non livré** : son module AQ 4 (6ES7232-4HD32-0XB0) est indiqué « non commandable » par Siemens (passage
  à la gamme S7-1200 G2) ; une gamme ne sera livrée que sur des références vérifiées et commandables.

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
- `tests/test_gammes_materiel.py::TestGammeLivreeSiemens` : S7-1500 reconnue (trois écritures), proposition en
  références 6ES75…, processeur, implantation, nomenclature, lecture seule, présence dans la liste des automates.
- `tests_web/test_coque_bureau.py::test_declarer_la_gamme_d_un_automate_non_decrit`.

## Captures (ouvrage fictif XTST)

`bibliotheque_gammes.png`, `declaration_gamme.png` (gamme livrée S7-1500, lecture seule), `materiel_s7_1500.png`.
