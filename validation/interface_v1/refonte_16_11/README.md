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
