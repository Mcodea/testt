# OGIAS — Mission autonome : intégration du référentiel V2 et amélioration continue

Tu travailles seul, sans interlocuteur jusqu'à demain soir. Ne pose aucune question : quand un choix est
réversible, prends la décision la plus prudente, écris-la dans `ETAT_TRAVAIL.md` et continue. Quand il est
irréversible, prépare-le, décris-le dans `docs/INSTRUCTIONS_EN_COURS.md` comme « décision à valider » et passe
au sujet suivant. Ne t'arrête jamais sur un blocage : contourne-le par un autre lot.

## 1. Dépôt, branche, documents

- Dépôt `Mcodea/OGIAS`. Pars du **dernier** commit de `release/1.0` (`git fetch` ; ne jamais écraser un commit
  plus récent). Travaille sur la branche dédiée **`claude/referentiel-v2`** (crée-la si elle n'existe pas,
  sinon reprends-la et rebase-la sur `release/1.0`). Ouvre une **PR vers `release/1.0`**, sans la fusionner.
- Le classeur joint `OGIAS_REFERENTIEL_V2.xlsx` : s'il n'est pas déjà dans `docs/referentiel/`, ajoute-le tel
  quel dans le premier commit. C'est une **spécification cible**, pas un fichier d'import : lis `GUIDE V2`,
  `DECISIONS`, `JOURNAL_V2` (140 modifications), `A_VERIFIER`, `CONTROLES_V2`. Les onglets `REGLES_AVANT`,
  `ARCHIVE …` et `Provenance source` servent à l'audit seulement : ne jamais les réimporter.
- Lis **en entier** avant de coder, dans cet ordre : `docs/CAHIER_DES_CHARGES_V1.md`, `ETAT_TRAVAIL.md`,
  `docs/INSTRUCTIONS_EN_COURS.md`, `docs/RAPPORT_CONFORMITE_MODELE_ES_V1.md`,
  `docs/MODELE_DONNEES_ES_V1_PROPOSITION.md`, `docs/INTEGRATION_BIBLIOTHEQUE_ES_V1.md`, `docs/CI.md`.
  Ils contiennent tout ce qui a été décidé le 10/11/2026.

## 2. Déjà fait le 10/11 (ne pas refaire, ne pas casser)

CI GitHub verte (5 jobs, Windows et Linux, 0 test ignoré) ; contrôle anti-données réelles sans liste blanche ;
732 lignes de modèles alignées sur le classeur V1 ; `genvar/lexique.py` (suffixe jamais tronqué, alerte au-delà
de 12 caractères, lexique de 354 entrées publié et versionné, éditable, onglet Excel) ;
`genvar/dictionnaire_es.py` (81 codes, contrôles V1-3-11 à 14) ; `outils/correspondance_es_v1.py` (144 E/S
rapprochées, 49 ajouts) ; rapports de modèle et de conformité.

## 3. Doctrine et décisions validées (permanentes)

1. **OGIAS n'impose pas l'algorithme.** L'analyse fonctionnelle définit calculs, conditions et temporisations ;
   le programme automate les réalise. Une règle est soit une *relation documentaire* (information fonctionnelle
   associée à une E/S), soit une *suggestion optionnelle* de signal, soit un *contrôle de cohérence*. Aucun
   signal calculé n'est créé sans sélection de l'utilisateur. Aucune temporisation ni valeur par défaut inventée.
2. E/S physiques (`ET`, `ST`, `EA`, `SA`) et informations de télétransmission (`TS`, `TC`, `TM`, `TR`, `RTR`,
   `CP`) distinctes, jamais dupliquées ; **aucun %MW pour une simple E/S physique**.
3. Même suffixe quand l'E/S et l'information sont la même chose : `ET_MV01_OUV` / `TS_MV01_OUV`. « Fin de
   course » va dans la description. Le code utilisé est `FER` (pas `FERM`).
4. `suffixe_es` facultatif, **uniquement** pour les 5 collisions de clé interne : `MV.ES_FDC_OUV` → `OUV`,
   `MV.ES_FDC_FER` → `FER`, `MV.ES_CONS_POS` → `POS`, `PM.ES_CMD_MA` → `MA`, `PM.ES_CONS_FREQ` → `FREQ`.
   Identifiants internes inchangés. Pas de `code_es`, pas d'`ident_v1` (traçabilité déjà assurée).
5. **CT supprimé**, consolidé dans **FT**. FT accepte indépendamment `EA_…_DEB`, `ET_…_IMP`, `ET_…_SENS`,
   `ET_…_DEF_EXT` (options matérielles) ; `TS_DEF` et `TS_DEF_EXT` restent distincts ; un seul `CP_VOL`, sans
   méthode de calcul imposée ; la correspondance 0/1 de `ET_SENS` est un paramètre de l'équipement.
6. Projets existants : rien ne change sans **adoption explicite** ; tout renommage, physique compris, est
   confirmé ligne à ligne ; sauvegarde avant, retour arrière possible ; adresses (%MW, %I/%Q/%IW, voies S4W),
   repères et correspondances TOPKAPI jamais réaffectés ni recalculés.
7. Référentiel unique (dépôt `referentiel_depot`), modifiable depuis l'interface : ajouter, modifier, retirer,
   remplacer, dupliquer, désactiver, archiver, importer/exporter, comparer, revenir en arrière. Une modification
   locale d'un équipement ne réécrit jamais le type ; le référentiel ne réécrit jamais un projet enregistré.
8. Les 54 renommages et 49 ajouts du rapport V1 ne sont **pas approuvés** (A1) : ne pas les appliquer.

## 4. Interdits absolus

Données réelles de l'ancien exploitant (noms de sites, adresses IP, identifiants) ; modification des projets ou
des données d'exploitation réelles ; fusion de la PR ; publication d'une révision sur un poste ; migration
appliquée à un projet réel ; affaiblir un test, un seuil, une couverture ou un corrigé ; liste blanche dans le
contrôle anti-données ; IA embarquée ; caractéristique constructeur, format industriel ou adresse inventés ;
déclarer une compatibilité Control Expert / S4W / TOPKAPI sans essai réel ; annoncer une fonction terminée sans
test ; utiliser `validation/aveugle` hors évaluation finale.

## 5. Lots, dans cet ordre

**L1 — Rapport d'écarts** (`docs/RAPPORT_ECARTS_V2.md`, court) : schéma réel du référentiel contre le classeur
V2 (onglets, colonnes ajoutées, adaptateur nécessaire), fichiers impactés, table `ancienne clé → nouvelle clé`
avec impact E/S, table de télétransmission, adresses et TOPKAPI (CT → FT, 9 organes FDC, 5 `suffixe_es`), points
`A_VERIFIER` encore ouverts. Puis enchaîne.

**L2 — Correspondances et adoption contrôlée** : liste `correspondances` dans le référentiel (refus des
correspondances ambiguës) ; `Session.adopter_referentiel` remplacé par un aperçu ligne à ligne, chaque
renommage décoché par défaut, sauvegarde horodatée (mécanisme `.bak` de `projets.py`), retour arrière, report des
adresses par correspondance. Écran d'adoption dans l'interface web.

**L3 — Noms physiques** : `suffixe_es` (lecture dans `modele.py`, contrôle d'unicité du nom physique par
équipement dans `catalogue.py`, colonne Excel) ; retrait de l'organe `FDC` des 9 signaux dans le **référentiel
livré**. Les projets existants, qui ont leur référentiel figé, gardent leurs noms à l'octet.

**L4 — CT → FT** : suppression de CT du référentiel livré ; correspondances `CT.CP_VOL → FT.CP_VOL`,
`CT.TS_ABSIMP → FT.TS_ABSIMP`, entrée physique de CT → `FT.ES_IMP` ; migration uniquement par l'adoption
contrôlée, avec inventaire, aucune écriture sur une variable FT existante, aucun doublon, cas incertains signalés.
Paramètre d'équipement « sens 0/1 » pour `ET_SENS`. Ne pas passer `ES_DEB` en « Option » sans décision (A2).

**L5 — Règles documentaires** : champ `gouvernance` (relation documentaire / suggestion optionnelle /
contrôle de cohérence) ; textes d'algorithme sortis des champs actifs vers `docs/referentiel/REGLES_AVANT.csv` ;
`Mode` historique jamais exécutoire ; générateur et interface : aucune information calculée créée sans
sélection ; FT-03/04 n'imposent pas le calcul de `CP_VOL` ; FT-05 n'exige pas l'entrée analogique.

**L6 — Gestion du référentiel** : dupliquer un modèle, archiver un modèle ou un type, bloquer la suppression d'un
élément utilisé par un projet enregistré (`ouvrages_utilisant`) en proposant l'archivage, remplacer par
correspondance, écrans du lexique et du dictionnaire.

**L7 et suivants — amélioration continue**, selon `docs/CAHIER_DES_CHARGES_V1.md` et `ETAT_TRAVAIL.md` :
interface conforme aux maquettes (`docs/maquettes/`, rigueur visuelle, accessibilité, clavier), rapprochement
hybride, fiabilité et performance (banc et seuils inchangés), productivité, documentation utilisateur,
installation portable. Choisis à chaque fois l'exigence « partiel » la plus utile et termine-la entièrement.

## 6. Méthode de chaque lot : améliorer, tester, s'autocritiquer

1. **Comprendre** : lis le code concerné avant de le modifier ; réutilise l'existant ; patch minimal, pas de
   refonte.
2. **Tester d'abord** : écris les tests du comportement attendu et les tests de non-régression (en particulier
   « projet existant identique à l'octet », « adoption refusée → fichier inchangé », « adoption puis retour arrière
   → fichier identique », « aucun nouveau %MW », « export/import du référentiel aller-retour sans perte »).
3. **Coder**, puis lancer localement : suite complète, `ruff`, `mypy`, `node --check`, contrôle anti-données
   (`python outils/ci.py data`). Rien ne part rouge.
4. **S'autocritiquer** avant chaque push : relis ton diff comme un relecteur hostile (correction, cas limites,
   données existantes, sécurité, lisibilité, doublons, doctrine du § 3). Corrige ce que tu trouves. Écris en
   trois lignes ce que tu as vérifié dans le message de commit ou dans `ETAT_TRAVAIL.md`.
5. **Pousser par lot complet** (un run de CI par lot, pour économiser), puis vérifier le run GitHub
   (`gh api repos/Mcodea/OGIAS/actions/runs?head_sha=…`) et corriger jusqu'au vert. Trois échecs sur le même point :
   marque-le « bloqué » avec le diagnostic, et passe au lot suivant.
6. **Tracer** : mets à jour la ligne correspondante de `ETAT_TRAVAIL.md` (fait seulement avec test nommé), et la
   PR (`PR_DESCRIPTION.md` si l'API refuse).

Tests obligatoires avant de déclarer L2 à L5 terminés : 0 référence CT dans le catalogue livré ; conversion d'un
projet CT **fictif** avec sauvegarde réversible ; FT 4–20 mA seul, impulsions seul, combiné ; défaut et sens
activés/désactivés ; mapping `ET_SENS` conservé après enregistrement et réouverture ; `TS_DEF` ≠ `TS_DEF_EXT` ;
`CP_VOL` unique ; `ET_MV01_OUV`, `TS_MV01_OUV` et collisions contrôlées ; exporteurs XSY / S4W / TOPKAPI toujours
conformes à leurs jeux de référence.

## 7. Fin de session et passage de relais à Codex

Avant de t'arrêter (crédits presque épuisés, ou plus rien d'utile faisable) : aucun travail non commité, CI
verte ou échec expliqué, puis ajoute en tête de `docs/INSTRUCTIONS_EN_COURS.md` une entrée
`[nouveau] Passation à Codex — <date heure>` : branche et dernier commit, lots faits (avec tests), lot en cours et
**étape exacte** de reprise, décisions à valider, pièges rencontrés. Codex reprend sur la même branche
`claude/referentiel-v2`, avec les mêmes règles ; si Claude revient ensuite, il lit cette entrée et reprend de
même. Les deux agents travaillent en binôme : petits commits, jamais de réécriture de l'historique de l'autre.
