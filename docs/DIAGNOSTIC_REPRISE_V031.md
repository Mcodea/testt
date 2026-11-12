# OGIAS V0.31 — Diagnostic de reprise et plan de finalisation

Date : 10 novembre 2026. Base examinée : `9eff10546d94cecf486438ea0b35956da84c2fc6`
(`Sauvegarde initiale OGIAS V0.31 - version non finalisee`). Le HEAD distant de
`main` correspond à cette base lors du contrôle.

Branche de travail : `codex/diagnostic-finalisation-v031`.

Suivi : les ressources manquantes ont ensuite été retrouvées dans l'archive
fournie par l'utilisateur ; voir [la provenance et les contrôles](../validation/README.md).
Les constats ci-dessous décrivent la base examinée avant cette restauration.

Cette première étape contient uniquement le diagnostic et le plan proposés.
Aucun code métier, interface, test, référentiel ou format de projet n'est modifié.
Les corrections attendent la validation de l'utilisateur.

## 1. Résultat reproduit dans l'environnement publié

Depuis `/workspace/OGIAS`, avec l'environnement Python déjà installé :

```bash
SOREP_DATA_DIR="$(mktemp -d /tmp/ogias-reprise-tests.XXXXXX)" \
QT_QPA_PLATFORM=offscreen XDG_CONFIG_HOME=/tmp/ogias-reprise-config \
/workspace/.venvs/ogias/bin/python -m pytest -q -r fEs -p no:cacheprovider \
  --junitxml=/workspace/ogias-cloud/reprise-v031/pytest.xml
```

Le contrôle effectué a redirigé la sortie vers
`/workspace/ogias-cloud/reprise-v031/pytest.log`, en conservant le code de sortie.

| Résultat | Nombre |
| --- | ---: |
| Tests exécutés | 402 |
| Réussis | 392 |
| Échoués | 10 |
| Erreurs de collecte/exécution distinctes des échecs | 0 |
| Ignorés | 0 |

Durée du lancement : 68,08 s ; code de sortie : 1. Les 132 avertissements
concernent la dépréciation Qt de `QSortFilterProxyModel.invalidateFilter()`.
Ils ne sont pas la cause des dix échecs.

Versions : Python 3.12.14, pytest 9.2.0, PySide6-Essentials / shiboken6 6.12.0,
openpyxl 3.1.5 et PyMuPDF 1.28.2. Aucun paquet n'a été réinstallé pour ce diagnostic.

Les nombres historiques de `ETAT_TRAVAIL.md` et des comptes rendus V0.30
(`373 passed, 25 skipped`) ne constituent pas le résultat actuel. Les dépendances
Qt et PDF sont présentes ; les quatre tests structurels propres à V0.31 sont
également exécutés. Ils réussissent, mais ne remplacent pas une recette navigateur.

## 2. Diagnostic des dix échecs

### 2.1 Huit tests DDT : fixture absente

Fichier : `tests/test_xsy_ddt.py`, classe `TestsDDT`.

Le chemin `FIXTURE` est fixé à
`validation/ddt/exemple_DDT_reconstitue.xsy`. Ce fichier n'existe pas dans le
checkout. `git ls-tree -r --name-only HEAD validation` et l'historique local de
ce chemin ne fournissent aucun fichier ; aucun sous-module ne le fournit.

| Test échoué | Contrôle qui reste à démontrer avec la fixture |
| --- | --- |
| `test_ancien_lecteur_reste_compatible` | Compatibilité du lecteur historique XSY |
| `test_doublon_chemin_refuse_sans_mutation` | Refus des doublons sans mutation |
| `test_export_excel_conserve_origine_et_parent` | Conservation des métadonnées DDT dans l'Excel |
| `test_import_et_sauvegarde_des_metadonnees` | Import et persistance des métadonnées |
| `test_lit_parents_et_champs_reels_sans_addresse_calculee` | Lecture des parents/champs sans fabriquer d'adresse |
| `test_reimport_changement_adresse_parent_invalide_validation` | Invalidation après changement d'adresse du parent |
| `test_selection_ddt_n_est_pas_validation_de_l_adresse` | Sélection distincte de la validation d'acquisition |
| `test_validation_ddt_requiert_mapping_et_confirmation_documentaire` | Correspondance et accès vérifié nécessaires à la validation |

Les huit traces se terminent par `FileNotFoundError` sur cette même fixture,
avant les assertions métier attendues. Les quatre autres tests du fichier,
qui construisent leur XML temporaire eux-mêmes, réussissent. Ils ne couvrent
pas intégralement les huit scénarios indisponibles.

**Diagnostic :** dépendance de test absente du dépôt, et non dépendance Python
manquante. Ces échecs ne démontrent pas un défaut du lecteur DDT ; ils empêchent
de conclure sur les scénarios concernés.

**Correction proposée après validation :** rechercher et récupérer la fixture
originale dans les sauvegardes de développement, vérifier sa provenance et son
caractère exclusivement fictif, puis la versionner avec les tests. Ne pas
reconstituer des données pour satisfaire les assertions, déduire l'adresse d'un
champ depuis l'adresse du parent, ni remplacer ces échecs par des tests ignorés.
Si l'original est irrécupérable, faire valider un nouveau jeu indépendant avec
ses attendus documentés avant toute modification de ces tests.

### 2.2 Un benchmark hybride : banc d'évaluation absent

Test :
`tests/test_rapprochement_hybride.py::RapprochementHybride::test_benchmarks_deux_scenarios`.

L'import `from validation.hybride.evaluer import evaluer, BASE` échoue avec
`ModuleNotFoundError: No module named 'validation'`. Le module et les jeux
qu'il doit désigner ne sont pas présents dans l'arbre Git examiné.

Le test doit comparer deux scénarios (`BASE` et `BASE / 'jeu_difficile'`), chacun
avec 18 liens attendus, puis comparer les stratégies programme/catalogue/hybride.
Aucun de ces résultats n'est calculé pendant le lancement actuel. Les onze
autres tests du fichier réussissent, notamment les protections des sources,
adresses, types et choix manuels ; cela ne valide pas la performance comparative.

**Correction proposée après validation :** récupérer ensemble le module
d'évaluation, les deux jeux, leurs corrigés et leur provenance. Ne pas coder une
fonction qui renvoie les scores attendus, fabriquer de correspondances ni modifier
les seuils pour obtenir du vert. L'absence persistante du banc doit rester
explicite dans le bilan de recette.

### 2.3 Un test Qt : précondition de navigation manquante

Test :
`tests_qt/test_fumee_qt.py::TestInterfaceQt::test_explorateur_ouvrage`.

`Fenetre.__init__()` appelle `self.accueil()` ; la page active du `QStackedWidget`
est donc `v_accueil`. Le test pilote directement `v_ouvrage._action_arbre(...)`
sans ouvrir la page Ouvrage, puis exige `vo.arbre.isVisible()`.

Un contrôle isolé a reproduit le résultat :

| Observation | Résultat |
| --- | --- |
| Page active initiale = accueil | `True` |
| Page Ouvrage masquée | `True` |
| Arbre explicitement masqué (`isHidden()`) | `False` |
| Arbre visible avant navigation (`isVisible()`) | `False` |
| Même méthode de test après `f.aller('Ouvrage')` et traitement des événements | Réussie |
| Arbre visible après cette navigation | `True` |

Trace du contrôle : `/workspace/ogias-cloud/reprise-v031/qt-diagnostic.log`.

**Diagnostic :** précondition manquante dans ce test. Les éléments d'une page
masquée ne sont pas visibles, même s'ils ne sont pas cachés explicitement.
Cela ne justifie pas de changer la page d'accueil ou l'affichage de l'application.

**Correction proposée après validation :** ouvrir Ouvrage dans ce test avant
de piloter l'arbre, conserver l'assertion de visibilité, puis relancer le test,
les 25 tests Qt et la suite complète. Ne pas forcer tous les tests à démarrer
sur Ouvrage : les tests de navigation vérifient précisément l'accueil.

## 3. État du développement existant

L'examen couvre `ETAT_TRAVAIL.md`, `PLAN_V031.md`, `README.md`, `LISEZ-MOI.md`,
les comptes rendus V0.26 à V0.30, celui de la liste d'E/S, les documents des
modules 1/2 et du référentiel, ainsi que les points d'entrée, les modules
concernés et les tests existants. Le code n'a pas fait l'objet d'un audit exhaustif.

| Couche | État constaté et contrainte pour la reprise |
| --- | --- |
| `genvar/` | Moteur et modèles existants à conserver. Le plan d'adressage possède déjà empreinte, refus des conflits, protection des adresses et retour arrière. |
| `sorep_web/serveur.py` | API existantes conservées ; les actions Variables et Adressage délèguent à `Session`. |
| `sorep_web/static/` | `app.js` et la coque V0.30 restent chargés ; V0.31 les complète via `v031-ui.js`, `v031-variables.js`, `v031.css`. Préserver les événements lors du déplacement de commandes. |
| Interface V0.31 | Navigation, accueil, dashboard et table Variables présents ; pagination à 150 lignes dans le code. Recette à 5 000 lignes encore requise. |
| Tests | Les protections d'adressage, scénarios industriels synthétiques, imports, référentiel et API HTTP sont exercés. Les quatre tests V0.31 contrôlent surtout la structure des fichiers JS/CSS. |
| Qt | Interface historique, distincte du parcours web principal. 24 tests Qt réussis, un échec de précondition expliqué ci-dessus. |
| Version et distribution | Le titre web annonce 0.31, `genvar.VERSION` reste à 0.30. `ETAT_TRAVAIL.md` reporte explicitement sa mise à jour à la fin de la recette. |

Vérifications complémentaires actuelles : syntaxe des quatre fichiers JS chargés
(`app.js`, `v030-shell.js`, `v031-ui.js`, `v031-variables.js`) conforme avec
`node --check`. Un contrôle Chromium de l'accueil puis du référentiel, servi
par l'API locale avec un dossier de données temporaire vide, réussit à 1366×768
sans exception JavaScript ni débordement horizontal de page. Il ne couvre pas
les parcours métier complets ni les autres tailles et thèmes. Le script de ce
contrôle a été corrigé pour accepter l'absence normale de nouvelle réponse HTTP
lors d'une navigation par fragment ; le lancement corrigé se termine avec le
code 0. Trace : `/workspace/ogias-cloud/reprise-v031/browser-smoke.log`.
Les rapports historiques de captures V0.30 sont des références,
pas une preuve de recette complète de V0.31.

Les archives V0.30 et les trois maquettes mentionnées par le plan ne sont pas
retrouvées parmi les fichiers de travail inspectés. Les captures V0.30 du dépôt
restent utilisables ; récupérer les références manquantes avant de prétendre à
une comparaison exhaustive avec la livraison antérieure.

La compatibilité doit préserver aussi les recontrôles déjà existants à l'ouverture :
`Session.ouvrir()` peut remettre un ancien statut à contrôler en mémoire et
afficher un avertissement, sans réécrire le fichier source. Il ne faut ni ajouter
de migration silencieuse ni supprimer ce garde-fou au nom de la compatibilité.

Les arbitrages du référentiel consignés dans `docs/AUDIT_REFERENTIEL.md`
(seuils, totalisateur, défauts de mesure) ne sont pas des corrections à appliquer
automatiquement pendant la finition visuelle.

## 4. Plan de finalisation proposé — soumis à validation

| Étape | Travail délimité | Critère de sortie |
| --- | --- | --- |
| 1. Rendre la référence de tests complète | Récupérer les fichiers de validation manquants et corriger uniquement la précondition du test Qt. Examiner les nouveaux résultats avant toute correction moteur. | Les dix scénarios s'exécutent réellement ; aucun échec inexpliqué, test supprimé ou assertion affaiblie. Suite complète relancée. |
| 2. Figer les références de compatibilité | Constituer des copies de projets de test ancien/neuf/existant, récupérer les références V0.30 disponibles, enregistrer les exports témoins et les contrats API utilisés par V0.31. | Comparaison avant/après des repères, noms, adresses, choix, snapshots du référentiel et fichiers source ; aucun changement sans décision explicite. |
| 3. Recetter les parcours web réels | Avec l'API locale et des données exclusivement fictives : création/ouverture, import avec aperçu, équipements, E/S, matériel, variables, télétransmission, recette, exports, sauvegarde/réouverture ; cycle du référentiel. | Actions conservées et accessibles ; propositions distinctes des validations ; refus vérifiés pour collisions, plan périmé, import invalide et disponibilité non attestée. Aucun réadressage historique. |
| 4. Corriger les défauts V0.31 démontrés | Pour chaque défaut : reproduction, justification, correction minimale dans la couche concernée, test pertinent puis non-régression. Harmonisation visuelle seulement là où la recette la justifie. | Pas de fonction perdue, API supprimée ou refonte générale ; chaque changement relié à un défaut et à une vérification. |
| 5. Achever la recette d'interface | Contrôler les écrans et modales à 1920×1080 et 1366×768, clair/sombre, focus/clavier, contrastes, erreurs, filtres, pagination et table de 5 000 lignes. Mesurer les performances avant de proposer une optimisation. | Captures et résultats reproductibles ; aucune erreur JS ni commande indispensable inaccessible. Décisions explicites sur les écarts visuels. |
| 6. Comparer les livrables et clôturer | Comparer XSY/TXT, contenu des classeurs Excel et formats déjà pris en charge aux témoins ; suite pytest complète ; démarrage Windows sur copie ; puis version, documentation et archive `OGIAS_V031.zip`. | Aucun échec inexpliqué dans le périmètre de livraison, compatibilité vérifiée sur les jeux disponibles, limites et résultats documentés ; PR relue, aucune fusion automatique. |

Après chaque correction : exécuter ses tests ciblés et les tests de contrat
affectés. Exécuter la suite complète à la fin de chaque lot cohérent. Le présent
changement documentaire ne modifie aucun comportement et ne nécessite pas de
relancer les 402 tests déjà exécutés sur cette même base applicative.

Les validations dans Control Expert, S4W-Tools, TOPKAPI et sur poste Windows
doivent rester distinctes des contrôles Linux. Ne pas annoncer de qualification
industrielle sans essai dans les logiciels cibles. L'absence de convention ou
de fichier de référence laisse la donnée non résolue ; aucun nouveau format,
adressage EIO/S4W ou rapprochement non vérifié n'entre implicitement dans V0.31.

La première validation demandée porte sur ce plan et l'ordre des travaux.
La récupération des jeux de validation est la première dépendance à résoudre ;
les nouvelles règles métier et les fonctionnalités suivantes feront l'objet
de décisions séparées.

## 5. Traçabilité de cette première tâche

- Seul ajout au dépôt : ce rapport. Pas de modification de configuration cloud,
  de données de projet, de tests ou d'application.
- Traces de ce lancement, hors dépôt :
  `/workspace/ogias-cloud/reprise-v031/pytest.log`, `pytest.xml`,
  `qt-diagnostic.log` et `browser-smoke.log`. Ces chemins locaux ne garantissent pas la disponibilité
  des journaux dans un clone neuf ; les résultats et commandes sont conservés ici.
- Une description de PR documentaire accompagne la branche, sans demande de fusion.
  La création distante dépend de l'accès à l'API GitHub : la lecture Git HTTPS
  réussit, mais la connexion à `api.github.com` renvoie un refus HTTP 403 du proxy
  dans l'environnement actuel. Aucun jeton supplémentaire n'est demandé sur
  la seule base de ce refus réseau.
