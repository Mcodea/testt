# Instructions en cours de route

**Agent actif : libre** (12/11/2026 19:03 UTC). Passation à Claude — dépôt public `Mcodea/testt`, branche `claude/referentiel-v2`.

## Passation à Claude — lot UI reporté sur le bon dépôt public

**Dernier commit fonctionnel : `01287a2`**, présentation industrielle adaptée
aux ajouts matériels récents. **`7466f35`** : corrections U9 reportées. Ce commit
de passation ne change que la documentation. Codex laisse la main à Claude.

### Étape exacte de reprise

1. Travailler dans **Mcodea/testt**, branche **claude/referentiel-v2** :
   `git fetch origin && git checkout claude/referentiel-v2 && git pull --rebase`.
   Workspace de cette session : **/workspace/testt**. L’ancien clone
   /workspace/OGIAS pointe toujours sur le dépôt privé ; ne pas y reprendre
   ce développement, ne pas lui ajouter une destination publique.
2. Relire BINOME.md et les commits depuis **085b1c7**. Le dépôt public garde
   sa racine **4d084b4** : seuls des fichiers UI/tests ont été reportés, aucun
   historique privé, aucun ancien commit fusionné. Ne rien refaire des lots finis.
3. Aucun lot UI Codex en cours ni fichier utile non commité. Poursuivre le
   backlog moteur/documentation de Claude, puis proposer la prochaine stable
   après essai utilisateur. Les écrans R3/R8, conflits R4 et rapports d’impact
   restent à répartir dans un futur lot UI ; pas de changement métier dans la
   refonte visuelle. Aucune fusion de PR, --force, étiquette ou release d’agent.

### Réalisé et préservé

- U9 : destinations correctes des points bloquants ; table Variables 44 px et
  cases clavier 24 px ; vues inchangées (« Adresses automate », identifiant
  exchange conservé), état vide/colonnes au resize, Échap et retour du focus
  respectant modale/recherche au premier plan.
- Refonte : industrial-ui.css après v031.css ; gabarit latéral libellé et
  deux classes S4W seulement dans app.js. Palette sombre #0B0F19 / #0F1623 /
  #111827, bordures #1E293B ; fontes locales et nombres tabulaires, commandes
  et tableaux compacts, racks/voies lisibles. La préférence de thème et son
  stockage ne changent pas : lune = sombre, soleil = variante claire technique.
- Les ajouts matériels de Claude (CPS, CPU, communication, grilles et catalogue,
  nomenclature), ses algorithmes, ses exports et leurs correctifs récents sont
  préservés. Composition présentée en grille ; références « à choisir » jamais
  devinées. Les fonctions, événements, identifiants, état et appels API restent
  inchangés dans le lot visuel. Aucun moteur/donnée/serveur/workflow modifié.
- Les maquettes d’origine restent intactes ; la demande visuelle du chat du
  12/11 remplace leur palette/formes. Pas de contenu de démonstration ajouté
  au produit. Les captures montrent uniquement l’API de projets de tests isolés.
- **validation/interface_v1/industriel_12_11/** : 28 captures régénérées sur
  la version publique, comparaison.html, mesures, SHA-256, verification.json
  et performance.json. Nouveau test de composition/rack sans écriture.

### Vérifications de cette version publique

- **730 tests Python**, 18 sous-cas, 0 ignoré (201,87 s), couverture moteur
  **89,283831 %**, exports **100 %**. **60 tests navigateur**, 52 sous-cas,
  0 ignoré (97,98 s), dont sept cas de présentation. Projets inchangés à l’octet
  après les interactions visuelles ; aucun POST lors du thème/détail.
- Ruff, mypy 49 fichiers, JS et audit strict des dépendances conformes ;
  audit données **0 détection / 0 échec de lecture**. Sept seuils du banc
  inchangés passent : rendu **84 ms**, filtre **100,2 ms**, adressage **0,621 s**.
- **CI publique active et gratuite sur les runners standards**. La base
  de Claude a passé le run **43276436661**, cinq jobs. Le push de ce lot
  déclenche la même CI complète Windows/Linux, navigateur/performance, qualité
  et portable. Suivre son statut réel (ne pas reprendre l’ancienne mention de
  quota privé) : https://github.com/Mcodea/testt/actions?query=branch%3Aclaude%2Freferentiel-v2.
- L’API GitHub est filtrée par l’environnement, mais les pages publiques
  Actions sont lisibles ; aucun blocage de quota en déduire. PR_DESCRIPTION.md
  est prêt pour une PR utilisateur vers release/1.0 ; aucune fusion automatique.
- A1 et D5-b restent en décision : pas de 193 E/S ni renommages V1, pas de
  CT/FDC_/CMD_/CONS_ réintroduit. R1 validé, STB limité aux registres de l’îlot,
  aucune adresse maître inventée. Preuves réelles Control Expert 14.1, TOPKAPI
  et S4W-Tools toujours attendues ; pas de qualification ou de livraison 1.0
  annoncée sur la seule base des tests. Dépassement matériel non fabriqué pour
  une capture ; sa bordure reprend l’état existant du moteur.

## Historique de cette session — correction du dépôt de destination

La consigne « testt » désigne le nouveau dépôt public, pas une branche de l’ancien.
La visibilité publique et la CI verte du run 43276436661 ont été vérifiées.
Report de fichiers UI/tests uniquement depuis le lot déjà testé, sans import
d’historique privé ; ajouts matériels et exports de Claude préservés.
BINOME.md et la passation du 12/11 à 16 h 40 font foi.

## [nouveau] 12/11/2026 17 h 30 — Matériel M340 / M580 complet (Claude, demande de l'utilisateur)

L'utilisateur trouvait la partie matériel incomplète. Ajouts (choix utilisateur : alimentation / CPU / racks,
communication, toutes les cartes d'E/S, rack réaliste + nomenclature ; **pas** de borniers ni câbles) :
- catalogue `genvar/data/materiel_schneider.json` sourcé : 8 alimentations BMX CPS, processeurs M340 (5) et
  M580 (4 confirmés), 5 modules de communication M340, extension BMX XBE 1000 / câbles / TSX TLY EX / cache
  BMX XEM 010, 20 cartes (dont 48 V, CA, relais, triac, température) et 6 cartes mixtes / comptage (listées,
  non placées automatiquement). 3 cartes de départ sont marquées « à confirmer » (absentes des sources lues) ;
- choix de l'automaticien `Ouvrage.materiel_config` (`POST /api/materiel/action {action: "config", …}`),
  contrôlés contre le catalogue ; processeur déduit du champ Automate s'il en porte la référence exacte ;
  rien n'est deviné (« à choisir ») ; consommations non intégrées (« bilan à vérifier ») ;
- rack réaliste : emplacement CPS, processeur (00, ou 00-01 en M580), communication, cartes, libres, XBE ;
- nomenclature de commande (`GET /api/materiel` → `nomenclature`, export `quoi=nomenclature`).
Tests : `tests/test_materiel_complet.py`, `tests_web/test_retours_essai_12_11.py::TestMaterielComplet`.

## [nouveau] 12/11/2026 16 h 40 — PASSATION À CODEX : tout ce qui a changé pendant ton arrêt (à lire en premier)

**Agent actif : libre** (Claude s'arrête ; Codex reprend). Règles du binôme inchangées (`docs/BINOME.md`).

1. **Nouveau dépôt** : on travaille désormais dans **`Mcodea/testt`** (public, CI gratuite), plus dans
   `Mcodea/OGIAS` (resté privé : son historique contient d'anciennes données de sites réels, ne jamais le
   rendre public ni y recopier d'historique). `testt` repart sans historique de l'état du 12/11 (`b5cae68`).
   Branches : `claude/referentiel-v2` (seule branche où les agents poussent), `release/1.0` (stable, fusion
   par l'utilisateur uniquement), `main`. Licence : tous droits réservés (`LICENCE.md`). CI complète (Linux,
   Windows, navigateur, zip portable) verte au départ (run 43247608193).
2. **Retours d'essai du 12/11** (`docs/RETOURS_ESSAI_12_11.md`) — moteur fait par Claude : M1 gamme non
   décrite sans repli M340 ; M2 `GET /api/parcours` (points bloquants / à vérifier par étape) ; M3 suppression
   et récupération d'un brouillon de référentiel ; M4 dossier de recette (`quoi=dossier_recette`) ; M5
   répartition des E/S (groupes de secours proposés puis confirmés, cartes distinctes, emplacements libres
   par rack, motif de chaque voie) ; M6 gamme Advantys STB (`genvar/data/materiel_stb.json`, îlot numéroté
   comme le logiciel Advantys `1/127`, `2/-`, `3/1`…, image d'E/S Modbus 40001 / 45392).
3. **Interface faite par Claude pendant ton arrêt** (ne pas refaire) : U1 défilement du référentiel ; U2
   « Supprimer le brouillon » / « Récupérer » ; U3 protocoles en liste déroulante à cases à cocher ; U4
   panneau « Pour passer à l'étape suivante » + état vide de l'étape 1 ; U5 bouton soleil / lune (icônes
   ajoutées au sprite Lucide, empreinte du manifeste mise à jour) ; U6 « télétransmission » au lieu de « table
   d'échange » ; U7 bloc « Répartition des E/S », îlot STB, **vue des voies d'une carte** avec déplacement /
   placement ; U8 bouton « Dossier de recette ». Tests : `tests_web/test_retours_essai_12_11.py`.
4. **Ton lot** : **U9 cohérence générale** des écrans (navigation, tableaux, commandes groupées, lisibilité),
   à partir des prochaines remarques de l'utilisateur ; ne rien changer au moteur (`genvar/`).
5. **Décisions de l'utilisateur à respecter** : S2 validé (secours sur cartes distinctes, désactivable) ;
   S1 STB décrit, **périmètre arrêté aux registres Modbus de l'îlot, pas d'adresses %MW** (ne pas lui
   redemander de captures) ; D5-b et A1 toujours **en attente** : ne pas les appliquer.
6. **Contrôles avant chaque envoi** : `pytest tests`, `pytest tests_web`, `ruff check --config ruff.toml .`,
   `node --check` sur les JS, `python outils/verifier_donnees.py` (0 détection, jamais de liste blanche).
   État au départ : 675 tests moteur et 44 tests navigateur verts.
7. **Version** : le numéro affiché est encore 0.32 ; la prochaine version stable (0.33) sera proposée à
   l'utilisateur après son essai, par pull request vers `release/1.0` qu'il fusionne lui-même.

## [nouveau] 12/11/2026 16 h 30 — Dépôt de travail : `Mcodea/testt` (public)

Le travail continue dans **`Mcodea/testt`**, public pour que la CI soit gratuite. Il repart de l'état du
12/11 (commit `b5cae68` de `Mcodea/OGIAS`, branche `claude/referentiel-v2`) **sans historique** : l'historique
de `Mcodea/OGIAS` contient d'anciennes données de sites réels et ce dépôt-là doit **rester privé**. Branches :
`release/1.0` (stable, fusions validées par l'utilisateur), `main` (copie de départ) et
`claude/referentiel-v2` (travail des agents), comme dans `docs/BINOME.md`. Licence :
tous droits réservés (`LICENCE.md`). Ne jamais y pousser de donnée réelle : audit `outils/verifier_donnees.py`
avant chaque envoi. Les tests Windows et le zip portable tournent de nouveau à chaque envoi.

## [nouveau] 12/11/2026 15 h 25 — CI : crédit GitHub Actions épuisé, Windows à la demande

Le crédit gratuit du compte (12 $ / mois, dépôt privé) est épuisé : GitHub ne démarre plus les tâches
(« recent account payments have failed or your spending limit needs to be increased »). Ce n'est pas un défaut
du code. En attendant : **toujours lancer localement** `pytest tests`, `pytest tests_web`, `ruff` et l'audit des
données avant chaque envoi. Pour économiser, sur `claude/referentiel-v2` la CI ne lance plus que Linux ; les
tests Windows et le zip portable tournent sur `release/1.0`, sur pull request ou à la demande (« Run workflow »).

## [nouveau] 12/11/2026 15 h — Interface : Claude a pris le relais (Codex sans crédit)

Faits par Claude (tests navigateur `tests_web/test_retours_essai_12_11.py`) : **U1** liste des types du
référentiel à défilement propre ; **U2** « Supprimer le brouillon » + « Récupérer un brouillon supprimé » ;
**U4** panneau « Pour passer à l'étape suivante » (points cliquables) et « À vérifier » sous chaque étape ;
**U5** bouton soleil / lune ; **U7** (partie) îlot STB numéroté comme Advantys et bloc « Répartition des
E/S » (groupes de secours) ; **U8** bouton « Dossier de recette » ; **U3** protocoles en liste déroulante à
cases à cocher (sans fenêtre) ; **U6** « table d'échange » remplacée par « télétransmission » à l'écran ;
état vide de l'étape 1 (« Ajouter le premier équipement ») ; **U7** clic sur une carte → vue de ses voies
(occupant, état), déplacement vers une voie libre de même nature, placement d'une E/S sans voie (une E/S
validée qui bouge repasse « à valider », confirmation demandée). **Reste pour Codex** : U9 (cohérence
générale).

## [traité en partie] 12/11/2026 13 h 20 — Passation à Codex : lots d'interface U1 à U9

Claude a terminé les lots moteur M1 à M5 de `docs/RETOURS_ESSAI_12_11.md` (M6, STB, attend la décision S1)
et les deux correctifs de relecture. **Codex reprend l'interface, dans cet ordre**, sur
`claude/referentiel-v2` uniquement (jamais `release/1.0`, jamais de fusion) :

1. **U1** défilement : liste des types et panneau « Détails » à défilement indépendant, détails collants.
2. **U2** brouillon du référentiel : bouton **« Supprimer le brouillon »** (remplace « Abandonner »), avec
   confirmation ; `POST /api/referentiel/cycle/action {action: "abandonner"}` renvoie `{copie}` (nom de la
   copie gardée) ; liste des brouillons supprimés et **« Récupérer »** :
   `{action: "recuperer_brouillon", nom}` (5 copies gardées).
3. **U3** communication : liste déroulante à cases à cocher dans le formulaire, sans fenêtre.
4. **U4** parcours guidé : `GET /api/parcours` → `{etapes: [{etape, vue, libelle, pret, bloquants,
   a_verifier}]}` ; chaque point `{code, message, vue, ident_eq, gravite}`. Panneau **« Pour passer à
   l'étape suivante »** (bloquants, chaque point cliquable vers `vue` / `ident_eq`), puis « à vérifier » ;
   bandeau « Étape suivante » quand `pret` ; état vide de l'étape 1 (« Ajouter le premier équipement »).
   `[]` pour un projet existant : ne rien afficher.
5. **U5** thème : icône soleil / lune, libellé « Thème clair / sombre ».
6. **U6** vocabulaire : « Télétransmission » (données vers la supervision, %MW compris) ; « Échanges
   inter-automates » seulement s'il y en a (aucun aujourd'hui).
7. **U7** matériel : vue de configuration par gamme ; gamme non décrite (`plateforme: "Non décrite"`,
   `remarque_plateforme`) → aucune carte affichée, message seul. Vue des voies d'une carte avec
   réaffectation. **Répartition (M5)** : `GET /api/materiel` contient `repartition` =
   `{separation_secours, emplacements_libres_rack, reserve_min, groupes_secours: [[{ident, repere}]],
   groupes_secours_proposes: [{type, designation, sous_ensemble, membres: [{ident, repere}]}]}`.
   Actions `POST /api/materiel/action` : `confirmer_groupe_secours {membres: [ident…]}`,
   `refuser_groupe_secours {membres}`, `retirer_groupe_secours {membres}`,
   `regles_repartition {separation_secours?, emplacements_libres_rack? (0 à 6)}`. Afficher les groupes
   proposés à confirmer / refuser (rien n'est appliqué sans confirmation), les groupes confirmés, la case
   « Équipements secourus sur cartes distinctes » (cochée par défaut). Le motif de chaque voie proposée est
   dans `regle` des affectations du plan d'adressage : l'afficher (infobulle ou colonne « Règle »).
   **STB (M6)** : `plateforme: "STB"` ; la proposition (`applicable: false`) donne pour chaque îlot
   `racks[i].nim`, `pdm`, `embase_pdm`, `terminaison`, et pour chaque module `embase` : l'afficher comme un
   îlot (NIM, PDM, modules, terminaison), pas comme un rack ; `cartes_catalogue` est alors celui de STB.
   `racks[i].composition` = `[{emplacement, reference, noeud, role, embase?}]` dans l'ordre du logiciel
   Advantys : afficher « emplacement / nœud » comme Advantys (`1/127`, `2/-`, `3/1`…).
8. **U8** dossier de recette : bouton d'export `quoi: "dossier_recette"` → `{base}_dossier_recette.zip`
   (sommaire HTML imprimable en PDF, pièces, empreintes, pièces non produites et motif).
9. **U9** cohérence générale (maquettes : navigation, tableaux, commandes groupées).

Règles : tests navigateur pour chaque écran touché, CI verte avant de passer au suivant, « Agent actif :
Codex <heure> » dans le premier commit, « libre » à la fin. Rien à changer dans `genvar/` : un besoin
moteur s'écrit ici pour Claude.

## [nouveau] 12/11/2026 12 h — Retours de l'essai utilisateur : PRIORITÉ

L'utilisateur a essayé la 0.32 sur son poste. 13 retours analysés et découpés en
lots dans **`docs/RETOURS_ESSAI_12_11.md`** : ils passent **avant** les lots R / P
restants. Claude : M1 (aucun repli M340 pour une plateforme non décrite, STB) →
M2 (points bloquants par étape) → M3 → M4 → M5 ; Codex : U1 → U9. Décisions
utilisateur attendues : S1 (périmètre STB), S2 (secours sur cartes distinctes).

## [traité] 12/11/2026 10 h 20 — Relecture des commits du 11/11 (Claude)

Aucun défaut bloquant. Traité le 12/11 (point 1 : référentiel figé rétabli, test ; point 2 : « à vérifier »
du parcours quand le nom du programme automate est vide). À traiter au prochain lot moteur :
1. `Session._operation_lourde` : si la copie horodatée échoue, l'ouvrage est
   rétabli mais pas le référentiel figé (`self.catalogue`) ; cas d'une
   restauration de copie. Rétablir aussi le référentiel figé, avec test.
2. Homonymes (P8) : deux ouvrages sans `nom_projet` ne sont jamais comparés ;
   ajouter une alerte (pas une erreur) quand des ouvrages en charte 12 sans
   projet déclaré produiraient des noms identiques.
Pour l'utilisateur : `BI_DIS` = disponible et `BI_DSC` = discordance (sa
décision du 11/11) diffèrent du PDF VANNE_MV (`BI_DIS` = discordance).

## [traité] 12/11/2026 10 h 15 — Version stable 0.32 posée

**Point stable : `release/1.0` @ `8d655ea`** (fusion de la PR #1, CI verte, run
43187135151, zip portable construit et essayé). Notes : `docs/NOTES_VERSION_0.32.md`.
Étiquette `v0.32.0` et pré-version GitHub : à créer par l'utilisateur depuis
GitHub (droits refusés aux agents). Gel levé : le travail reprend sur
`claude/referentiel-v2` selon `docs/BINOME.md` ; `release/1.0` ne reçoit que des
fusions validées par l'utilisateur.

## [traité] 12/11/2026 09 h 45 — Stabilisation demandée par l'utilisateur

Gel fonctionnel : **aucun nouveau lot** sur `claude/referentiel-v2` tant que la
version stable n'est pas posée. Seuls sont admis les correctifs de CI ou de défaut.
Les échecs CI du 11/11 après 16 h (`5c67e82`, `a3c4f54`, `c78daae`) venaient du
service d'artefacts GitHub (« Failed to CreateArtifact », réponse HTML) : tests
verts dans ces mêmes runs (649 / 649 / 36). Suite locale sur `494e00b` : 636
tests, ruff, JS, audit des données verts.

Lire ce fichier après chaque `git pull --rebase`. Marquer chaque entrée
`[traité]` ou `[refusé]` (avec la raison) dans le commit qui la prend en compte.

**Agent actif : libre** (12/11/2026, 12 h 20 UTC ; lots M1 à M5 faits par Claude, relais à Codex : U1 à U9). **Règle du binôme : `docs/BINOME.md`**
— une seule branche `claude/referentiel-v2`, domaines Codex = interface, Claude = moteur.

## [nouveau] Bilan du 11/11 — rédigé par Claude, 20 h 45 UTC

Branche `claude/referentiel-v2`, PR #1 vers `release/1.0` (non fusionnée). Dernier commit fonctionnel : `5e75909`.

### Commits de la journée

**Codex : aucun commit le 11/11.**

**Claude, session autonome du matin (08 h 19 → 08 h 58 UTC)** :
`14e1c07` correction de la course de navigation dans `app.js` (domaine Codex, signalé) · `2253920` profil VANNE_MV,
P5 · `d158c43` homonymes entre ouvrages, P8/R9 · `417d686` version calculée par profil et synchronisation, R2/R3 ·
`755585c` conflits de surcharge, R4 · `ddd3e0a` rapport d'impact et journal, R5/R7 · `9b099c9` acceptation en un
geste, R6 · `60437bf` reprise contrôlée d'un modèle figé · `9a419af` alerte P3 · `39c4e4c` passation.

**Claude, session planifiée de midi (12 h 17 → 12 h 40 UTC)** : `de27749` agent actif · `072b444` variables
internes déclarées, P1 · `4054e61` seuil de confiance, mesures publiées, confirmation en lot annulable (§ 6) ·
`d60e43f` passation.

**Claude, session avec l'utilisateur (après-midi)** : `cb6a4c8` candidats BI de MV (P1) · `9017ba3` sortie d'arrêt
`ST_<repère>_ARR` (P5) · `5c67e82` seuil strict 80 retenu · `a3c4f54` R1 noté comme validé.

**Claude, session planifiée du soir (20 h 13 UTC →)** : `c78daae` agent actif · `5e75909` copies horodatées avant
chaque opération lourde, restaurables (V1-7-03, moteur et API) · ce bilan.

Relecture : aucun commit ne contredit la doctrine. Pas d'adresse recalculée, pas de %MW pour une E/S physique,
rien n'est appliqué sans aperçu. A1 et D5-b ne sont pas appliqués. Point à faire trancher : le commit `a3c4f54` note
R1 comme validé, alors que la consigne planifiée de ce soir interdit d'appliquer R1. Je ne l'ai pas appliqué
(voir les décisions ci-dessous).

### Exigences passées à « fait » aujourd'hui (avec test)

| ID | Preuve |
| --- | --- |
| V1-6-03 seuil réglé sans faux connu au-dessus | `tests/test_seuil_confiance_rapprochement.py::TestSeuil` |
| V1-6-04 précision et rappel publiés | `tests/test_seuil_confiance_rapprochement.py::test_compte_rendu_publie_identique_au_calcul` |

Côté moteur, ces lignes sont terminées mais restent « partiel » parce que l'écran Codex manque :

- **V1-6-02** confiance et raison ;
- **V1-6-05** confirmation en lot annulable ;
- **V1-7-03** copies horodatées (`tests/test_copies_horodatees.py`, 17 tests) ;
- P1, P3, P5, P8, R2 à R7 et la reprise du modèle figé : tests nommés dans les passations ci-dessous.

Tableau de conformité : 35 lignes « fait », 116 « partiel », 10 « en attente de preuves utilisateur » (176 lignes).

### État de la CI

- Runs 71 à 74 (`5c67e82`, `a3c4f54`) rouges à cause d'une **panne DNS des miroirs Ubuntu** sur les exécuteurs
  GitHub (`Temporary failure resolving 'azure.archive.ubuntu.com'` pendant `apt-get` et `playwright install
  --with-deps`). Aucun test n'a échoué et le code n'est pas en cause.
- Run 75 (`c78daae`, poussé pour relancer la CI) : tests Windows et Linux, navigateur, banc, statique, audit et
  données **verts**. L'envoi de l'artefact portable a échoué après 10 min, au moment où l'API GitHub renvoyait des
  erreurs 502 : incident du service GitHub, pas du code.
- Run 77 (`5e75909`) : voir le commentaire de la PR (encore en file d'attente au moment de la rédaction).
- En local sur `5e75909` : 636 tests Python (30 ignorés ici faute de PyMuPDF/PySide6, 0 en CI), 36 tests navigateur
  et 34 sous-cas, ruff, mypy (47 fichiers), `node --check`, audit des données (0 détection), banc dans les seuils
  (adressage 0,46 s avec la copie).

### Ce qui reste avant une version candidate (`v1.0.0-rc1`)

1. **Décisions de l'utilisateur** : A1 bloque V1-3-05 à V1-3-09 ; D5-b ; R1 (lot moteur prêt à démarrer) ;
   A2/A7/A8/A10/A11.
2. **Interface (Codex)** : écrans en attente du moteur. Il s'agit de R3 à R8, des conflits R4, du rapport d'impact,
   du journal, de l'acceptation en un geste, de la reprise du modèle figé, des options de MV, de la confiance et
   de la raison, de la confirmation et de l'annulation en lot, des variables internes et des copies horodatées.
   S'y ajoutent la conformité aux maquettes, WCAG AA, Ctrl+Z et l'affichage de 1366×768 à 2560×1440.
3. **Moteur (Claude)** : V1-7-05 (reprise sans perte après arrêt brutal : `.tmp` orphelin, verrou) et V1-7-04
   (verrou d'ouvrage). Ensuite V1-7-06 (journal tournant consultable) et le lot R1 si l'utilisateur le confirme.
   Puis les preuves V1 des lignes héritées « Fonctions/tests hérités… », à reprendre une par une.
4. **Livraison** : `VERSION = "1.0.0"` à un seul endroit, documentation (§ 9 : manuel, guide administrateur,
   règles de nommage générées, CHANGELOG, notes de version, LICENCES_TIERCES), `COMPTE_RENDU_V1.0.md`, essai sur
   un Windows propre avec captures.
5. **Section 8** : exports réels Control Expert 14.1, TOPKAPI 6.3 et S4W-Tools à fournir par l'utilisateur. Aucune
   compatibilité n'est déclarée sans essai.

### Décisions à valider par l'utilisateur

- **D5-b** : dix règles historiques « auto » classées en suggestions. En attente, non appliquée.
- **A1** : 54 renommages V1 et 49 ajouts. En attente, non appliquée.
- **R1** : votre accord de l'après-midi est inscrit (`a3c4f54`) : un équipement CT d'un projet existant devient FT
  par l'adoption contrôlée, avec son repère et ses noms d'origine. La consigne planifiée de ce soir interdit
  toutefois d'appliquer R1, donc le lot moteur n'est pas lancé. **À confirmer** : faut-il lancer le lot R1 à la
  prochaine session ? Si oui, retirez R1 des interdits de la consigne planifiée.
- **A2/A7/A8/A10/A11** et types logiques de EI, MI, RI : en attente.
- **Nouveau, V1-7-03** (choix prudents, réversibles) :
  - 10 copies conservées par opération ; les copies d'adoption ne sont jamais effacées ;
  - un ouvrage jamais enregistré n'a pas de copie (rien sur disque à protéger) ;
  - une copie impossible annule l'opération ;
  - les copies d'un ouvrage mis à la corbeille restent dans son dossier.

### Message à envoyer à Codex

> Codex, reprends sur `claude/referentiel-v2` après `git pull --rebase`. Lis d'abord `docs/BINOME.md` et ce bilan.
> Mets « Agent actif : Codex <heure> » dans ton premier commit. Ton domaine est l'interface. Le moteur et les
> routes existent déjà, donc ne touche pas à `genvar/`. Dans cet ordre :
> 1. **Copies horodatées** (V1-7-03) : dans l'ouvrage, une liste « Copies de sauvegarde ». Elle s'appuie sur
>    `GET /api/ouvrage/copies`, qui renvoie `nom`, `operation`, `libelle`, `le` et `taille`. Chaque ligne a un
>    bouton « Restaurer » qui appelle `POST /api/ouvrage/restaurer-copie {nom}`, avec une confirmation explicite.
>    Après la restauration, recharge l'ouvrage et affiche le nom de la copie de l'état d'avant
>    (`copie_avant_restauration`). Ajoute un test navigateur : adresser, restaurer, retrouver les adresses vides.
> 2. **Rapprochement § 6** : afficher `confiance` et `raison`, le bouton « Confirmer en lot · n », le journal et
>    « Annuler le lot ». Les routes sont à ajouter dans `serveur.py` en petits commits.
> 3. **Écrans référentiel en attente** : pastilles R8 et synchronisation, conflits R4 et « Revenir au standard »,
>    rapport d'impact, journal, acceptation en un geste, reprise du modèle figé, options de MV, variables internes
>    (préréglage séparé, jamais dans « Table d'échange » ni « Télétransmission »).
> 4. Le test intermittent `tests_web/test_referentiel_codes.py::test_texte_saisi_echappe_dans_la_table_et_le_detail`
>    (attente après `page.reload`).
>
> N'applique pas A1, D5-b ni R1. N'affaiblis aucun test. Pas de `--force`, ne fusionne pas. Lance la suite
> complète, ruff, mypy, `node --check` et `python outils/ci.py data` avant chaque push. Termine par une passation
> et « Agent actif : libre ».

## [nouveau] Passation de Claude — 11/11/2026, 12 h 40 UTC

Session autonome planifiée (12 h 17 → 12 h 40 UTC). Branche `claude/referentiel-v2`. Commits fonctionnels :
**`072b444`** (P1) et **`4054e61`** (§ 6 rapprochement).
Aucun travail non commité. Revue des commits depuis la passation de 08 h 57 : aucun commit de Codex, rien à
corriger. CI de `072b444` : run *push* vert ; run *pull_request* rouge sur un seul test navigateur de l'essai
portable Windows (`tests_web/test_referentiel_codes.py::test_texte_saisi_echappe_dans_la_table_et_le_detail` :
après `page.reload`, `[data-ref-objet="lexique"]` n'apparaît pas en 30 s) — **intermittent** (vert au run
*push* du même commit, vert en local), sans lien avec le lot moteur ; **domaine Codex, à examiner** (attente
après rechargement, ou écran d'arrivée après reload).

### Lots faits (moteur, tests nommés)

| Lot | Commit | Tests |
| --- | --- | --- |
| **P1 variables internes déclarées** BI, EI, MI, RI : point « Interne », présence « Option » seule, ni source ni alarme ; `generer_internes` ; exclues de l'échange, du %MW, des E/S, de TOPKAPI, du rapprochement ; XSY sans `topologicalAddress` ; contrôles de noms, de type, homonymes ; règle « auto » refusée | `072b444` | `tests/test_variables_internes_p1.py` (18) |
| **Cahier § 6** : `SEUIL_CONFIANCE = 80` (aucun faux connu ≥ 80 ; max 79), `Proposition.confiance` / `raison`, mesures publiées `validation/hybride/SEUIL_CONFIANCE.md` (générées, comparées au calcul), `confirmables_en_lot` / `confirmer_en_lot` / `annuler_lot`, confirmation unitaire tracée, `journal_rapprochement` dans le fichier | `4054e61` | `tests/test_seuil_confiance_rapprochement.py` (10) |

Preuves locales : 618 tests Python (30 ignorés ici faute de PyMuPDF / PySide6 ; 0 en CI), 36 tests navigateur
+ 34 sous-cas, ruff, mypy 46 fichiers, `node --check`, audit données 0 détection, banc dans les seuils.

### Choix prudents consignés (réversibles)

- P1 : **aucune variable interne ajoutée au référentiel livré** ; type logique pris du signal, jamais déduit de
  la famille ; variables internes placées après l'échange dans le XSY (import Control Expert non essayé).
- § 6 : lecture **stricte** du cahier — le seuil couvre *tous* les candidats faux (le 79 est un second
  candidat), d'où un rappel au seuil de 13,9 % sur les deux jeux. Ne compter que les premiers candidats
  donnerait un seuil de 65 et plus de confirmations en lot : **décision à valider**. Le lot ne vérifie jamais
  l'accès TOPKAPI ; une ligne modifiée après le lot n'est pas touchée par l'annulation (signalée).

### Étape exacte de reprise

1. Vérifier le run CI du dernier commit (`list_workflow_runs`, branche `claude/referentiel-v2`).
2. **Codex (interface)** : écrans de la passation de 08 h 57 (R3–R8, reprise du modèle figé, options MV) ;
   plus : afficher `confiance` et `raison` des candidats, bouton « Confirmer en lot · n »
   (`Session.confirmables_en_lot` / `confirmer_en_lot`), journal et « Annuler le lot » (`annuler_lot`) — routes
   à ajouter dans `serveur.py` ; variables internes dans la fiche équipement et l'écran Variables (préréglage
   séparé, jamais dans « Table d'échange » ni « Télétransmission ») ; test intermittent ci-dessus.
3. **Claude (moteur)** : exigence « partiel » suivante la plus utile : V1-7-03 (copies horodatées avant
   *chaque* opération lourde : adressage appliqué, import, confirmation en lot) puis V1-7-05 (reprise sans
   perte après arrêt brutal : fichier `.tmp` orphelin, verrou). Commencer par inventorier les opérations
   lourdes de `session.py` qui écrivent sans `.bak`.

### Décisions à valider par l'utilisateur

- **§ 6** : [traité le 11/11, l'utilisateur s'en remet à la recommandation] seuil **strict 80** conservé pour
  la 1.0 (aucun faux connu, même en second candidat ; précision avant rappel). À remesurer sur des exports
  réels anonymisés avant tout abaissement.
- **P1** : [traité le 11/11 par l'utilisateur] candidats BI de MV ajoutés (`DIS` = disponible, `DSC` =
  discordance), option « Variables internes ». Reste : types logiques de EI, MI, RI s'ils doivent être imposés.
- **P5** : [traité le 11/11 par l'utilisateur] `ST_<repère>_ARR` (3 lettres), `TC_AR` inchangé.
- **R1** : [validé par l'utilisateur le 11/11] « CT est supprimé, il est contenu dans FT » (doctrine n° 5, déjà
  appliquée au référentiel livré et aux projets neufs). Pour un projet existant, la conversion d'un équipement CT
  en FT se fera par l'adoption contrôlée **en conservant le repère et les noms d'origine** (doctrine n° 6 :
  repères, adresses et TOPKAPI jamais réaffectés). Lot moteur à faire ; il remplace le blocage actuel.
- Toujours en attente : **A1, D5-b, A2/A7/A8/A10/A11**. Aucune n'a été appliquée.

## [nouveau] Passation de Claude — 11/11/2026, 08 h 57 UTC

Session autonome planifiée (08 h 19 → 08 h 57 UTC). Branche `claude/referentiel-v2`, dernier commit
fonctionnel **`9a419af`** (le commit de passation le suit). Aucun travail non commité. CI GitHub : verte sur
`14e1c07`, `2253920`, `d158c43`, `417d686`, `755585c`, `9b099c9` (`ddd3e0a` annulé par le run suivant, contenu
inclus dans `9b099c9`) ; runs de `60437bf` et `9a419af` lancés, à vérifier au démarrage.

### Corrigé en premier : CI Windows rouge par intermittence (domaine Codex, signalé)

`test_cinq_etapes_accessibles_sans_ecriture` échouait (runs 31, 33, 37, 39) : le tableau de bord, plus lent,
finissait après le clic sur une autre étape et réaffichait son écran. **Défaut réel de `app.js`** : jeton de
navigation, un écran quitté n'affiche plus rien et n'écrase plus `E.es`, `E.mat`, `detailEtape`, `v31Tele`,
`sel`. Test qui reproduit la course : `test_chargement_lent_du_tableau_de_bord_ne_remplace_pas_l_etape_choisie`.

### Lots faits (moteur, tests nommés, suite complète verte en local)

| Lot | Commit | Tests |
| --- | --- | --- |
| P5 profil VANNE_MV : options « Arrêt dédié câblé » (`ES_AR` → `ST_<repère>_AR`) et « Défauts de manœuvre détaillés » (`TS_DOV`, `TS_DFE`) | `2253920` | `tests/test_profil_vanne_mv_p5.py` |
| P8 / R9 homonymes entre ouvrages du même projet Control Expert, recette web | `d158c43` | `tests/test_homonymes_p8.py` |
| R2 + R3 version calculée par profil, état de synchronisation, `GET /api/referentiel/synchronisation` | `417d686` | `tests/test_synchronisation_profils_r2_r3.py` |
| R4 conflits de surcharge dans l'aperçu, `revenir_au_standard`, `POST .../revenir-au-standard` | `755585c` | `tests/test_conflits_surcharge_r4.py` |
| R5 rapport d'impact (`GET .../impact`) ; R7 journal `journal_referentiel`, refus motivé (`POST .../refuser-mise-a-jour`) | `ddd3e0a` | `tests/test_rapport_impact_r5.py`, `tests/test_journal_decisions_r7.py` |
| R6 acceptation en un geste (`GET .../propagation`, `POST .../accepter-propagation`), `deja_valide` / `deja_exporte` | `9b099c9` | `tests/test_propagation_conception_r6.py` |
| Reprise contrôlée d'un modèle figé (étape 4 de la passation Codex) : `apercu_modele`, `adopter_modele`, routes ; « actualiser le modèle » protégé | `60437bf` | `tests/test_adoption_modele_fige.py` |
| P3 alerte « nouveau code hors 3 lettres » | `9a419af` | `tests/test_regle_trois_lettres_p3.py` |

Preuves locales finales : **590 tests Python** (5 ignorés localement seulement : Windows), **36 tests navigateur
et 34 sous-cas**, mypy 46 fichiers, `node --check`, audit données 0 détection, banc de performance dans les
seuils (après R6). Ruff non exécutable ici (PyPI bloqué par le proxy) : contrôlé par la CI.

### Choix prudents consignés (réversibles)

- **P5 : `ST_<repère>_AR` et non `ARR`** (doctrine n° 3, même suffixe que `TC_AR` ; pratique des types PD, SP,
  SV, XV). Statut des trois signaux « À valider ». Détail : `docs/DECISIONS_CONCEPTION_PROFILS.md`.
- P8 : périmètre = `nom_projet` (projet Control Expert) ; « table d'échange commune » non modélisée, non contrôlée.
  Une anomalie par équipement et par ouvrage concurrent (liste complète des noms), ouvrages archivés ignorés.
- R7 : l'annulation d'une adoption restaure le fichier à l'octet, elle n'ajoute donc pas d'entrée au journal.
- R6 : un fichier antérieur sans `deja_valide` / `deja_exporte` a un historique inconnu → jamais éligible.
  Le premier export d'un ouvrage neuf enregistre l'indicateur dans son fichier.

### Étape exacte de reprise

1. Vérifier les runs de `60437bf` et `9a419af` (`list_workflow_runs`, branche `claude/referentiel-v2`).
2. **Codex (interface)** : pastilles R8 et états de synchronisation (`/api/referentiel/synchronisation`) ;
   conflits R4 dans la boîte d'adoption (`apercu.conflits`, bouton « Revenir au standard ») ; rapport d'impact
   (`/api/referentiel/impact`) à la publication ; journal ; acceptation en un geste ; écran de reprise du modèle
   figé (le parcours web bloque encore un changement de clé de modèle figé) ; options MV dans la fiche.
3. **Claude (moteur)** : **P1 variables internes déclarées** (BI, EI, MI, RI). Points à toucher : `catalogue.py`
   (`FAMILLES_CATALOGUE`), `modele.generer` (type logique du signal, pas `type_echange` ; jamais d'adresse),
   `plan_adresses` / `adressage.py` (exclure : aucun %MW), `teletransmission.py` et export TOPKAPI (exclure),
   `export_xlsx.py` (table d'échange : exclure), XSY (variable non localisée, format déjà supporté sans
   `topologicalAddress`), contrôles « pas d'adresse » (exclure). Tests : non sélectionné → absent ; jamais dans
   TOPKAPI ni la table d'échange ; aucun %MW ; XSY sans adresse. **Ne pas** ajouter de type logique par famille
   sans la spécification (types EI/MI/RI non définis dans le dépôt) ; candidats BI de MV (P5) : `DIS` ambigu
   (disponible ou discordance ?) → demander, ou n'ajouter que `OUV`, `FER`, `DOV`, `DFE`, `DEF`.

### Décisions à valider par l'utilisateur

- **P5** : `ST_<repère>_AR` (retenu) ou `ST_<repère>_ARR` (texte de P5) ?
- **P1** : types logiques des familles EI, MI, RI et sens de `DIS` pour les candidats BI de MV.
- Toujours en attente : **A1, R1, D5-b, A2/A7/A8/A10/A11**. Aucune n'a été appliquée.

## [nouveau] 10/11/2026 23 h 35 — Décisions de conception des profils (P1 à P9)

L'utilisateur a demandé à Claude de trancher en concepteur senior la spécification
« Codification et profil VANNE_MV ». Décisions et lots autorisés :
**`docs/DECISIONS_CONCEPTION_PROFILS.md`**. **Ordre des lots mis à jour à 23 h 50** (ajout des
décisions R2 à R9 sur la propagation des profils, même fichier) : P5 → P8 →
R2+R3 (version calculée par profil, état de synchronisation) → R4 (conflits de
surcharge locale) → R5+R7 (impact multi-ouvrages, journal) → R6 → puis P1, P3.
Interface R8 et écrans associés : Codex. Aucun renommage de code existant ; `RTR`
conservé ; options modulantes de MV conservées jusqu'à A1.

## [nouveau] Passation à Claude — 10/11/2026, 19 h 57 UTC

**Codex s'arrête à la demande de l'utilisateur après le lot en cours terminé.**
Branche unique : `claude/referentiel-v2`. Dernier commit fonctionnel : **`19c64eb`** ;
le commit de passation le suit immédiatement. Reprendre au HEAD distant, sans
réappliquer les lots et sans revenir sur release/1.0. Aucun travail non commité.

### Lots terminés et poussés par Codex

- `84bdd22` : Lexique, Dictionnaire et Correspondances ; recherche, pagination,
  clavier, édition en brouillon, motif et ambiguïté ; archivage/réactivation du type,
  colonne Archivé dans Excel, anciens classeurs et modèle sans E/S préservés.
- `1a40195` : adoption détaillée par équipement, confirmations individuelles décochées,
  aperçu périmé refusé, téléchargement de la sauvegarde, Annuler l'adoption avec
  restauration du fichier à l'octet. Copie séparée avant annulation ; sauvegardes
  uniques ; retour arrière abandonné lors d'un nouvel ouvrage, d'une ouverture ou
  d'un Enregistrer sous. `annuler_adoption(enregistrer=True)` est utilisé par le web ;
  l'appel historique sans argument conserve son comportement en mémoire.
- `53783c6` : Inter et JetBrains Mono embarquées avec licences OFL, Lucide ISC local,
  À propos et empreintes ; en-têtes/cellules Variables alignés avec le panneau ouvert.
- `19c64eb` : répartition E/S avec `point`, cinq étapes accessibles, vide connu distingué
  d'une source indisponible, aucun taux ni faux bilan sans anomalie, palette sans
  second accent corail. Le cahier §4 demande « aucun compteur à zéro » : les zéros
  connus sont des états vides explicites, pas des compteurs nuls ni Non disponible.

Correctifs moteur/Excel nécessaires aux deux premiers lots signalés dans leurs
messages de commit. Les données du catalogue n'ont pas changé dans ces lots UI.

### Preuves du dernier état fonctionnel

- **557 tests Python, 0 ignoré**, 131,23 s ; couverture moteur **88,575957 %**, trois
  modules d'export industriel **100 %**. Rapports :
  `/workspace/ogias-cloud/v2/dashboard-python-final/`.
- **35 tests navigateur et 34 sous-cas**, 47,62 s, aucune exception JS ; rapports :
  `/workspace/ogias-cloud/v2/dashboard-web-complet/`. Les six scénarios Variables
  initiaux sont conservés. Les réponses synthétiques des tests de présentation
  ne qualifient aucun matériel ou format industriel.
- Ruff, mypy (44 fichiers), syntaxe JS et audit données conformes (0 détection,
  0 erreur). Dépendances inchangées depuis l'audit des 48 paquets, sans vulnérabilité.
- Sept seuils de performance passés : `validation/performance/RESULTAT_DASHBOARD_V2.json`,
  adressage 0,386 s, rendu 56 ms, filtrage 83 ms ; limites inchangées.
- Captures réelles inspectées face aux trois maquettes :
  `validation/interface_v2/maquettes/COMPARAISON.html`, écarts et mesures dans README
  et maquettes-mesures.json. **Conformité globale UI encore partielle.**

### Étape exacte de reprise pour Claude

1. Fetch/pull de la branche et vérification du run CI du HEAD. L'API GitHub est
   bloquée ici par la politique réseau (Forbidden, déjà constaté à plusieurs reprises) :
   Codex n'a pas certifié le run distant. Les contrôles locaux passent.
2. Lire le checkpoint d'ETAT_TRAVAIL.md et la comparaison des maquettes.
3. L7 / §4 : relier chaque constat du tableau de bord à sa correction précise
   (actuellement tous vont à Recette), puis dimensions/densité/historique du panneau
   Variables. Activité récente uniquement depuis des faits enregistrés. Le taux de
   recette exige un véritable total des contrôles ; ne pas le déduire des seules anomalies.
4. Côté moteur : les signaux d'un modèle figé ne sont pas adoptés par le catalogue.
   Le parcours web le signale et bloque un changement de clé de ce modèle ; une
   migration dédiée reste à traiter. Voir docs/ADOPTION_REFERENTIEL.md.
5. Continuer les exigences partielles du cahier selon les règles V2 et le binôme.

**Décisions toujours en attente : A1, R1, D5-b, A2/A7/A8/A10/A11.** Ne pas intégrer
les 49 ajouts ou renommages V1, ne pas convertir les projets CT, ne pas changer les
règles auto concernées. Les noms historiques FDC du scénario HV viennent des jeux
et du moteur existants ; aucun nouveau préfixe, format ou adressage dans ces lots.
CE 14.1 / TOPKAPI / S4W-Tools restent en attente de preuves utilisateur.

PR #1 jamais fusionnée ; aucun tag ou release créé. Seule destination de push :
`claude/referentiel-v2`. PR_DESCRIPTION.md tenu à jour si l'API GitHub reste inaccessible.

## [en cours] 10/11/2026 17 h 30 — Mission V2 autonome (branche `claude/referentiel-v2`)

L'utilisateur a autorisé le travail autonome sur la branche dédiée
`claude/referentiel-v2` (PR vers `release/1.0`, jamais fusionnée par un agent).
Consigne complète : `docs/referentiel/PROMPT_CLAUDE_AUTONOME_OGIAS_V2.md` ;
spécification : `docs/referentiel/OGIAS_REFERENTIEL_V2.xlsx` ; écarts :
`docs/RAPPORT_ECARTS_V2.md`. Claude travaille ; Codex prend le relais à l'arrêt
de Claude, sur la même branche, en lisant la passation ci-dessous.

## [traité pour les étapes UI 1–3 ; L7 en cours] Passation à Codex — 10/11/2026 vers 18 h 30

Branche `claude/referentiel-v2` (PR vers `release/1.0`, ne pas fusionner). Lire
d'abord `docs/referentiel/PROMPT_CLAUDE_AUTONOME_OGIAS_V2.md` : mêmes règles.

Fait par Claude (tests nommés, suite complète verte en local) :
- L1 `docs/RAPPORT_ECARTS_V2.md`.
- L2 adoption contrôlée : `genvar/adoption.py`, `Session.apercu_adoption /
  adopter_referentiel(types, renommages_confirmes) / annuler_adoption`, routes
  `/api/referentiel/adopter` et `/api/referentiel/annuler-adoption`, boîte
  d'adoption (`adoptionControlee` dans `app.js`) ; correspondances dans
  `referentiel_modeles.json` contrôlées par le cycle. Tests :
  `tests/test_adoption_controlee.py`.
- L3 noms physiques : `modele.suffixe_physique`, champ `suffixe_es` (5 signaux),
  organe FDC retiré de 9 signaux, contrôles d'unicité du nom physique, colonne
  Excel. Tests : `tests/test_noms_physiques_v2.py` ; noms attendus des projets
  neufs mis à jour dans 3 fichiers de tests (clés inchangées).
- L4 CT supprimé, correspondances CT → FT, dictionnaire corrigé. Tests :
  `tests/test_ft_ct_v2.py`.
- L5 règles : champ `gouvernance` (32 relations documentaires, 32 suggestions),
  textes d'algorithme sortis vers `docs/referentiel/REGLES_AVANT.csv`, affichage
  de la note de gouvernance (`regles.texte`), colonne Excel, contrôle des
  valeurs. Tests : `tests/test_regles_documentaires_v2.py` ; 7 assertions
  d'anciens tests inversées (le texte d'algorithme ne doit plus s'afficher).

Décisions à valider (ne pas appliquer sans accord) :
- **D5-b** : 10 règles « auto » classées suggestion restent retenues d'office :
  PM-05 (CP_HF, CP_NDEM), CU-03, LT-02, PT-02, TT-02, AT-02, FT-02, DA-01 (TS_DEF /
  TS_DEFMES), FT-03 (CP_VOL), GEN-01 (TR → RTR). Les rendre manuelles change le
  contenu de tous les projets neufs (20 tests de scénarios et plans). GEN-01 est
  probablement une relation documentaire (retour de consigne) : à reclasser ?
- **R1** : conversion CT → FT d'un projet existant (le repère contient le code
  du type). Aucune conversion n'est faite ; l'adoption la bloque.
- A1, A2, A7, A8, A10, A11 du classeur V2 (`A_VERIFIER`).

Mise à jour 10/11 vers 20 h (Claude, Codex n'ayant rien poussé) — L6 fait :
`Session.dupliquer_modele / archiver_modele / archiver_type`, statut de modèle
« archivé » (non proposé, refusé pour un nouvel équipement, réversible),
suppression d'un modèle ou d'un type **bloquée** s'il est employé par un projet
enregistré (`referentiel_depot.modeles_utilises`, `ouvrages_utilisant`),
correspondances éditables dans le brouillon (`ajouter/supprimer_correspondance`,
motif obligatoire, ambiguïté refusée) et onglet Excel « Correspondances ».
Boutons Dupliquer / Archiver dans l'écran Modèles. Tests :
`tests/test_gestion_referentiel_v2.py`.

Reprise exacte pour Codex :
1. Vérifier le run CI du dernier commit de la branche.
2. Écrans : lexique, dictionnaire, correspondances (le moteur et les actions
   `editer` existent) ; bouton « Archiver le type » ; l'indicateur `archive` des
   types de modèles n'est pas encore porté par l'export Excel (à ajouter).
3. Écran d'adoption : détail par équipement, lien vers la sauvegarde, bouton
   « Annuler l'adoption » (route `/api/referentiel/annuler-adoption` prête),
   tests navigateur.
4. Puis amélioration continue selon le cahier (§ 5 L7 de la consigne).

## [traité — pris en compte par Codex, état ci-dessous] 10/11/2026 — Travail en binôme Claude / Codex

Codex a atteint sa limite d'utilisation ; Claude a pris le relais sur `release/1.0`
le 10/11 après-midi et avance tant que ses crédits le permettent. **À son retour,
Codex reprend la main à partir du dernier commit de `release/1.0`** (lire `git log`
et ce fichier : la liste « Fait par Claude » est tenue à jour). Les deux agents travaillent
désormais en binôme sur la même branche, par petits commits, et se passent le
relais par ce fichier et `ETAT_TRAVAIL.md`.

Objectif commun inchangé : un produit fini commercial, professionnel et
industriel — toutes les fonctions nécessaires, tout testé, fonctionnel, rapide,
avec une interface sérieuse et une UI/UX irréprochable conforme aux maquettes.
Le cahier `docs/CAHIER_DES_CHARGES_V1.md` reste la seule référence ; toutes les
contraintes permanentes (§ 11) et garde-fous de la consigne autonome s'appliquent.

Fait par Claude (voir `git log`) :
1. CI GitHub entièrement verte (5 jobs, Windows et Linux, 467 tests, 0 ignoré) ;
   run : https://github.com/Mcodea/OGIAS/actions/runs/42833016469.
2. Contrôle anti-données réelles levé sans liste blanche (classeur masqué,
   8 lignes « Retiré » retirées).
3. V1-3-01 : les 732 lignes de modèles alignées sur le classeur, test de conformité.
4. Bibliothèque des E/S : correspondance complète établie, intégration bloquée
   sur une décision de modèle — voir `docs/INTEGRATION_BIBLIOTHEQUE_ES_V1.md`.
5. V1-3-02 / V1-3-03 : `genvar/lexique.py` ; `_suffixe_propose` sans troncature
   (code du catalogue, puis lexique ; alerte « suffixe à raccourcir » > 12) ;
   lexique (354 entrées) dans `referentiel_modeles.json`, donc publié, versionné,
   archivé ; édition dans le brouillon (`editer` : ajouter/modifier/supprimer_lexique) ;
   onglet « Lexique » à l'export/import Excel (suppression explicite, export ancien
   sans onglet accepté). Tests : `tests/test_lexique_v1.py`. Reste : écran du lexique
   dans l'interface Référentiel ; installations existantes : le lexique arrive avec
   la nouvelle révision (lot Migration § 3), jamais injecté hors cycle.
6. V1-3-11 à V1-3-14 : `genvar/dictionnaire_es.py` ; dictionnaire (81 entrées,
   clé NATURE.CODE) dans `referentiel_modeles.json` ; erreurs (format 2–9, nature,
   libellé, même code deux sens) et alertes (répétition, deux codes un libellé,
   code non standard du catalogue : 42 alertes tant que l'harmonisation E/S n'est
   pas validée) ; brouillon (`ajouter/modifier/supprimer_code_es`) ; onglet Excel
   « Dictionnaire E-S ». Tests : `tests/test_dictionnaire_es_v1.py`.

À reprendre par Codex, dans cet ordre :
1. Écrans du lexique et du dictionnaire dans l'interface Référentiel (moteur prêt,
   points 5 et 6).
2. Bibliothèque des E/S selon la décision consignée ci-dessous par l'utilisateur ;
   sans décision, avancer sur les sujets indépendants (types ajoutés, modèles
   FV/DG, Matériel).
3. Migration (§ 3) puis interface, rapprochement, fiabilité, productivité,
   documentation, dans l'ordre du cahier. Garder la CI verte à chaque commit.

## [traité — pris en compte par Codex, état ci-dessous] Décision utilisateur — modèle des E/S (10/11/2026)

Conserver le modèle métier : séparer les E/S physiques (ex. `ET_VAN01_OUV`, fin
de course) des informations fonctionnelles de télétransmission (`TS_VAN01_OUV`),
associées dans le modèle de données mais jamais confondues, sans doublon inutile.
1. Les E/S physiques sont définies par le modèle d'équipement.
2. Les informations de télétransmission sont associées à ces E/S ou à des états calculés.
3. E/S physique : affectation matérielle ; information de télétransmission :
   correspondance de communication uniquement si nécessaire.
4. Pas d'adresse %MW supplémentaire systématique pour chaque E/S.
5. Compatibilité des projets existants : migration non destructive.
6. Aucune duplication fonctionnelle inutile.
7. Vannes : règles de cohérence fins de course ouvert/fermé ↔ états fonctionnels.

**Avant toute modification**, le modèle proposé et ses conséquences (projets
existants, listes d'E/S, variables, exports Schneider, SOFREL, TOPKAPI) sont
présentés : `docs/MODELE_DONNEES_ES_V1_PROPOSITION.md`. **Aucune migration sans
validation explicite de l'utilisateur**, consignée ici.

## [traité — pris en compte par Codex, état ci-dessous] Validation utilisateur de la proposition de modèle E/S (10/11/2026)

Principes validés, **code non autorisé** à ce stade. Précisions de l'utilisateur :
même suffixe fonctionnel pour l'E/S et l'information quand elles décrivent la même
chose (`ET_MV01_OUV` / `TS_MV01_OUV`, pas `ET_MV01_FDC_OUV`) ; pas de `code_es` ni
d'`ident_v1` sauf nécessité démontrée ; correspondances internes seulement si
aucun mécanisme n'existe, jamais ambiguës ; tout renommage, physique compris,
confirmé explicitement ; aucune migration automatique ; référentiel modifiable
depuis l'interface (ajouter, modifier, supprimer non utilisé, archiver, remplacer,
dupliquer, importer/exporter, historique) sans bibliothèque parallèle ; règles
vannes conservées ; extension FV/VV après examen de leur instrumentation.

Rapport de conformité demandé et remis : `docs/RAPPORT_CONFORMITE_MODELE_ES_V1.md`.
**Attendre la validation de ce rapport avant toute modification de code ou de données.**

## Passation reçue par Codex — 10/11/2026 (sur `release/1.0`, avant de voir la branche V2)

Les quatre entrées précédentes ont été lues et prises en compte. La validation
finale du rapport E/S n'est pas reçue dans ce chat : aucun changement de ce modèle
ni migration n'est engagé. L'état distant `c3e506e` est intégré sans écrasement ni
réécriture ; les implémentations communes lexique/dictionnaire sont conservées.
Les travaux indépendants continuent sur leur interface et leurs tests navigateur.
Voir le checkpoint actif de `ETAT_TRAVAIL.md` pour les preuves du lancement commun.

Note Claude (fusion du 10/11, 19 h 45) : ce travail de Codex sur `release/1.0`
(`e9cbf79`, `5c31e8b`) est fusionné dans `claude/referentiel-v2` sans conflit de
code. La validation des principes E/S et l'autorisation de coder sur la branche
dédiée ont été données après coup par l'utilisateur : voir l'entrée « Mission V2
autonome » en tête de ce fichier. **Codex : travailler désormais sur
`claude/referentiel-v2`**, pas sur `release/1.0`.

### Interface des objets communs réalisée par Codex

Lexique et Dictionnaire sont consultables et éditables dans le brouillon de
l'écran Référentiel. Preuves : `tests_web/test_referentiel_codes.py` ; captures
`validation/interface_v1/referentiel/`. Aucun changement du modèle E/S ni migration.
