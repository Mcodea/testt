# Jeux de validation récupérés

Ce dossier a été restauré depuis `validation.zip`, fourni par l'utilisateur le
10 novembre 2026. Les **58 fichiers** ont été conservés octet pour octet ; le
cache Python compilé de l'archive n'a pas été recopié. `SOURCE_ARCHIVE.json`
enregistre l'empreinte SHA-256 de l'archive et de chaque fichier restauré.
Les encodages, fins de ligne (dont CRLF), PDF et captures restent inchangés ;
ils ne sont pas normalisés pour satisfaire un contrôle stylistique des espaces.

L'archive contient les ressources qui manquaient aux tests DDT et au benchmark
hybride, ainsi que les autres exemples et rapports de développement associés.
Aucune modification du moteur, des tests, des seuils ou des corrigés n'a été
nécessaire pour rétablir ces validations.

## Données de test et rapports historiques

- `ddt/exemple_DDT_reconstitue.xsy` est explicitement un exemple synthétique,
  pas un export industriel réel ni le fichier public évoqué par son README.
- `hybride/` contient l'évaluateur, les deux jeux fictifs et leurs corrigés.
- `aveugle/` contient un jeu indépendant avec catalogue de référence figé et
  corrigé séparé, réservé à l'évaluation.
- `pdf_pl7/` fournit des PDF fictifs et leurs générateurs de développement.
  Les PDF fournis suffisent aux lecteurs ; les générateurs ne sont pas requis
  pour exécuter la suite pytest.
- Les captures, journaux, CSV/JSON de résultats et rapports présents dans
  l'archive sont des **preuves historiques**. Leur présence ne signifie pas
  qu'ils ont été régénérés ou validés avec le code actuel.

Ces fichiers servent aux tests et ne doivent pas précharger de données dans
une installation utilisateur. Les exemples d'adresses ne sont jamais une
cartographie de production ni une preuve d'accès Modbus, OPC/OFS ou TOPKAPI.

## Résultats du contrôle après restauration

Sur le code de la branche de reprise, avec Python 3.12.14, pytest 9.2.0,
PySide6-Essentials 6.12.0, openpyxl 3.1.5 et PyMuPDF 1.28.2 :

- Modules DDT et rapprochement hybride : **24 tests réussis**.
- Suite pytest complète : **402 réussis, aucun échec, aucun ignoré**, en 68,50 s,
  code de sortie 0. Les 134 avertissements de dépréciation Qt restent présents.
- Recette Chromium : **6 tests réussis**, en 11,31 s.
- Diagnostic XSY hors ligne : 3 variables principales, 4 définitions DDT et
  7 champs développés ; aucun avertissement et aucune adresse de champ calculée.
- Les empreintes des 58 fichiers restent identiques à celles de l'archive après
  ces contrôles. Aucun corrigé, seuil de test ou comportement applicatif modifié.

Ces résultats proviennent des nouveaux lancements, pas des rapports archivés.
Leurs journaux actuels sont sous
`/workspace/ogias-cloud/restauration-validation/` dans la machine de travail ;
ils ne sont pas inclus dans le dépôt. Les commandes de reproduction suivent.

## Reproduire les contrôles

Depuis la racine du dépôt, avec les dépendances de développement installées :

```bash
python -m pytest -q tests/test_xsy_ddt.py tests/test_rapprochement_hybride.py
python -m pytest -q
```

Pour Qt sous Linux sans écran, utiliser `QT_QPA_PLATFORM=offscreen`. Le dossier
de données de l'application doit être temporaire pendant la recette, via
`SOREP_DATA_DIR`, comme dans les comptes rendus de reprise.

La recette Chromium est distincte ; voir [tests_web/README.md](../tests_web/README.md).
Elle utilise elle aussi des ouvrages temporaires et aucune donnée d'exploitation.

Le diagnostic DDT peut être lancé hors ligne sur la fixture fournie en choisissant
un répertoire de sortie hors dépôt :

```bash
python validation/ddt/verifier_xsy_github.py \
  validation/ddt/exemple_DDT_reconstitue.xsy --sortie /tmp/ogias-diagnostic-ddt
```

Certains scripts historiques écrivent leurs résultats dans ce dossier. Pour
préserver les sorties de l'archive, utiliser une copie de travail ou les fonctions
de lecture/évaluation sans lancer leur écriture. Le manifeste décrit la
restauration initiale ; une régénération changera les empreintes concernées.

## Limites du rapprochement

Le benchmark exige une amélioration relative, pas une identification parfaite.
Lors du contrôle actuel, la méthode hybride obtient :

| Jeu | Liens attendus | Bonnes propositions | Fausses | Non proposées | Faux positifs sur signaux absents |
| --- | ---: | ---: | ---: | ---: | ---: |
| Initial | 18 | 18 | 0 | 0 | 0 |
| Difficile | 18 | 12 | 1 | 5 | 2 |

Les suggestions restent à confirmer par un automaticien. Ni la réussite du
test ni un score de classement ne valident une correspondance d'exploitation.
Le moteur et les corrigés n'ont pas été ajustés pour améliorer ces scores.
