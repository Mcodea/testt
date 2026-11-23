# Licences des composants tiers

OGIAS est distribué sous licence propriétaire, tous droits réservés (`LICENCE.md`). Il embarque les composants
suivants. Le cahier des charges (V1-11-05) n'admet que des licences compatibles avec une vente commerciale (MIT, BSD,
Apache, ISC) : les écarts sont signalés ci-dessous et **attendent une décision**.

## Bibliothèques Python livrées (`requirements-runtime.lock`)

| Composant | Version | Licence | Usage dans OGIAS | Conformité au cahier |
| --- | --- | --- | --- | --- |
| openpyxl | 3.1.5 | MIT | Lecture et écriture des classeurs Excel | Conforme |
| et_xmlfile | 2.0.0 | MIT | Dépendance d'openpyxl | Conforme |
| pdfminer.six | 20260107 | MIT | Analyse des PDF de projets PL7 | Conforme |
| charset-normalizer | 3.5.2 | MIT | Dépendance de pdfminer.six | Conforme |
| cryptography | 50.0.1 | Apache-2.0 ou BSD-3-Clause | Dépendance de pdfminer.six (PDF chiffrés) | Conforme |
| cffi | 2.1.1 | MIT-0 | Dépendance de cryptography | Conforme |
| pycparser | 3.0 | BSD-3-Clause | Dépendance de cffi | Conforme |
| PySide6_Essentials | 6.12.0 | LGPL-3.0, ou licence commerciale Qt | Ancienne interface Qt (`genvar_qt`) | **Écart à décider** |
| shiboken6 | 6.12.0 | LGPL-3.0, ou licence commerciale Qt | Dépendance de PySide6 | **Écart à décider** |

**PyMuPDF (AGPL-3.0) n'est plus livré** depuis le 23/11/2026 : remplacé par pdfminer.six, qui produit des
inventaires identiques sur les PDF de référence (`tests/test_analyse_pdf_pl7.py::TestEquivalenceMoteurs`). Il reste
un outil de développement (`requirements-ci.lock`) pour fabriquer les PDF d'essai, non distribué.

**PySide6** ne sert qu'à l'ancienne interface Qt, remplacée par l'interface actuelle. Proposition : ne plus la livrer
dans la version vendue (décision de l'utilisateur attendue).

## Ressources de l'interface (`sorep_web/static/assets/`)

Empreintes et sources dans `sorep_web/static/assets/tiers/manifest.json` ; textes de licence à côté des fichiers et
consultables depuis Aide › À propos.

| Composant | Version | Licence | Usage | Conformité au cahier |
| --- | --- | --- | --- | --- |
| Inter (police) | 4.1 | SIL Open Font License 1.1 | Texte de l'interface | Hors liste du cahier ; l'OFL autorise l'intégration dans un logiciel vendu (police non vendue seule) |
| JetBrains Mono (police) | 2.304 | SIL Open Font License 1.1 | Noms, repères, adresses | Idem |
| Lucide (icônes) | 0.468.0 | ISC | Icônes de l'interface | Conforme |

## Environnement d'exécution de la version portable

| Composant | Licence | Remarque |
| --- | --- | --- |
| CPython (runtime embarqué) | PSF License | Licence permissive ; textes `LICENSE*.txt` copiés dans `runtime/` |

## Outils de développement (non distribués)

pytest, ruff, mypy, coverage, playwright, pip-audit et leurs dépendances (`requirements-ci.lock`) servent aux essais
et à l'intégration continue ; ils ne sont pas livrés avec OGIAS.
