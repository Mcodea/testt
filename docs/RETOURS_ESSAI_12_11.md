# Retours de l'essai utilisateur du 12/11/2026 (version 0.32) — analyse et plan

Essai réel par l'utilisateur sur son poste, version 0.32 récupérée sur GitHub (le titre de fenêtre indiquait
encore « 0.31 » : corrigé). 13 retours, analysés par Claude. Domaines du binôme : `docs/BINOME.md`.

## Analyse

| N° | Retour | Constat dans le code | Décision |
| --- | --- | --- | --- |
| 1 | « Détails » invisible quand on choisit un type en bas de liste (XT) | Panneaux liste et détails dans le même défilement | Liste et détails à défilement indépendant, détails toujours visibles (collant) |
| 2 | Supprimer un référentiel « Brouillon » | Un brouillon s'abandonne, pas de suppression explicite à l'écran | Bouton « Supprimer le brouillon » avec confirmation ; la révision publiée n'est jamais touchée |
| 3 | Communication par pop-up | Choix multiple de protocoles (une liste simple ne suffit pas) | Liste déroulante **à cases à cocher** dans le formulaire, sans fenêtre |
| 4 | Enchaîner les étapes | Le bouton « Étape suivante » existe en bas | Après validation d'une étape : proposer d'emblée l'étape suivante (bandeau d'action) |
| 5, 7 | Qu'est-ce qui bloque ? | Messages ponctuels (« Ajoutez et validez au moins un équipement ») | Panneau **« Pour passer à l'étape suivante »** : liste exhaustive des points bloquants, chacun avec un lien vers l'endroit à corriger ; même liste côté moteur pour chaque étape |
| 6 | « Structure / ajouter » peu visible | Seul point d'entrée, en haut à droite | À l'étape 1 sans équipement : état vide avec action principale « Ajouter le premier équipement » ; structure proposée au bon moment |
| 8 | STBNIP2212 → modules M340 | **Défaut** : le matériel ne décrit que M340 et M580 ; un automate inconnu retombe sur M340 avec un simple avertissement | **Correctif immédiat** : plateforme non décrite → aucune configuration proposée, message clair. Ensuite : plateforme STB (îlot NIP, alimentation, embases, modules) **à partir des références constructeur vérifiées**, et vue de configuration interactive par gamme (STB, M340, M580) |
| 9 | Table d'échange et télétransmission | Dans OGIAS, « table d'échange » désigne les %MW lus par la supervision : c'est le support de la télétransmission | Vocabulaire aligné sur l'usage industriel : **« Télétransmission »** = données vers télégestion / supervision (%MW compris) ; **« Échanges inter-automates »** = RX / TX entre automates (décision P2), affichés seulement s'ils existent |
| 10 | Répartition intelligente des E/S, continuité de service ; clic sur une carte | Règle actuelle : E/S d'un même équipement groupées sur une carte ; clic sur carte pour la modifier | Règles de répartition paramétrables : **équipements secourus (marche/secours, n+1) sur cartes distinctes**, groupement par équipement conservé, réserve par carte ; proposition modifiable ; vue des voies d'une carte avec réaffectation |
| 11 | Livrables de recette | Exports présents séparément (liste E/S, cartes, variables, XSY, TOPKAPI) | **Dossier de recette** : équipements, classeur E/S avec matériel et affectation, table de télétransmission, échanges inter-automates s'il y en a ; choix Excel / PDF / format cible pris en charge ; schéma d'architecture après P2 |
| 12 | Roue dentée = thème | Icône trompeuse | Icône soleil / lune avec libellé « Thème clair / sombre » |
| 13 | Cohérence d'un logiciel d'ingénierie | — | Poursuite de l'alignement sur les maquettes : navigation, tableaux structurés, commandes groupées, lisibilité |

## Lots

**Claude (moteur)** — dans cet ordre :
1. **M1** : [fait le 12/11] plateforme non décrite (STB…) : aucun repli M340, blocage explicite ; références
   Schneider (BMXP34…, BMEP58…) reconnues. Test : `tests/test_materiel_gamme_non_decrite.py`.
2. **M2** : [fait le 12/11] « points bloquants » par étape : `genvar/parcours.py`, `GET /api/parcours`.
   Test : `tests/test_parcours_guide.py`.
3. **M3** : [fait le 12/11] suppression d'un brouillon avec copie récupérable (5 gardées).
   Test : `tests/test_brouillon_supprime.py`.
4. **M4** : [fait le 12/11] dossier de recette zip (`genvar/dossier_recette.py`), sommaire HTML
   imprimable en PDF (aucune bibliothèque PDF embarquée). Test : `tests/test_dossier_recette.py`.
5. **M5** : [fait le 12/11] répartition B3, B4, B7, B8 : groupes de secours proposés (même type, même
   sous-ensemble) puis confirmés ou refusés, cartes distinctes (séparation avant réserve), conflit signalé
   si impossible, cartes ajoutées à la proposition de matériel pour séparer, 2 emplacements libres par rack,
   motif de chaque voie proposée, règles reprises au sommaire du dossier de recette. B1, B2, B5, B7 déjà en
   place ; B6 (sécurité) hors périmètre. Test : `tests/test_repartition_secours.py`.
6. **M6** : [fait le 12/11, nomenclature] gamme STB reconnue (STBNIP…), catalogue de 31 modules sourcés,
   îlot proposé à titre indicatif (NIM, PDM, modules, embases, terminaison, 32 modules, budget 1 200 mA) ;
   aucune adresse proposée tant que la correspondance avec l'automate maître n'est pas établie.
   Test : `tests/test_materiel_stb.py`. Énoncé initial : plateforme STB à partir des références vérifiées de `docs/RECHERCHE_STB_ET_REPARTITION.md`
   (fiches techniques à confirmer d'abord) — **décision S1** ; attention : STB en fin de vie (fin de
   fabrication 01/12/2027, remplacement Edge I/O NTS).

**Codex (interface)** — dans cet ordre : U1 défilement (1) · U2 bouton supprimer le brouillon (2) · U3 liste
à cases à cocher pour la communication (3) · U4 parcours guidé : panneau des points bloquants, passage
proposé à l'étape suivante, état vide de l'étape 1 (4 à 7) · U5 icône de thème (12) · U6 vocabulaire
Télétransmission / Échanges inter-automates (9) · U7 vue de configuration matérielle par gamme et vue des
voies d'une carte (8, 10) · U8 dossier de recette à l'écran (11) · U9 cohérence générale (13).

## Décisions à prendre par l'utilisateur

- **S1** : [traité le 12/11] l'utilisateur a désigné le site Schneider comme source : gamme STB décrite
  (nomenclature). Décidé le 12/11 (15 h 24) : périmètre arrêté aux registres Modbus de l'îlot, pas d'adresses %MW.
- **S2** : [validé le 12/11] prendre en compte les bonnes pratiques industrielles : équipements secourus sur
  cartes distinctes par défaut, désactivable par ouvrage (B4).
