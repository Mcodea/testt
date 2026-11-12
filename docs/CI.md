# Intégration continue V1

Le workflow `.github/workflows/ci.yml` s'exécute à chaque push et pull request,
et peut être lancé manuellement. Il ne publie aucune release et ne fusionne rien.
Les actions sont référencées par leur commit vérifié, les versions Python,
Node et les dépendances sont figées. Les permissions du jeton sont en lecture.

## Contrôles bloquants

| Contrôle | Exécution / objectif |
| --- | --- |
| Python Windows 2025 / Ubuntu 24.04 | `python outils/ci.py python` : au moins 402 cas réellement exécutés, aucun échec/erreur/ignoré ; rapports JUnit et couverture du lancement |
| Couverture | `python outils/ci.py coverage` : au moins 85 % des instructions de `genvar/`, 100 % sans exclusion sur les trois modules de formats/exports industriels natifs |
| Navigateur | `python outils/ci.py web --managed-browser` : serveur et API réels, Chromium, au moins 6 cas, données temporaires |
| Performance | `python outils/ci.py performance` : 300 équipements, 5 000 variables, 70 fichiers TOPKAPI, seuils stricts de la section 7 |
| Statique | `python outils/ci.py static` : Ruff (correction du code, pas reformatage général), mypy sur le moteur, syntaxe de chaque JS livré |
| Dépendances | `python outils/ci.py audit` : service PyPI, collection stricte, versions figées, aucune vulnérabilité ignorée |
| Données | `python outils/ci.py data` : motifs et empreintes de `validation/CONTROLE_DONNEES.json`, rapport sans copie des valeurs interdites |
| Portable Windows | `python outils/construire_portable.py` : runtime Python natif copié, dépendances applicatives seules, ZIP déterministe et SHA-256, audit du contenu |
| Essai portable | `python outils/tester_portable.py <archive> --web` : vérification SHA, extraction contrôlée, Python isolé avec PATH restreint, accueil vierge, puis six tests navigateur sur le programme extrait |

Les modules industriels couverts à 100 % sont `genvar/export_xsy.py`,
`genvar/formats_control_expert.py` et `genvar/formats_topkapi.py`. Les rapports
Excel de travail, lecteurs PDF et autres fonctions restent dans le seuil global
du moteur. Une couverture totale ne constitue pas une qualification constructeur.

Les portes JUnit refusent une collecte vide, un rapport absent ou des tests
ignorés. Un rapport antérieur est supprimé avant l'exécution. Les codes de sortie
des commandes sont conservés. Les rapports sont stockés en artefacts GitHub
pendant 14 jours, y compris en cas d'échec des tests/contrôles.

## Exécution locale

Installer `requirements-ci.lock` dans un environnement virtuel Python 3.12 (dernier correctif fourni par les runners GitHub ; les dépendances restent figées par le verrou).
Les outils ne s'installent pas dans le programme distribué. Chromium peut être
installé avec `python -m playwright install chromium`, ou choisi explicitement
par `OGIAS_TEST_CHROMIUM` pour les contrôles locaux. Les commandes s'exécutent
depuis la racine du dépôt. Les données de recette et caches sont temporaires.

Le portable se construit sur Windows x64 ; un test Linux de l'archive ZIP et
de son SHA ne remplace pas l'essai du runtime Windows. L'artefact CI n'est pas une
release commerciale : la publication attend la matrice de conformité et l'audit
de sortie. Les preuves d'import constructeur sont listées séparément.

## État initial des portes V1

Les portes restent bloquantes pendant le développement : un dépassement de
performance, un contenu interdit dans une source historique ou une couverture
insuffisante rend la CI rouge. Aucun seuil ni motif n'est supprimé pour obtenir
un résultat vert. `ETAT_TRAVAIL.md` conserve les mesures et le travail restant.

Une branche protégée doit exiger les quatre jobs de ce workflow avant fusion.
La présence du YAML ne prouve pas que cette règle est activée dans GitHub ;
son état doit être vérifié dans les paramètres du dépôt avant livraison.
