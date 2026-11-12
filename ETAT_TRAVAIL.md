# OGIAS 1.0 — Conformité et point de reprise

Mis à jour le 12 novembre 2026. Dépôt public **Mcodea/testt**, branche active `claude/referentiel-v2`.
Référence unique : [CAHIER_DES_CHARGES_V1.md](docs/CAHIER_DES_CHARGES_V1.md),
lu en entier. Les deux classeurs (tous les onglets/cellules), les trois maquettes
et `validation/README.md` ont été lus. Les six fichiers ont été importés à l’identique
au commit `fb329f0` ; la branche distante apporte ensuite le classeur anonymisé
et la correction descriptive du nombre de codes (commit `aa68c3b`). La consigne active demande la reprise V2 de l’interface et de l’adoption.
A1 et D5-b restent en décision ; R1 validé le 11/11 ; la qualification industrielle attend les preuves utilisateur.
Historique V0.31 conservé : [docs/ETAT_TRAVAIL_V031.md](docs/ETAT_TRAVAIL_V031.md).

## Règle de suivi

Chaque ligne reprend une puce ou un critère numéroté du cahier, avec sa section
et sa ligne source. Les sous-exigences d’une même puce sont conservées dans son
texte et doivent toutes être prouvées avant « fait ». Un test hérité qui ne
couvre qu’une partie de l’exigence laisse la ligne « partiel ». Une capture de
l’application sans comparaison à la maquette ne prouve pas la conformité UI.
Les critères de sortie demeurent bloquants hors preuves utilisateur de section 8.

## Point CI en cours — lot Formulaires

Run 43317537003 : Windows/Linux, qualité et portable verts ; navigateur échoué.
Cause encore inconnue (65 tests locaux passent). Diagnostic d’échec ajouté
dans tests_web/conftest.py, annotations publiques sans changement des assertions
ni des résultats. Reprise exacte : lire l’annotation du prochain run, corriger
le défaut démontré et obtenir une CI verte. Codex reste actif sur ce point.

## Checkpoint actif — contraste des formulaires, 12/11/2026

- Reprise utilisateur « continuer », base publique c43f713, CI précédente verte
  run 43286205755. Aucun commit nouveau de Claude à reprendre.
- Périmètre strict conservé : présentation uniquement. Une feuille produit
  modifiée, **industrial-ui.css : 20 lignes** ; aucun JavaScript, moteur,
  état, API, structure, événement, donnée ni export changé.
- Anomalies reproduites : labels/titre de création trop sombres, boutons/badge
  conservant leur ancienne palette, double bordure du formulaire, contraste
  de l’onglet actif des listes et repère de sélection des niveaux d’adressage
  supprimé avec les ombres. Correction par les couleurs du thème et un contour
  de sélection ; aucun comportement ni règle de validation remanié.
- **Cinq nouveaux tests et 18 sous-cas** : contraste WCAG au moins 4,5:1 sur
  les éléments ciblés, Neuf/Existant, clair/sombre, trois résolutions ; parcours
  des quatre listes, trois niveaux, focus/actions accessibles ; données API
  et listes inchangées, projet de test identique à l’octet.
- **730 Python / 18 sous-cas**, 0 ignoré, 194,22 s ; **65 navigateur / 70
  sous-cas**, 0 ignoré, 110,68 s. Couverture moteur **89,283831 %**, exports
  **100 %**. Statique et dépendances conformes. Sept seuils du banc inchangés
  passent : rendu **75,9 ms**, filtre **97,4 ms**, adressage **0,719 s**.
- **16 captures avant/après non retouchées** et preuves :
  validation/interface_v1/formulaires_12_11/. Aucune maquette de création
  n’étant fournie, comparaison à l’écran antérieur et à la palette du chat ;
  les maquettes originales ne sont pas modifiées. Pas de certification WCAG
  globale ; la ligne V1-4-45 reste partielle.
- Dernier commit fonctionnel **efe3b1f**, passation à Claude, agent libre.
  Étape exacte de reprise dans docs/INSTRUCTIONS_EN_COURS.md.
- Audit données **0/0** ; statut CI du lot : verification.json / Actions publiques.
  A1, D5-b et qualification réelle restent dans leur état ; aucune release.

## Checkpoint historique — report UI terminé sur le dépôt public Mcodea/testt

- Le nom testt désigne le **nouveau dépôt public**, pas une branche de l’ancien.
  Base publique conservée : **085b1c7**, racine **4d084b4**. Aucun historique privé
  importé. Branche commune : **claude/referentiel-v2** ; aucune fusion d’agent.
- Première CI publique vérifiée : run **43276436661 vert**. L’ancienne limite
  de crédit concernait le dépôt privé. Workflow public complet conservé : Linux,
  Windows, couverture, navigateur, performance, qualité et portable. Suivi :
  https://github.com/Mcodea/testt/actions?query=branch%3Aclaude%2Freferentiel-v2.
- Lot U9 reporté **7466f35** : bonne destination des points bloquants, lignes
  Variables 44 px et cases 24 px, état vide/redimensionnement, fermeture Échap
  respectant les fenêtres au premier plan et retour du focus. Tests ciblés :
  25 tests et 29 sous-cas, avec la nouvelle composition matérielle de Claude.
- Passation à Claude : dernier commit fonctionnel **01287a2**, agent libre.
  Reprise exacte dans docs/INSTRUCTIONS_EN_COURS.md.
- Lot visuel : couche industrial-ui.css, lien index.html, gabarit latéral et
  deux classes S4W d’app.js. Fonctions, événements, identifiants, état, API,
  structures et export inchangés dans ce lot. Les catalogues, nomenclature et
  correctifs d’exports de Claude sont préservés, ainsi que ses tests unitaires.
- La consigne visuelle du chat du 12/11 remplace palette/formes lavande des
  anciennes maquettes. Préférence de thème conservée ; bouton lune pour la
  palette sombre, variante claire technique. Aucune donnée injectée au produit.
- Preuves du **dépôt public** : validation/interface_v1/industriel_12_11/
  (captures régénérées, comparaison, mesures, vérifications et performance).
  Les fichiers restent identiques à l’octet après les interactions visuelles.
- **730 tests Python**, 18 sous-cas, 0 ignoré, 201,87 s ; couverture moteur
  **89,283831 %**, exports **100 %**. **60 tests navigateur**, 52 sous-cas, 0 ignoré, 97,98 s ;
  statique conforme (mypy 49 fichiers, ruff, JS), audit dépendances conforme.
  Audit données 0/0 ; sept seuils de performance inchangés passent
  (rendu 84 ms, filtre 100,2 ms, adressage 0,621 s). Détails dans verification.json. La qualification sur les logiciels réels
  reste en attente ; aucune livraison 1.0 ni compatibilité industrielle déduite.

### Conformité — consigne visuelle du 12/11

| Exigence | État | Preuve |
| --- | --- | --- |
| Palette sombre exacte et bordures nettes, sans ombres/dégradés décoratifs | fait | industrial-ui.css ; test_palette_typographie_et_theme_sans_ecriture ; comparaison.html. |
| Polices locales et chasse fixe tabulaire sur les éléments techniques | fait | tests ressources embarquées conservés ; tests design palette/voies/composition. |
| Couleurs de plateforme sur les cibles existantes | fait | test_raccourcis_existants_et_exports_identifies ; test_cibles_sofrel_et_topkapi_sans_inventer_de_donnees. |
| Espace de travail, navigation et actions compactes | fait | test_workspace_et_captures_trois_resolutions ; sept écrans, trois tailles. |
| Densité et en-têtes fixes | fait | tests Variables densité/colonnes ; test_entete_reste_visible_au_defilement_sans_modifier_les_variables. |
| Grilles de rack et composition, voies occupées/libres | fait | test_composition_et_rack_existant_en_sombre_sans_ecriture ; test_voies_occupees_et_libres_gardent_leurs_actions ; captures non retouchées. |
| Dépassement matériel | partiel | Bordure rouge liée à l’état existant de jauge ; aucun conflit fabriqué pour produire une capture ; pas de qualification revendiquée. |
| Anti-régression de l’état et des données | fait | Sept tests design, fichiers et valeurs API inchangés après interaction ; aucun POST lors du thème/détail ; validation/adoption existantes conservées. |

## Checkpoint — session planifiée Claude du 11/11/2026 (20 h 20 UTC)

- CI rouge des runs 71 à 74 (`5c67e82`, `a3c4f54`) : **panne DNS des miroirs Ubuntu** sur les exécuteurs GitHub
  (`Temporary failure resolving 'azure.archive.ubuntu.com'` aux étapes `apt-get` et `playwright install
  --with-deps`) ; aucun test en échec, rien à corriger dans le code ; relancé par le push suivant.
- **V1-7-03 copies horodatées** (moteur et API) : `genvar/copies.py` ; la copie contient l'état **en mémoire**
  juste avant l'opération (référentiel figé compris), écrite atomiquement à côté du fichier
  (`<fichier>.avant-<opération>-<horodatage>-<aléa>`), 10 conservées par opération, copies d'adoption et anciennes
  `.avant_adressage_*` jamais effacées. L'ancienne copie de fichier de `adressage.py` (5 conservées, écrasée dans la
  même seconde) est remplacée. Choix prudents : ouvrage jamais enregistré → pas de copie (rien sur disque) ;
  la restauration charge en mémoire, l'interface enregistre (ancien fichier en `.bak`). Tests :
  `tests/test_copies_horodatees.py` (17). Reste « partiel » : écran Codex.
- R1 consigné validé (commit `a3c4f54`) mais **non appliqué** : la consigne planifiée de cette session l'interdit.

## Checkpoint — session autonome Claude du 11/11/2026 (12 h 17 UTC)

- CI du HEAD repris (`39c4e4c`) verte ; aucun commit de Codex depuis la passation du matin, rien à corriger.
- **P1 variables internes déclarées** (BI, EI, MI, RI), moteur : fait avec `tests/test_variables_internes_p1.py`
  (18 tests : non sélectionnée → absente partout ; sélection par option, retrait individuel, signal propre ;
  enregistrement et réouverture ; aucune adresse ni %MW ; absente de TOPKAPI et de la table d'échange Excel ;
  XSY sans `topologicalAddress`, adresses d'échange inchangées ; règles de déclaration ; règle auto refusée ;
  nom trop long ; homonymes ; aller-retour Excel du référentiel sans perte). Puis, sur décision de l'utilisateur,
  candidats BI de MV livrés (option « Variables internes », `DIS` = disponible, `DSC` = discordance).
- P5 tranché par l'utilisateur : sortie d'arrêt de MV `ST_<repère>_ARR` (clé `ES_ARR`), `TC_AR` inchangé ;
  `validation/referentiel/correspondance_es_v1.csv` régénéré (index décalés par les ajouts de MV).
- Vérifié : 608 tests Python (30 ignorés ici faute de PyMuPDF/PySide6, présents en CI), 36 tests navigateur +
  34 sous-cas, ruff, mypy 46 fichiers, `node --check`, audit données 0 détection, banc dans les seuils.
- **Rapprochement hybride, cahier § 6** : seuil de confiance réglé et prouvé (V1-6-03 fait), mesures publiées
  (V1-6-04 fait, `validation/hybride/SEUIL_CONFIANCE.md`), confiance et raison par proposition, confirmation en
  lot tracée et annulable (V1-6-02 / V1-6-05 : moteur fait, interface Codex). Tests :
  `tests/test_seuil_confiance_rapprochement.py`.

## Checkpoint — session autonome Claude du 11/11/2026 (08 h 19 → 08 h 57 UTC)

- CI Windows intermittente réparée (course de navigation réelle dans `app.js`, test qui la reproduit).
- Lots moteur faits, chacun avec ses tests : P5, P8/R9, R2+R3, R4, R5, R7, R6, reprise contrôlée d'un modèle
  figé, P3. Détail, commits et reprise exacte : passation en tête de `docs/INSTRUCTIONS_EN_COURS.md`.
- Relecture critique faite à chaque lot (doctrine § 3 : aucune logique imposée, aucun %MW pour une E/S
  physique, aucune adresse recalculée, rien d'appliqué sans aperçu et confirmation, fichiers d'ouvrage
  inchangés à l'octet par les aperçus et rapports). A1, R1, D5-b non appliqués.
- 590 tests Python, 36 tests navigateur + 34 sous-cas, mypy, audit données, banc dans les seuils.
- Exigences du cahier touchées : V1-3-22 / V1-3-23 (projets existants et adoption : surcharges conservées,
  modèle figé protégé) et V1-7-03 (copie horodatée avant reprise de modèle) restent « partiel » : l'interface
  correspondante (Codex) et la qualification industrielle manquent encore.
- Prochaine étape moteur : P1 (voir passation). Interface : Codex.

## Checkpoint actif — V2, L7 / interface

- Consigne active : dernière instruction du chat et
  `docs/referentiel/PROMPT_CLAUDE_AUTONOME_OGIAS_V2.md`, lus en entier avec les
  documents demandés et les cinq onglets de décision du classeur (140 entrées du journal).
- **Pousser uniquement sur `claude/referentiel-v2`. Ne fusionner ni la PR #1 ni `release/1.0`.**
  Base récupérée `7e5ebf0`, complétée par `38efa5d` (report du lot UI antérieur et règle du binôme). Les travaux V2 L1–L6 de Claude sont conservés.
- **A1 non approuvé** : aucun des 49 ajouts ni des renommages V1 n'est intégré.
  Les fichiers `genvar/data/` ne changent pas dans ce lot. CT reste absent du
  catalogue livré ; les références historiques CT des correspondances sont conservées.
  `suffixe_es` reste limité aux cinq signaux déjà validés, PM CONS_FREQ reste FREQ.
- **R1** (conversion des projets CT avec repère conservé), **D5-b** (dix règles
  historiques auto classées suggestions) et A2/A7/A8/A10/A11 restent en décision.
  Aucune conversion CT ni modification de ces modes n'est engagée.
- Lot réalisé : écrans Lexique, Dictionnaire et Correspondances sur le dépôt commun,
  consultation / recherche / clavier / saisie / suppression en brouillon ; bouton
  réversible Archiver le type ; état archivé conservé dans Excel et dans les anciens
  classeurs sans cette colonne. Un modèle explicitement sans E/S reste vide au réimport.
- Lot adoption réalisé : aperçu par équipement, confirmations individuelles décochées,
  sauvegarde téléchargeable, annulation du fichier à l’octet avec copie de l’état courant.
  Un autre ouvrage ou un Enregistrer sous ne récupère pas le retour arrière précédent.
  Un aperçu périmé et une confirmation incomplète sont refusés par le serveur.
- Preuves locales : **557 tests Python réussis**, 0 ignoré, 131,23 s ; **88,575957 %**
  sur le moteur et **100 %** sur les trois modules industriels. Ruff et mypy (44 fichiers),
  syntaxe JS et audit données passent (0 détection / 0 erreur de lecture).
  Journaux : `/workspace/ogias-cloud/v2/dashboard-python-final/`.
- L7 réalisé : Inter et JetBrains Mono embarquées, géométries Lucide locales,
  licences consultables depuis À propos ; alignement des en-têtes/cellules corrigé
  lorsque le panneau Variables est ouvert. Captures des trois écrans comparées
  aux maquettes dans `validation/interface_v2/maquettes/COMPARAISON.html`.
- Tableau de bord corrigé : répartition E/S depuis `point`, cinq étapes accessibles,
  états vides explicites pour les zéros connus (aucun compteur nul), indisponibilité
  distinguée, aucun faux taux ni faux bilan sans anomalie.
- **Étape suivante pour Claude : L7** — liens des constats vers leur correction,
  dimensions/densité et historique du panneau Variables, activité récente à partir
  de faits enregistrés. Aucun taux ni événement inventé. Ne pas appliquer A1. Les signaux d’un modèle figé ne sont pas adoptés par le catalogue ;
  une migration de clé de ce modèle est bloquée dans le parcours web et reste à traiter
  dans un lot moteur dédié. Voir `docs/ADOPTION_REFERENTIEL.md`.
- API GitHub inaccessible depuis cet environnement : `gh api ...actions/runs` retourne
  Forbidden. Ne pas présenter une exécution locale comme la preuve du run distant.
- Section 8 : CE 14.1 / TOPKAPI 6.3 / S4W-Tools toujours en attente de preuves utilisateur.

## Conformité

| ID | Exigence du cahier | État | Preuve (fichier et test) |
| --- | --- | --- | --- |
| V1-1-01 (L9) | équipements ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-1-02 (L10) | entrées et sorties physiques ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-1-03 (L11) | matériel (cartes Schneider M340 / M580, postes SOFREL S4W) ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-1-04 (L12) | variables et table d'échange ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-1-05 (L13) | télétransmission TOPKAPI 6.3 ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-1-06 (L14) | recette. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-1-07 (L17) | Projets neufs et existants, imports Control Expert / TOPKAPI / Excel | partiel | tests/test_interface_web.py, tests/inbound ; périmètre V1 à compléter et formats section 8 en attente. |
| V1-1-08 (L19) | Logiciel professionnel vendable, stable, fiable, rapide, documenté, installable sans assistance | partiel | Existant opérationnel ; critères V1 ci-dessous pas encore tous satisfaits. |
| V1-2-01 (L25) | Classeur de 740 lignes, 25 modèles, ID ligne et lexique | fait | tests/test_references_v1.py::test_classeurs_sources_complets et test_reference_fournie_preservee ; intégration au référentiel traitée au §3. |
| V1-2-02 (L26) | Classeur de 193 E/S, dictionnaire, variantes et correspondances | fait | tests/test_references_v1.py : 193 E/S, 49 ajoutées, 81 entrées / 80 codes, conforme au cahier corrigé ; aucun code inventé. |
| V1-2-03 (L27) | Trois maquettes de référence | fait | tests/test_references_v1.py::test_maquettes_format_et_dimensions et test_reference_fournie_preservee ; 1920×1080, octets conservés. |
| V1-2-04 (L28) | Jeux fictifs et provenance | fait | validation/README.md, SOURCE_ARCHIVE.json ; 24 tests DDT/hybride réussis, empreintes de la restauration contrôlées. |
| V1-2-05 (L29) | Exports et preuves de qualification | en attente de preuves utilisateur | validation/controlexpert/ENVIRONNEMENT.md ; aucun fichier CE 14.1 réel reçu. |
| V1-3-01 (L34) | Le référentiel livré contient exactement les 732 lignes conservées, avec le suffixe et le libellé du classeur, rapprochées par « ID ligne ». Les 8 lignes « Retiré » sont absentes. | fait | tests/test_referentiel_v1_modeles.py (ensemble exact, libellés/suffixes, 8 absentes). Publication en révision : voir Migration §3. |
| V1-3-02 (L35) | `_suffixe_propose` ne tronque jamais. Il utilise d'abord le code du catalogue ou du dictionnaire des E/S, puis le lexique. Un suffixe de plus de 12 caractères déclenche une alerte « suffixe à raccourcir ». | fait | tests/test_lexique_v1.py::TestProposition (aucune troncature, code du catalogue prioritaire, alerte > 12, import annoté). |
| V1-3-03 (L36) | Le lexique est un objet du référentiel : exporté, importé, versionné, modifiable dans le brouillon. | fait | genvar/lexique.py, référentiel dépôt/Excel et écran commun ; tests/test_lexique_v1.py et tests_web/test_referentiel_codes.py : consultation, édition en brouillon et conservation de la révision publiée. |
| V1-3-04 (L37) | Les noms sont en majuscules, de la forme `<Rôle>_<Repère>_<Suffixe>` (exemple : `TS_SR02AT01_HS`). | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-3-05 (L41) | Le référentiel livré contient exactement les 193 E/S, rapprochées par « Identifiant », dont les 49 lignes « Ajouté » : | partiel | A1 non approuvé : renommages V1 / 49 ajouts non appliqués, conformément à la consigne V2 ; docs/referentiel/PROMPT_CLAUDE_AUTONOME_OGIAS_V2.md et docs/INSTRUCTIONS_EN_COURS.md. |
| V1-3-06 (L42) | nouveaux types CG, UV, FI, AB, CE et DG ; | partiel | A1 non approuvé : renommages V1 / 49 ajouts non appliqués, conformément à la consigne V2 ; docs/referentiel/PROMPT_CLAUDE_AUTONOME_OGIAS_V2.md et docs/INSTRUCTIONS_EN_COURS.md. |
| V1-3-07 (L43) | E/S des types FV, VV et OU ; | partiel | A1 non approuvé : renommages V1 / 49 ajouts non appliqués, conformément à la consigne V2 ; docs/referentiel/PROMPT_CLAUDE_AUTONOME_OGIAS_V2.md et docs/INSTRUCTIONS_EN_COURS.md. |
| V1-3-08 (L44) | variantes manquantes des types existants. | partiel | A1 non approuvé : renommages V1 / 49 ajouts non appliqués, conformément à la consigne V2 ; docs/referentiel/PROMPT_CLAUDE_AUTONOME_OGIAS_V2.md et docs/INSTRUCTIONS_EN_COURS.md. |
| V1-3-09 (L45) | Les codes « Harmonisé » remplacent l'ancien code, et toutes les règles qui le citaient sont mises à jour. Aucune référence ne reste cassée. | partiel | A1 non approuvé : renommages V1 / 49 ajouts non appliqués, conformément à la consigne V2 ; docs/referentiel/PROMPT_CLAUDE_AUTONOME_OGIAS_V2.md et docs/INSTRUCTIONS_EN_COURS.md. |
| V1-3-10 (L46) | La télétransmission suit la colonne « Télétransmission ». Chaque variante de l'onglet « Variantes » génère exactement ses E/S. | partiel | A1 non approuvé : renommages V1 / 49 ajouts non appliqués, conformément à la consigne V2 ; docs/referentiel/PROMPT_CLAUDE_AUTONOME_OGIAS_V2.md et docs/INSTRUCTIONS_EN_COURS.md. |
| V1-3-11 (L47) | Le dictionnaire des codes est un objet du référentiel. Contrôles : | fait | genvar/dictionnaire_es.py ; dictionnaire (81 entrées) dans referentiel_modeles.json, brouillon, Excel « Dictionnaire E-S » ; tests/test_dictionnaire_es_v1.py. |
| V1-3-12 (L48) | code de 2 à 9 caractères (A–Z, 0–9, « _ ») ; | fait | tests/test_dictionnaire_es_v1.py::TestControles::test_format_du_code. |
| V1-3-13 (L49) | un code non standard déclenche une alerte ; | fait | codes_non_standard : 42 alertes sur le catalogue actuel (harmonisation E/S en attente de validation) ; test_code_non_standard. |
| V1-3-14 (L50) | deux codes pour un même libellé déclenchent une alerte ; | fait | test_repetition_identique_et_deux_codes_un_libelle_alertent. |
| V1-3-15 (L51) | un même code avec deux sens est une erreur. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-3-16 (L52) | Les correspondances Schneider / SOFREL S4W alimentent l'écran Matériel : | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-3-17 (L53) | une sortie analogique sur S4W impose un module AO ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-3-18 (L54) | une sortie TOR au-delà de 150 mA impose un relais d'interface ou un module 4DO+. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-3-19 (L55) | BMX EHC, BMX ART et l'identification des voies S4W-Tools restent « à confirmer ». Aucune adresse S4W n'est inventée. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-3-20 (L56) | Le modèle « Vanne de régulation » est rattaché à FV, et « Détection de gaz » à DG. | partiel | A1 non approuvé : renommages V1 / 49 ajouts non appliqués, conformément à la consigne V2 ; docs/referentiel/PROMPT_CLAUDE_AUTONOME_OGIAS_V2.md et docs/INSTRUCTIONS_EN_COURS.md. |
| V1-3-21 (L60) | Installation vierge : ce référentiel est publié comme révision 1. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-3-22 (L61) | Installation existante : il est publié comme nouvelle révision, historique conservé. Les ouvrages existants gardent leur révision figée tant qu'ils ne l'adoptent pas. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-3-23 (L62) | Un projet existant importé garde ses noms et adresses d'origine. | partiel | tests/test_adoption_controlee.py et tests_web/test_adoption.py : refus, annulation et sauvegarde identiques, adresses conservées ; couverture des imports V1 et qualification industrielle encore partielles. |
| V1-4-01 (L70) | fond lavande doux ; | partiel | Valeur visuelle remplacée par la consigne utilisateur du 12/11 ; industrial-ui.css, tests_web/test_design_industriel.py et validation/interface_v1/industriel_12_11/comparaison.html. Ancienne référence conservée. |
| V1-4-02 (L71) | grandes cartes blanches arrondies, sans bordure grise ; | partiel | Valeur visuelle remplacée par la consigne utilisateur du 12/11 ; industrial-ui.css, tests_web/test_design_industriel.py et validation/interface_v1/industriel_12_11/comparaison.html. Ancienne référence conservée. |
| V1-4-03 (L72) | barre latérale indigo à icônes ; | partiel | Valeur visuelle remplacée par la consigne utilisateur du 12/11 ; industrial-ui.css, tests_web/test_design_industriel.py et validation/interface_v1/industriel_12_11/comparaison.html. Ancienne référence conservée. |
| V1-4-04 (L73) | indigo principal, corail en contraste ; | partiel | Valeur visuelle remplacée par la consigne utilisateur du 12/11 ; industrial-ui.css, tests_web/test_design_industriel.py et validation/interface_v1/industriel_12_11/comparaison.html. Ancienne référence conservée. |
| V1-4-05 (L74) | grands chiffres, beaucoup d'espace. | partiel | Valeur visuelle remplacée par la consigne utilisateur du 12/11 ; industrial-ui.css, tests_web/test_design_industriel.py et validation/interface_v1/industriel_12_11/comparaison.html. Ancienne référence conservée. |
| V1-4-06 (L80) | **Couleurs :** | partiel | Valeur visuelle remplacée par la consigne utilisateur du 12/11 ; industrial-ui.css, tests_web/test_design_industriel.py et validation/interface_v1/industriel_12_11/comparaison.html. Ancienne référence conservée. |
| V1-4-07 (L81) | fond `#EEF1FB`, cartes `#FFFFFF`, survol `#F5F7FE`, ligne sélectionnée `#EEF0FD` ; | partiel | Valeur visuelle remplacée par la consigne utilisateur du 12/11 ; industrial-ui.css, tests_web/test_design_industriel.py et validation/interface_v1/industriel_12_11/comparaison.html. Ancienne référence conservée. |
| V1-4-08 (L82) | barre latérale en dégradé `#4F5BD5` → `#3D47B8` ; | partiel | Valeur visuelle remplacée par la consigne utilisateur du 12/11 ; industrial-ui.css, tests_web/test_design_industriel.py et validation/interface_v1/industriel_12_11/comparaison.html. Ancienne référence conservée. |
| V1-4-09 (L83) | principal `#5B63E6` (teinte claire `#E4E6FB`) ; | partiel | Valeur visuelle remplacée par la consigne utilisateur du 12/11 ; industrial-ui.css, tests_web/test_design_industriel.py et validation/interface_v1/industriel_12_11/comparaison.html. Ancienne référence conservée. |
| V1-4-10 (L84) | corail `#F28C5B`, au plus un élément par écran ; | partiel | Valeur visuelle remplacée par la consigne utilisateur du 12/11 ; industrial-ui.css, tests_web/test_design_industriel.py et validation/interface_v1/industriel_12_11/comparaison.html. Ancienne référence conservée. |
| V1-4-11 (L85) | texte `#1E2340`, texte secondaire `#7A80A0`, séparateurs `#EDEFF7` ; | partiel | Valeur visuelle remplacée par la consigne utilisateur du 12/11 ; industrial-ui.css, tests_web/test_design_industriel.py et validation/interface_v1/industriel_12_11/comparaison.html. Ancienne référence conservée. |
| V1-4-12 (L86) | états : validé `#2BA36B` / `#E3F5EC`, à valider `#E39B2D` / `#FCF1DE`, erreur et conflit `#E0524A` / `#FCE6E4`. | partiel | Valeur visuelle remplacée par la consigne utilisateur du 12/11 ; industrial-ui.css, tests_web/test_design_industriel.py et validation/interface_v1/industriel_12_11/comparaison.html. Ancienne référence conservée. |
| V1-4-13 (L87) | **Formes :** | partiel | Valeur visuelle remplacée par la consigne utilisateur du 12/11 ; industrial-ui.css, tests_web/test_design_industriel.py et validation/interface_v1/industriel_12_11/comparaison.html. Ancienne référence conservée. |
| V1-4-14 (L88) | cartes : rayon de 20 px, ombre `0 10px 30px rgba(61,71,184,.08)`, marge intérieure de 24 px ; | partiel | Valeur visuelle remplacée par la consigne utilisateur du 12/11 ; industrial-ui.css, tests_web/test_design_industriel.py et validation/interface_v1/industriel_12_11/comparaison.html. Ancienne référence conservée. |
| V1-4-15 (L89) | boutons et champs : rayon de 12 px, 40 px de haut ; | partiel | Valeur visuelle remplacée par la consigne utilisateur du 12/11 ; industrial-ui.css, tests_web/test_design_industriel.py et validation/interface_v1/industriel_12_11/comparaison.html. Ancienne référence conservée. |
| V1-4-16 (L90) | pastilles et filtres en gélule ; | partiel | Valeur visuelle remplacée par la consigne utilisateur du 12/11 ; industrial-ui.css, tests_web/test_design_industriel.py et validation/interface_v1/industriel_12_11/comparaison.html. Ancienne référence conservée. |
| V1-4-17 (L91) | panneaux et fenêtres : rayon de 24 px. | partiel | Valeur visuelle remplacée par la consigne utilisateur du 12/11 ; industrial-ui.css, tests_web/test_design_industriel.py et validation/interface_v1/industriel_12_11/comparaison.html. Ancienne référence conservée. |
| V1-4-18 (L92) | Jamais de carte dans une carte. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-4-19 (L93) | **Typographie :** | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-4-20 (L94) | Inter et JetBrains Mono, embarquées ; | fait | Polices WOFF2 locales et licences OFL, tests_web/test_ressources_embarquees.py ; chargement réel avec accès extérieur refusé, chasse fixe mesurée. Captures comparées : validation/interface_v2/maquettes/README.md. |
| V1-4-21 (L95) | échelle 12 / 13 / 14 / 16 / 20 / 32 px ; | partiel | Valeur visuelle remplacée par la consigne utilisateur du 12/11 ; industrial-ui.css, tests_web/test_design_industriel.py et validation/interface_v1/industriel_12_11/comparaison.html. Ancienne référence conservée. |
| V1-4-22 (L96) | noms de variables, repères et adresses en police à chasse fixe. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-4-23 (L97) | **Icônes :** Lucide (licence ISC), embarquées. Jamais d'emoji. | partiel | 19 géométries Lucide ISC embarquées pour V31.icon, rendu SVG, empreintes et licence testés dans tests_web/test_ressources_embarquees.py ; autres surfaces historiques et glyphes à vérifier. Comparaison : validation/interface_v2/maquettes/. |
| V1-4-24 (L98) | **Transitions :** 180 ms, sans animation décorative. | partiel | Valeur visuelle remplacée par la consigne utilisateur du 12/11 ; industrial-ui.css, tests_web/test_design_industriel.py et validation/interface_v1/industriel_12_11/comparaison.html. Ancienne référence conservée. |
| V1-4-25 (L102) | Barre latérale de 80 px : Accueil, Ouvrages, Référentiel, Paramètres, À propos. | partiel | Valeur visuelle remplacée par la consigne utilisateur du 12/11 ; industrial-ui.css, tests_web/test_design_industriel.py et validation/interface_v1/industriel_12_11/comparaison.html. Ancienne référence conservée. |
| V1-4-26 (L103) | Aucun menu horizontal, ruban ou onglet de documents. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-4-27 (L104) | Dans un ouvrage, les 5 étapes en gélules forment la seule navigation : Équipements → Liste des E/S → Matériel → Variables → Recette. Chaque étape affiche son état et le nombre de points à traiter. | partiel | tests_web/test_tableau_de_bord.py::test_cinq_etapes_accessibles_sans_ecriture : cinq liens, titres et états, fichier identique après navigation ; compte des points par étape encore à compléter. |
| V1-4-28 (L105) | Le tableau de bord de l'ouvrage est la page d'arrivée : | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-4-29 (L106) | indicateurs ; | fait | tests_web/test_tableau_de_bord.py : indicateurs, vrais états vides, source indisponible et bilan de recette cohérents ; captures 1920×1080 comparées dans validation/interface_v2/maquettes/README.md. |
| V1-4-30 (L107) | avancement de la recette ; | partiel | Taux non affiché si total absent ou incohérent, tests test_zero_connu_signale_sans_compteur_nul_ni_taux_de_recette_fabrique et test_taux_incoherent_non_affiche ; le moteur ne fournit pas encore le total des contrôles. |
| V1-4-31 (L108) | répartition des E/S ; | fait | tests_web/test_tableau_de_bord.py : comparaison aux points réels du moteur et contrat visuel des quatre natures ; captures comparées dans validation/interface_v2/maquettes/README.md. Aucune qualification matérielle déduite. |
| V1-4-32 (L109) | points à traiter, avec un lien vers chacun ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-4-33 (L110) | activité récente. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-4-34 (L111) | Les écrans de travail sont faits d'une grande carte qui contient la table. Le panneau de détail glisse depuis la droite à la sélection d'une ligne et se ferme avec Échap. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-4-35 (L112) | Rien d'inutile : | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-4-36 (L113) | aucun compteur à zéro ; | partiel | Tableau de bord : états vides explicites, aucun nombre nul dans les cartes ou la répartition, tests test_ouvrage_sans_equipement_signale_ses_etats_vides_sans_compteur_nul et test_zero_connu_signale_sans_compteur_nul_ni_taux_de_recette_fabrique ; autres écrans à auditer. |
| V1-4-37 (L114) | aucun texte d'aide permanent (infobulle « i » ou état vide) ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-4-38 (L115) | au plus 3 actions visibles. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-4-39 (L119) | Une seule table. Colonnes : variable, famille, source, adresse automate, adresse de télétransmission, statut, règle. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-4-40 (L120) | « Table d'échange » et « Télétransmission » sont des préréglages de cette table, pas des écrans séparés. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-4-41 (L121) | Le bouton principal « Valider les propositions · n » est dans la table. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-4-42 (L122) | Le panneau de détail propose : Valider, Saisir (avec contrôle immédiat), Déverrouiller (avec motif), Réserver. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-4-43 (L123) | Un blocage (référentiel non publié, propositions non décidées, conflit) laisse le bouton visible mais désactivé, avec la raison et un lien vers la correction. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-4-44 (L124) | Projet existant : les adresses importées sont validées et protégées. Aucune n'est recalculée. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-4-45 (L128) | Accessibilité WCAG AA et navigation complète au clavier. | partiel | Contraste des labels/titres, onglets et cartes de niveau prouvé sur les formulaires ciblés (test_formulaires_industriels.py, 4,5:1 minimum) ; clavier/focus Variables conservés. Captures formulaires_12_11/. Audit WCAG complet encore partiel. |
| V1-4-46 (L129) | Affichage correct de 1366×768 à 2560×1440. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-4-47 (L130) | Annulation (Ctrl+Z) des modifications de l'ouvrage. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-4-48 (L131) | Chaque action a un retour visible : chargement, succès, erreur avec la cause et la solution. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-5-01 (L135) | Dupliquer un équipement : aucune adresse recopiée, nouveau numéro proposé. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-5-02 (L136) | Dupliquer, réordonner et déplacer des lignes de variables, avec un ordre stable dans les exports. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-5-03 (L137) | Sens de chaque variable (lecture, commande, consigne, retour, réserve), affiché et filtrable. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-5-04 (L138) | Profils d'import Excel enregistrés et réutilisables, avec aperçu avant import. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-5-05 (L139) | Création en série d'équipements d'un même type. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-5-06 (L140) | Recherche globale (repère, variable, adresse, libellé). | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-6-01 (L144) | La précision passe avant le rappel. Aucune correspondance n'est appliquée sans confirmation humaine. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-6-02 (L145) | Chaque proposition affiche son niveau de confiance et sa raison. Sous le seuil, la ligne est marquée « à rapprocher manuellement ». | partiel | Moteur : `Proposition.confiance` (« élevée » au-dessus de `SEUIL_CONFIANCE` et non ambiguë, sinon « à rapprocher manuellement ») et `Proposition.raison`, tests/test_seuil_confiance_rapprochement.py::TestSeuil::test_confiance_et_raison ; affichage dans l'écran de rapprochement : Codex. |
| V1-6-03 (L146) | Le seuil est réglé pour qu'aucune proposition fausse connue ne passe au-dessus, sur tous les jeux de validation. | fait | `SEUIL_CONFIANCE = 80` : aucune proposition fausse connue (2 jeux, 3 méthodes, tous candidats, signaux absents) ne l'atteint, plus haut faux = 79 ; tests/test_seuil_confiance_rapprochement.py::TestSeuil::test_aucune_proposition_fausse_connue_au_dessus_du_seuil et test_le_seuil_n_est_pas_trivial. |
| V1-6-04 (L147) | Précision et rappel sont mesurés et publiés dans le compte rendu. | fait | Précision et rappel au seuil, par jeu et par méthode, publiés dans validation/hybride/SEUIL_CONFIANCE.md (généré par `rapport_seuil`, identique au calcul : test_compte_rendu_publie_identique_au_calcul) ; hybride : 5/36 au seuil, précision 100 %, rappel 13,9 %. À reprendre dans COMPTE_RENDU_V1.0. |
| V1-6-05 (L148) | Les confirmations (une par une, ou en lot pour les confiances élevées) sont tracées et annulables. | partiel | Moteur : confirmation une par une tracée (`valider_fonction`), en lot limitée à la confiance élevée (`confirmer_en_lot`), annulable à l'identique (`annuler_lot`), journal `journal_rapprochement` enregistré ; tests/test_seuil_confiance_rapprochement.py::TestConfirmationEnLot et TestJournalPersistant ; boutons et routes : Codex. |
| V1-7-01 (L152) | **Données :** | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-7-02 (L153) | écriture atomique et sauvegarde automatique ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-7-03 (L154) | copies horodatées avant chaque opération lourde, restaurables depuis l'interface ; | partiel | Moteur et API faits : `genvar/copies.py`, `Session.copies_horodatees` / `restaurer_copie`, `GET /api/ouvrage/copies`, `POST /api/ouvrage/restaurer-copie` ; copie de l'état d'avant (non enregistré compris) pour adressage, plan historique, implantation, matériel, inventaire, confirmation en lot, import, adoption ; refus ou sans effet → aucune copie ; copie impossible → opération annulée ; restauration réversible : tests/test_copies_horodatees.py (17). Reste : écran de liste et bouton « Restaurer » (Codex). |
| V1-7-04 (L155) | verrou d'ouvrage ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-7-05 (L156) | reprise sans perte après un arrêt brutal. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-7-06 (L157) | **Journal :** fichier tournant, sans donnée sensible, consultable dans l'interface. Aucune exception brute n'est affichée à l'utilisateur. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-7-07 (L158) | **Sécurité :** | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-7-08 (L159) | le serveur n'écoute que sur 127.0.0.1 ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-7-09 (L160) | aucun appel réseau sortant ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-7-10 (L161) | toutes les entrées sont échappées ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-7-11 (L162) | aucun chemin hors des dossiers autorisés ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-7-12 (L163) | les classeurs piégés (macros, liens externes, formules) sont refusés ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-7-13 (L164) | les dépendances sont auditées, sans vulnérabilité connue. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-7-14 (L165) | **Performance** (ouvrage synthétique de 300 équipements et 5 000 variables) : | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-7-15 (L166) | ouverture en moins de 2 s ; | fait | bench/performance.py et validation/performance/RESULTAT_LOCAL.json : 300 équipements / 5000 variables / 70 fichiers ; ouverture 0,031 s, génération 0,026 s, adressage 0,649 s, import 0,016 s, exports 1,014 s, rendu 0,092 s, filtrage 0,119 s ; aucune limite modifiée. Mesure locale, CI distante à confirmer. |
| V1-7-16 (L167) | génération des variables en moins de 3 s ; | fait | bench/performance.py et validation/performance/RESULTAT_LOCAL.json : 300 équipements / 5000 variables / 70 fichiers ; ouverture 0,031 s, génération 0,026 s, adressage 0,649 s, import 0,016 s, exports 1,014 s, rendu 0,092 s, filtrage 0,119 s ; aucune limite modifiée. Mesure locale, CI distante à confirmer. |
| V1-7-17 (L168) | adressage en moins de 2 s ; | fait | bench/performance.py et validation/performance/RESULTAT_LOCAL.json : 300 équipements / 5000 variables / 70 fichiers ; ouverture 0,031 s, génération 0,026 s, adressage 0,649 s, import 0,016 s, exports 1,014 s, rendu 0,092 s, filtrage 0,119 s ; aucune limite modifiée. Mesure locale, CI distante à confirmer. |
| V1-7-18 (L169) | interface en moins de 200 ms, y compris le filtrage d'une table de 5 000 lignes ; | fait | bench/performance.py et validation/performance/RESULTAT_LOCAL.json : 300 équipements / 5000 variables / 70 fichiers ; ouverture 0,031 s, génération 0,026 s, adressage 0,649 s, import 0,016 s, exports 1,014 s, rendu 0,092 s, filtrage 0,119 s ; aucune limite modifiée. Mesure locale, CI distante à confirmer. |
| V1-7-19 (L170) | import de 70 fichiers .$$t en moins de 10 s ; | fait | bench/performance.py et validation/performance/RESULTAT_LOCAL.json : 300 équipements / 5000 variables / 70 fichiers ; ouverture 0,031 s, génération 0,026 s, adressage 0,649 s, import 0,016 s, exports 1,014 s, rendu 0,092 s, filtrage 0,119 s ; aucune limite modifiée. Mesure locale, CI distante à confirmer. |
| V1-7-20 (L171) | exports en moins de 5 s. | fait | bench/performance.py et validation/performance/RESULTAT_LOCAL.json : 300 équipements / 5000 variables / 70 fichiers ; ouverture 0,031 s, génération 0,026 s, adressage 0,649 s, import 0,016 s, exports 1,014 s, rendu 0,092 s, filtrage 0,119 s ; aucune limite modifiée. Mesure locale, CI distante à confirmer. |
| V1-7-21 (L172) | Un banc reproductible est dans `bench/`. | fait | bench/performance.py et validation/performance/RESULTAT_LOCAL.json : 300 équipements / 5000 variables / 70 fichiers ; ouverture 0,031 s, génération 0,026 s, adressage 0,649 s, import 0,016 s, exports 1,014 s, rendu 0,092 s, filtrage 0,119 s ; aucune limite modifiée. Mesure locale, CI distante à confirmer. |
| V1-8-01 (L176) | **Control Expert :** | en attente de preuves utilisateur | Exports de référence, comptes rendus et réexports Control Expert 14.1 / TOPKAPI 6.3 / S4W-Tools non fournis ; structure et protocole de recette à préparer. |
| V1-8-02 (L177) | les exports de référence de `validation/controlexpert/references/` (anonymisés ou fictifs) définissent le format attendu pour la version indiquée dans `ENVIRONNEMENT.md` ; | en attente de preuves utilisateur | Exports de référence, comptes rendus et réexports Control Expert 14.1 / TOPKAPI 6.3 / S4W-Tools non fournis ; structure et protocole de recette à préparer. |
| V1-8-03 (L178) | le XSY généré par OGIAS doit leur être équivalent ; | en attente de preuves utilisateur | Exports de référence, comptes rendus et réexports Control Expert 14.1 / TOPKAPI 6.3 / S4W-Tools non fournis ; structure et protocole de recette à préparer. |
| V1-8-04 (L179) | leur lecture se fait sans perte ; | en attente de preuves utilisateur | Exports de référence, comptes rendus et réexports Control Expert 14.1 / TOPKAPI 6.3 / S4W-Tools non fournis ; structure et protocole de recette à préparer. |
| V1-8-05 (L180) | chaque compte rendu d'import et chaque réexport de `imports_ogias/` est analysé, et tout avertissement ou toute perte est un défaut à corriger ; | en attente de preuves utilisateur | Exports de référence, comptes rendus et réexports Control Expert 14.1 / TOPKAPI 6.3 / S4W-Tools non fournis ; structure et protocole de recette à préparer. |
| V1-8-06 (L181) | ces fichiers deviennent des tests automatiques (génération, lecture, aller-retour). | en attente de preuves utilisateur | Exports de référence, comptes rendus et réexports Control Expert 14.1 / TOPKAPI 6.3 / S4W-Tools non fournis ; structure et protocole de recette à préparer. |
| V1-8-07 (L182) | **TOPKAPI 6.3 et S4W-Tools :** même démarche dès que des preuves sont fournies. | en attente de preuves utilisateur | Exports de référence, comptes rendus et réexports Control Expert 14.1 / TOPKAPI 6.3 / S4W-Tools non fournis ; structure et protocole de recette à préparer. |
| V1-8-08 (L183) | **COMPATIBILITE.md :** ne déclare compatible que ce qui a été réellement importé sans erreur dans le logiciel réel, avec la version et la date. Il liste précisément les essais restant à faire sur les logiciels réels. | en attente de preuves utilisateur | Exports de référence, comptes rendus et réexports Control Expert 14.1 / TOPKAPI 6.3 / S4W-Tools non fournis ; structure et protocole de recette à préparer. |
| V1-9-01 (L187) | **Installation :** | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-9-02 (L188) | version portable Windows 10 / 11, hors ligne, sans droits administrateur, avec un Python embarqué et un lanceur ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-9-03 (L189) | script de construction reproductible. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-9-04 (L190) | **Données :** séparées du programme. Une mise à jour (y compris depuis la V0.30 ou la V0.31) ne touche jamais aux ouvrages. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-9-05 (L191) | **Installation vierge :** sans donnée de démonstration. Un ouvrage d'exemple fictif est fourni à part. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-9-06 (L192) | **Documentation en français, avec captures de l'interface finale :** | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-9-07 (L193) | MANUEL_UTILISATEUR (PDF et Markdown) ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-9-08 (L194) | GUIDE_ADMINISTRATEUR ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-9-09 (L195) | REGLES_DE_NOMMAGE, générées depuis le référentiel ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-9-10 (L196) | CHANGELOG.md, au format Keep a Changelog ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-9-11 (L197) | NOTES_DE_VERSION_1.0 ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-9-12 (L198) | COMPATIBILITE.md ; | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-9-13 (L199) | LICENCES_TIERCES.md. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-10-01 (L203) | **Intégration continue GitHub Actions**, à chaque push et chaque pull request, sous Windows et Linux : | partiel | .github/workflows/ci.yml ; Actionlint 1.7.7 valide ; exécutions GitHub Windows/Linux encore à observer. |
| V1-10-02 (L204) | dépendances à versions figées ; | fait | requirements-ci.lock, requirements-runtime.lock ; résolution Windows --dry-run réussie ; tests/test_ci.py ; Python/Node/actions figés. |
| V1-10-03 (L205) | tests unitaires et d'intégration, avec couverture ; | fait | outils/ci.py python ; tests/test_ci.py ; 541 tests réussis, 0 ignoré, rapport JUnit et couverture du lancement local stable. |
| V1-10-04 (L206) | tests navigateur (Playwright) ; | fait | tests_web/test_variables_v031.py ; outils/ci.py web : 6 tests réussis sur serveur réel (comparaison maquettes V1 encore distincte). |
| V1-10-05 (L207) | banc de performance bloquant ; | fait | bench/performance.py ; lancement 300/5000/70 terminé en code 1 sur dépassements ; tests/test_ci.py::test_command_failure_preserves_exit_status_and_output. |
| V1-10-06 (L208) | analyse statique ; | fait | ruff.toml, mypy.ini, outils/ci.py static ; Ruff F/E9, mypy avec check_untyped_defs sur 43 fichiers moteur et syntaxe de tous les JS sans erreur ; tests/test_ci.py. |
| V1-10-07 (L209) | audit des dépendances ; | fait | outils/ci.py audit ; requirements-ci.lock ; 0 vulnérabilité connue, aucun ID ignoré ; rapport JSON hors dépôt dans /workspace/ogias-cloud/v1/ci-audit-final/. |
| V1-10-08 (L210) | contrôle anti-données réelles (motifs interdits listés dans un fichier de contrôle) ; | fait | validation/CONTROLE_DONNEES.json et outils/verifier_donnees.py ; tests/test_ci.py::test_data_control_finds_normalized_content_without_disclosing_it ; 24 contenus bloqués, aucune valeur imprimée. |
| V1-10-09 (L211) | construction de la version portable en artefact. | partiel | outils/construire_portable.py et outils/tester_portable.py ; tests/test_ci.py valide SHA, chemins et reproductibilité ; exécution Windows en attente CI distante. |
| V1-10-10 (L212) | **Qualité du code :** | partiel | Statique/types/couverture et audit locaux conformes ; audit données et performance encore bloquants. |
| V1-10-11 (L213) | analyse statique sans erreur ; | fait | outils/ci.py static ; Ruff F/E9 sur tout le code suivi (hors ressources historiques), syntaxe JS ; journaux du lancement local. |
| V1-10-12 (L214) | vérification des types sur le moteur ; | fait | mypy.ini ; contrôle de tous les corps activé (check_untyped_defs=True), 0 diagnostic sur 43 fichiers ; tests/test_tableur_robustesse.py et suite complète après correction des 58 diagnostics. |
| V1-10-13 (L215) | couverture d'au moins 85 % sur `genvar/`, et de 100 % sur les exports industriels ; | fait | outils/ci.py coverage : genvar 88,55 %, trois modules industriels 100 %, aucune exclusion ; tests/test_exports_robustesse.py, tests/test_formats_control_expert.py, tests/test_formats_topkapi.py. |
| V1-10-14 (L216) | aucun code mort, fichier temporaire ou secret. | partiel | Imports/variables inutilisés retirés, deux anciens helpers XSY privés sans appel supprimés ; références historiques interdites encore détectées et licences de distribution à auditer. |
| V1-10-15 (L217) | **Branches :** | absent | Aucun test V1 complet identifié à ce stade. |
| V1-10-16 (L218) | branche principale protégée : aucune fusion sans intégration continue verte ; | absent | Protection GitHub non vérifiable via API actuellement refusée ; règle de fusion à configurer et vérifier. |
| V1-10-17 (L219) | aucune réécriture de son historique. | fait | Branche release/1.0 issue de df38702 ; aucun reset/rebase/force-push de main, références distantes main inchangées ; vérification git ls-remote. |
| V1-10-18 (L220) | **Versions :** | absent | Aucun test V1 complet identifié à ce stade. |
| V1-10-19 (L221) | `VERSION = "1.0.0"` défini à un seul endroit ; | absent | Aucun test V1 complet identifié à ce stade. |
| V1-10-20 (L222) | étiquette `v1.0.0-rc1`, puis `v1.0.0` après la recette finale ; | absent | Aucun test V1 complet identifié à ce stade. |
| V1-10-21 (L223) | release GitHub avec la version portable, sa somme SHA-256 et les notes de version. | absent | Aucun test V1 complet identifié à ce stade. |
| V1-10-22 (L227) | Intégration continue verte sous Windows et Linux, sans test ignoré non justifié. | absent | Aucun test V1 complet identifié à ce stade. |
| V1-10-23 (L228) | Tableau de conformité à ce cahier des charges (exigence, état, preuve) entièrement « fait », chaque ligne prouvée par un test. | absent | Aucun test V1 complet identifié à ce stade. |
| V1-10-24 (L229) | Couverture, analyse statique et audit conformes. | partiel | Couverture 88,55/100 %, Ruff et mypy sans erreur, audit 0 vulnérabilité ; commandes/outils dans docs/CI.md. Windows distant à confirmer au critère 1. |
| V1-10-25 (L230) | Banc de performance dans les objectifs. | fait | bench/performance.py et validation/performance/RESULTAT_LOCAL.json : 300 équipements / 5000 variables / 70 fichiers ; ouverture 0,031 s, génération 0,026 s, adressage 0,649 s, import 0,016 s, exports 1,014 s, rendu 0,092 s, filtrage 0,119 s ; aucune limite modifiée. Mesure locale, CI distante à confirmer. |
| V1-10-26 (L231) | Installation sur un Windows propre depuis l'artefact : ouvrage neuf jusqu'à la recette, import d'un projet existant fictif, ouverture d'un ouvrage créé en V0.30. Captures d'écran. | absent | Aucun test V1 complet identifié à ce stade. |
| V1-10-27 (L232) | Aucune donnée réelle ni de l'ancien exploitant dans le dépôt, les artefacts ou les captures. | partiel | outils/ci.py data : 0 détection sur l’état rapproché ; tests/test_verifier_donnees_portable.py ; l’audit de l’artefact Windows rapproché et des captures finales reste à prouver. |
| V1-10-28 (L233) | COMPTE_RENDU_V1.0.md complet : | absent | Aucun test V1 complet identifié à ce stade. |
| V1-10-29 (L234) | bilan ; | absent | Aucun test V1 complet identifié à ce stade. |
| V1-10-30 (L235) | décisions prises ; | absent | Aucun test V1 complet identifié à ce stade. |
| V1-10-31 (L236) | résultats exacts des tests et de la couverture ; | absent | Aucun test V1 complet identifié à ce stade. |
| V1-10-32 (L237) | mesures de performance ; | absent | Aucun test V1 complet identifié à ce stade. |
| V1-10-33 (L238) | précision et rappel du rapprochement ; | absent | Aucun test V1 complet identifié à ce stade. |
| V1-10-34 (L239) | essais restant à faire sur les logiciels réels. | absent | Aucun test V1 complet identifié à ce stade. |
| V1-11-01 (L243) | Le projet réel est strictement confidentiel. Aucune donnée réelle n'entre dans le dépôt : seulement des données fictives (lieu XTST) ou anonymisées par l'utilisateur. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-11-02 (L244) | Ne supprimer aucune fonction opérationnelle. Ne pas modifier les projets originaux. Préserver les anciens repères et les anciennes adresses. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-11-03 (L245) | Aucune donnée de démonstration dans une installation vierge. Aucune intelligence artificielle embarquée. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-11-04 (L246) | N'inventer aucune caractéristique constructeur, aucun format industriel, aucune adresse pour un projet existant. Ne jamais déclarer un export compatible sans essai qui le prouve. | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |
| V1-11-05 (L247) | Toute bibliothèque ajoutée a une licence compatible avec une vente commerciale (MIT, BSD, Apache, ISC). | partiel | Fonctions/tests hérités de df38702 à vérifier contre cette exigence ; preuve V1 non encore établie. |

## Vérification du lot et décisions prudentes

- Base V2 avant report UI : 535 tests réussis, 97,85 s.
- Les six nouveaux tests de `TestArchivageExcel` démontrent : conservation du statut,
  absence de réactivation avec un ancien classeur, désarchivage explicite, valeur
  invalide refusée, feuille vide signalée, modèle explicitement sans signaux conservé.
- Relecture : aucun changement de catalogue, règle, nom physique ou adresse ; aucune
  publication implicite. L'export conserve l'ordre logique des signaux de modèles.
  Les commandes existantes gardent leurs IDs et leurs événements ; leur unicité et
  leur visibilité sont testées dans Chromium, sans affaiblir le contrôle UI existant.
- Une compatibilité industrielle n'est pas démontrée par les tests internes :
  `COMPATIBILITE.md` et `validation/controlexpert/ENVIRONNEMENT.md` gardent la liste
  des preuves CE 14.1 / TOPKAPI / S4W à fournir. Aucun tag ni release n'est créé.
- Les anciennes étapes et mesures sont disponibles dans l'historique Git et
  `docs/ETAT_TRAVAIL_V031.md` ; seul le checkpoint actif ci-dessus sert à la reprise.

## Preuves navigateur du lot Référentiel V2

**15 tests et 11 sous-cas réussis**, 21,59 s, aucune exception JavaScript ; les
six scénarios Variables hérités sont conservés. Tests :
`tests_web/test_referentiel_codes.py`, `tests_web/test_variables_v031.py`.
Captures inspectables : `validation/interface_v2/referentiel/` ; artefacts du
lancement : `/workspace/ogias-cloud/v2/web-reference-complet/`.

## Lot Référentiel précédent

Commit `84bdd22`, après rebase du seul commit non poussé sur `38efa5d` ; comparaison
Git du moteur, de l'interface, des outils et des tests : octets identiques à l'état
qui a passé les contrôles. Aucun historique poussé n'est réécrit.
Banc du lancement : `validation/performance/RESULTAT_LOCAL_V2.json` — sept seuils
passés, sans modification des limites. Ce lot est suivi de l’adoption décrite ci-dessous.

## Lot Adoption — décisions prudentes et relecture

- Sauvegarde par nom unique, même si deux opérations ont le même horodatage ;
  restauration par remplacement atomique. Avant annulation, une autre copie conserve
  les éventuelles modifications postérieures. Retour arrière limité à la dernière
  adoption de la session, sans persistance d’une commande d’annulation après ouverture.
- Le parcours web exige un ouvrage enregistré et un aperçu toujours actuel.
  Les noms viennent du catalogue effectif de chaque équipement ; aucun nom d’un
  modèle figé n’est présenté à tort comme mis à jour. Une migration de clé de modèle
  figé est refusée, car l’implémentation d’adoption actuelle ne migre pas ces modèles.
- Relecture : aucun changement dans genvar/data, aucune application d’A1, R1 ou D5-b,
  aucune réaffectation d’adresse. Les noms historiques FDC des jeux fictifs servent
  exclusivement à tester leur adoption explicite. Les refus laissent le fichier intact.
  Une erreur d’annulation affiche son motif et garde le projet utilisable.
- Documentation : `docs/ADOPTION_REFERENTIEL.md`. Captures inspectées :
  `validation/interface_v2/adoption/`. Ce ne sont pas les comparaisons aux trois
  maquettes du cahier ; §4 reste partiel.
- Le premier lancement complet a révélé une assertion du nouveau test d’échec de
  restauration comparant une adoption partielle au catalogue entièrement adopté.
  Corrigée pour vérifier la conservation exacte du catalogue partiel avant/après
  l’échec ; aucune assertion héritée ni aucun seuil n’a été retiré ou affaibli.

Validation navigateur finale : **21 tests et 14 sous-cas**, 29,46 s ; aucune exception
JavaScript. `tests_web/test_adoption.py` comporte six scénarios, dont le refus
d’annulation affiché et la conservation des octets après ce refus.
Audit des dépendances : aucune vulnérabilité connue ; statique et audit données conformes.

Banc final du lot : `validation/performance/RESULTAT_ADOPTION_V2.json`, sept seuils
passés, adressage 0,372 s, rendu 50 ms, filtrage 54 ms ; limites inchangées.

Dernier commit fonctionnel : **`1a40195`**. Reprise exacte : L7 / typographie et
icônes embarquées, puis comparaison des trois écrans aux maquettes. A1/R1/D5-b inchangés.

## Lot L7 — ressources graphiques et comparaison

- Inter 4.1 variable et JetBrains Mono 2.304 régulière : octets et licences copiés
  sans modification des archives officielles, SHA-256 dans
  `sorep_web/static/assets/tiers/manifest.json`. L’OFL autorise leur incorporation
  au logiciel vendu ; aucune nouvelle bibliothèque Python/JS n’est ajoutée.
- Lucide 0.468.0 ISC : 19 géométries regroupées en symboles sans modification,
  noms d’appels de V31.icon conservés. Licences accessibles depuis À propos.
- **26 tests navigateur et 29 sous-cas**, 39,92 s. Les ressources sont chargées
  localement, sans aucun accès extérieur accepté pendant les tests.
  `test_detail_garde_les_entetes_alignes_aux_cellules` prouve l’alignement et les
  colonnes visibles dans neuf combinaisons (trois vues, trois résolutions).
- **557 tests Python**, 118,40 s, couverture 88,575957 % / exports 100 % ; statique
  et audit données conformes. Dépendances inchangées depuis l’audit des 48 paquets,
  sans vulnérabilité connue, du lot Adoption.
- Captures 1920×1080 inspectées face aux trois maquettes, rectangles DOM enregistrés
  et écarts consignés : `validation/interface_v2/maquettes/README.md`. L’identité
  visuelle globale n’est pas déclarée faite : densité, dimensions, tableau de bord
  et historique restent partiels. Aucun pourcentage de conformité inventé.
- Relecture : moteur, données et fichiers de dépendances inchangés ; aucune nouvelle
  règle d’adressage, aucun nom ou correspondance ajouté. L’essai des en-têtes a
  reproduit neuf décalages avant le correctif, puis les neuf cas passent. Les six
  scénarios Variables précédents et tous les seuils CI sont conservés.

Banc du lot Ressources : `validation/performance/RESULTAT_RESSOURCES_V2.json`,
sept limites inchangées passées, adressage 0,389 s, rendu 60 ms, filtrage 87 ms.

Dernier commit fonctionnel : **`53783c6`**. Reprise : tableau de bord, clé `point`
des E/S, vrais zéros et cinq étapes ; ensuite densité/dimensions/historique Variables.

## Lot L7 — tableau de bord et relais à Claude

- Répartition calculée avec le champ `point` de l’API E/S. Vérification sur les
  points du moteur ; autre essai sur les quatre natures du contrat visuel, sans
  adresse ni matériel fictivement qualifié. SA utilise l’indigo clair pour laisser
  un seul accent corail au tableau de bord.
- Les données indisponibles restent Non disponible. Le cahier §4 impose « aucun
  compteur à zéro » : les zéros connus deviennent des états vides explicites,
  sans nombre nul ni assimilation à une erreur de chargement. Les premiers tests
  du nouveau lot ont été ajustés à cette exigence, avec assertion supplémentaire
  d’absence de nombre nul ; aucun test hérité n’a été affaibli.
- Les cinq étapes sont accessibles depuis le tableau de bord. Les titres réels
  sont attendus après navigation asynchrone ; le fichier reste identique à l’octet.
  Un essai initial utilisait un attribut interne du shell V0.30 absent : remplacé
  par le titre visible de la page, avec attente de son changement, sans temporisation
  arbitraire. La comparaison du fichier est conservée pour chaque étape.
- Une recette indisponible ou un résumé positif sans détail ne produit jamais
  « Aucune anomalie ». Un total absent ou incohérent n’affiche aucun pourcentage.
- Preuves finales : **557 tests Python**, 0 ignoré, 131,23 s ; **35 tests navigateur
  et 34 sous-cas**, 47,62 s ; couverture 88,575957 % / exports 100 %, statique et
  audit données conformes. Les neuf scénarios du tableau de bord couvrent données
  réelles de test, états vides, erreurs et contrat de présentation synthétique.
- Banc : `validation/performance/RESULTAT_DASHBOARD_V2.json`, sept seuils passés,
  adressage 0,386 s, rendu 56 ms, filtrage 83 ms. Limites inchangées.
- Relecture : seuls interface, tests navigateur, captures et suivi changent.
  Moteur, serveur, catalogue, dépendances et workflows inchangés dans ce lot.
  Les six scénarios Variables initiaux restent conservés. Pas d’application d’A1,
  R1 ou D5-b, pas de push sur release/1.0, PR #1 non fusionnée.
- À la demande de l’utilisateur, **laisser la main à Claude après ce lot**.
  Reprise exacte : lire la passation en tête de docs/INSTRUCTIONS_EN_COURS.md et
  la comparaison des maquettes ; liens des constats vers la correction, puis
  densité/dimensions/historique Variables et activité récente vérifiable.
  API GitHub toujours bloquée par la politique réseau : CI distante non certifiée.

Dernier commit fonctionnel : **`19c64eb`**. Lot terminé ; relais préparé pour
Claude sur demande de l’utilisateur. Agent actif remis à libre. Reprendre au HEAD
de `claude/referentiel-v2`, en lisant la passation ; aucun nouveau lot engagé par Codex.
