# Refonte industrielle de l'interface — 16/11/2026 (Claude)

Branche **`claude/refonte-ui-industrielle`**, partie du dernier commit de Copilot / Codex
(`cdb7299`, `codex/ui-validation-20261114`). Présentation seule : aucun moteur, API, donnée, règle de
validation ou format d'export modifié. Ouvrage de démonstration **fictif** (lieu `XTST`).

## Captures

- `avant/` : état de `cdb7299` ; `apres/` : état de la branche. Même ouvrage, mêmes écrans :
  tableau de bord, équipements, liste des E/S, matériel, variables, recette, référentiel, aux résolutions
  **1366 × 768, 1440 × 900, 1920 × 1080, 2560 × 1440**, plus le thème sombre à 1366 × 768.
- Images réduites en PNG à palette (256 couleurs) pour limiter la taille du dépôt.

## Défauts corrigés à leur source

| Défaut | Cause | Correction |
| --- | --- | --- |
| Détail des variables hors fenêtre (+13 px à 1920 et 2560 px, échec de la CI de Copilot) | règle générique `aside{width:350px}` (arborescence historique) appliquée au panneau de détail | règle limitée à `aside:not([class])` |
| Colonne vide de 270 px dans les variables à 1366 px | grille à 2 colonnes imposée même sans détail ouvert | 2ᵉ colonne seulement avec `.has-detail` |
| Libellés de navigation coupés au milieu des mots (« Équipement s ») | `overflow-wrap:anywhere` dans une colonne de 124 px | 176 px entre 1121 et 1400 px, 188 px au-delà, coupure entre les mots seulement |
| Contenu visible sous la barre d'étape | marge basse de la zone de défilement sous une barre collante | marge nulle quand la barre existe, barre poussée en bas de la zone |
| Barre d'état inférieure absente | masquée par la couche 0.31 et jamais remplie | rétablie et remplie par la couche actuelle (ouvrage, étape, référentiel, protections, qualification) ; hauteur bornée (l'ancienne règle de 29 px la faisait sortir de 3 px) |
| Arborescence des équipements cachée dans un tiroir | `#vue>aside{display:none!important}` | ancrée à gauche dès 1280 px, défilement propre ; le bouton la masque / l'affiche |
| Fiche ouvrage occupant tout le premier écran | formulaire toujours déplié | fiche enregistrée et complète repliée sur une ligne de résumé (`<details>`), dépliée si incomplète ou modifiée ; aucun champ supprimé |
| Rack sous la ligne de flottaison | ordre des blocs | rack affiché juste sous le bandeau ; emplacements distincts : alimentation, processeur, communication, carte, libre, « à choisir » |
| Avertissements en violet | jeton `--v31-warning` violet | orange (cahier des charges § 2) ; vert = réussi, rouge = bloquant, bleu = information / proposition |
| Boutons de recette séparés et empilés | un seul bouton déplacé dans la barre de commandes | « Dossier de recette » et « Actualiser les contrôles » dans la même barre |
| Référentiel décalé de 24 px | retrait du corps | aligné sur le bandeau |
| Tableau de bord étiré à 2560 px | cartes étirées sur la hauteur | hauteur du contenu |
| Processeur peu visible en thème sombre | même teinte que le fond du rack | fond bleu d'action atténué et bordure |

## Système graphique

`sorep_web/static/industrial-ui.css`, réorganisé en six sections : jetons (clair / sombre), base,
structure de l'écran, composants, écrans, largeurs d'écran (un bloc par largeur). Bleu nuit `#14243B`
pour la structure, bleu d'action `#1F5FBF`, échelle de 4 px, rayons de 3 à 6 px, police Segoe UI
(Inter embarquée en repli), ombres réservées aux fenêtres flottantes.

## Tests

- Nouveau `tests_web/test_geometrie_resolutions.py` (5 tests, 60 cas) : 8 écrans × 4 résolutions ;
  débordement, éléments hors fenêtre, chevauchements, barre d'état, barre d'étape, libellés,
  détail des variables, arborescence et fiche repliable, rack ; aucune écriture du projet.
- Tests de Copilot mis à jour pour les choix voulus par le cahier des charges (orange, bleu unique,
  largeurs de navigation) ; tous les autres contrôles inchangés.
- Résultats du 16/11 : `pytest tests` 700 réussis (5 ignorés : Qt), `pytest tests_web` 70 réussis,
  `ruff`, `node --check`, audit des données (0 détection).

## Restes connus

- Les couches CSS anciennes (`app.css`, `v031.css`) contiennent encore des règles mortes ou forcées
  (`!important`) ; la nouvelle couche les neutralise, leur suppression est un chantier à part.
- Liste des E/S : lignes de trois informations empilées encore hautes (≈ 65 px).
- Pas d'écran « versionning » dédié : l'historique existant (révisions du référentiel, copies
  horodatées) n'a pas été remplacé par une maquette.
- Accessibilité WCAG globale non auditée ; contrastes vérifiés sur les éléments ciblés seulement.

## Retours de l'utilisateur du 16/11 (10 h 24), intégrés

- **Arborescence** : en-tête en barre d'outils (titre, nombre d'équipements, filtre avec icône, « + Équipement »,
  « + UF », « Importer… » sur une ligne). Identifiants et fonctions inchangés.
- **Rack équipé emplacement par emplacement** (M340 / M580, matériel retenu) : un clic (ou Entrée) sur un
  emplacement ouvre le choix adapté — CPS : alimentations ; processeur : processeurs ; communication : remplacer
  ou libérer ; libre : carte d'E/S du catalogue ou module de communication. Le moteur refuse désormais une carte
  sur un emplacement réservé (processeur, communication) ou hors du rack retenu ; les choix d'alimentation et de
  processeur sont reportés sur le rack retenu. « Densité des cartes » devient « Cartes du calcul automatique »,
  et le bloc de choix s'intitule « Choix par défaut du calcul automatique ».
- **Sources d'acquisition** : le champ « Automate » devient « Source d'acquisition », liste classée
  (Automate / Télégestion / E/S déportées / Autres) d'après le tableau fourni ; protocoles : Modbus TCP/IP,
  LACBUS IP, EtherNet/IP, LACBUS IP / LX Connect. Installations existantes : ajout seulement, aucune valeur
  retirée ni renommée. « DL4W (LS,LT,OS) » est écrit « DL4W (LS / LT / OS) » (virgule interdite dans une valeur).
- Sources sans catalogue matériel (TSX37, TSX57, M221, M241, M251, S500, LogUp, DL4W, NEO, Ydrix, SCADAPack,
  Edge I/O NTS, TM3) : message « gamme non décrite », aucune configuration proposée. STB NIP 2311 : référence
  reprise, limites du NIP 2212 appliquées à titre indicatif et signalées.
- Tests : `tests/test_emplacements_et_sources.py` (7), `tests_web/test_retours_16_11.py` (4).

## Retours de l'utilisateur du 16/11 (11 h 03), intégrés

Captures : `retours_11h03/` (1366 × 768 ; `avant_equipement_1366.png` = fiche avant ce lot).

- **Fiche d'un équipement** (après « + Équipement ») : la page de ≈ 4 950 px sans fil conducteur devient
  un parcours. Une ligne **« Prochaine action »** unique (échelles 4–20 mA à définir → informations
  proposées à décider → erreurs → « Valider le paramétrage », ou « Liste des E/S » une fois validé), puis
  **trois onglets numérotés avec leur état** : E/S physiques · Informations fonctionnelles · Lignes de
  supervision (flèches gauche / droite au clavier ; l'onglet choisi est retenu par équipement). Options de
  l'équipement en cases compactes sur une ligne ; textes d'aide longs repliés (« Comment paramétrer les
  E/S ? »). Aucun bloc, identifiant ni commande retiré : les blocs non affichés portent `hidden`.
- **Écran Matériel** : sous-titre court, ligne « Prochaine action » (calculer → implanter les E/S sans
  voie → valider les voies → valider le matériel), rack en tête, puis trois onglets : **Voies des E/S**
  (implantation + liste par voie), **Réglages du calcul** (choix par défaut, besoin, répartition),
  **Nomenclature et livrables**. Onglet ouvert par défaut : réglages tant qu'aucune carte n'est posée,
  voies ensuite. Îlots STB affichés sous le rack.
- **Variables** : colonne « Source » retirée ; remplacée par le **Libellé** de l'information (libellé
  supervision, sinon commentaire), aussi pris en compte par le filtre. Dans le détail, « Source » devient
  « E/S source ».
- Tests : `tests_web/test_retours_16_11.py` (+3 : onglets de la fiche, onglets matériel, libellé des
  variables) ; tests existants adaptés pour ouvrir l'onglet voulu avant de lire la composition ou la
  nomenclature. Résultats : `pytest tests` 707 réussis (5 ignorés : Qt), `pytest tests_web` 77 réussis,
  `ruff`, `mypy`, `node --check`, audit des données (0 détection).

## Poste de travail « logiciel d'ingénierie » — pilote sur l'écran Matériel (16/11, 12 h)

Retour : OGIAS ressemble à un site web (pages qui défilent, fenêtres pour chaque détail), pas à un logiciel
d'ingénierie (TIA Portal, AVEVA, Control Expert). Captures : `poste_travail/`.

- **Cadre fixe, sans défilement de page** : éditeur au centre (rack, puis voies / réglages / nomenclature),
  **catalogue à droite**, **inspecteur en bas** ; chaque panneau défile seul.
- **Catalogue** (alimentations, processeurs, communication, cartes TOR / analogiques de la plateforme) avec
  filtre. Un clic sur un élément met en surbrillance les emplacements qui peuvent le recevoir ; un clic sur l'un
  d'eux l'installe. Glisser-déposer possible. Échap annule. Mêmes appels au moteur que la fenêtre de
  l'emplacement (emplacements réservés toujours contrôlés par le moteur).
- **Inspecteur** de la sélection : *Propriétés* (rack, emplacement ou carte), *Voies et E/S* d'une carte
  (réaffectation sur place, sans fenêtre), *Contrôles* (points bloquants de l'étape).
- Un clic sélectionne ; double-clic ou Entrée ouvre la fenêtre de l'emplacement (inchangée).
- Titre redondant masqué, plateforme et réserve sous le rack.
- Tests : `TestPosteDeTravailMateriel` (géométrie aux 4 résolutions, installation par clic et glisser,
  inspecteur, filtre). Résultats : `pytest tests_web` 80 réussis.

### Extension du poste de travail (16/11, 13 h)

- **Équipements** : catalogue des **modèles d'équipement** à droite (par domaine, filtrable). Un clic sur un
  modèle ouvre l'ajout pré-rempli (type, modèle, UF sélectionnée, numéro libre) : il ne reste que le libellé.
  On peut aussi glisser un modèle sur une UF ou sur l'ouvrage dans l'arborescence. Les commandes de la fiche
  passent à la ligne au lieu de déborder.
- **Liste des E/S** : plus de défilement de page ; tableau sur toute la hauteur, **une ligne par E/S**
  (≈ 44 px au lieu de ≈ 65 px : équipement et variable automate en colonnes séparées, clé en infobulle,
  désignation abrégée avec texte complet en infobulle et dans le détail ; clé du signal sur la même ligne au-delà de 1 700 px). Détail ancré à droite ; sur un écran
  ≤ 1 700 px, sens et raccordement se lisent dans le détail. Correction : le pied d'étape et la barre de
  commandes disparaissaient après la sélection d'une E/S (rendu partiel) ; l'écran est désormais reconstruit
  en entier.
- **Variables** : déjà en tableau + panneau de propriétés sans défilement de page ; inchangé.
- Tests : `TestPosteDeTravailEquipementsEtES` (+2). `pytest tests_web` : 82 réussis.
