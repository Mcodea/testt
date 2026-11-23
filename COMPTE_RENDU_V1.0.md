# Compte rendu de la version 1.0 d'OGIAS

> **Brouillon du 23/11/2026.** Les chiffres sont ceux de ce jour ; ils sont à figer à la livraison, avec le numéro
> 1.0.0 (`genvar/__init__.py` est encore 0.32). Les sections 3 à 7 sont chacune adossées à un fichier ou à une
> commande reproductible.

## 1. Bilan

OGIAS prépare les ouvrages d'automatisme et exporte la liste des E/S physiques de chaque automate, la télétransmission
de chaque supervision et l'IHM. Il n'est lié à aucun constructeur : les formats d'export s'apprennent depuis un fichier
exporté par l'outil du client, les gammes de matériel se déclarent. Schneider (M340, M580) et Siemens (S7-1500 livrée)
sont couverts pour l'instant.

Avancement au tableau de conformité (`ETAT_TRAVAIL.md`, 176 exigences du cahier des charges) : **67 % au sens strict
(99 / 148), 77 % en comptant un « partiel » pour moitié** ; 28 exigences sont remplacées par décision de l'utilisateur
(refonte d'interface) et sortent du calcul. Restent : 31 partielles (dont les 7 lignes de ce compte rendu, en brouillon), 8 absentes (livraison : version,
étiquettes, release, essai sur Windows propre, branche protégée), 10 en attente de fichiers réels des logiciels constructeurs.

## 2. Décisions prises

| Date | Décision |
| --- | --- |
| 11/11 | Seuil de confiance du rapprochement conservé à 80/100 (précision avant rappel). |
| 22/11 | OGIAS n'exporte que trois familles de fichiers (E/S physiques, télétransmission, IHM) ; formats appris depuis un fichier exemple ; qualification après un premier essai réel. |
| 22/11 | Logiciel ouvert à tout constructeur ; Schneider et Siemens pour l'instant. |
| 23/11 | Ordre d'export des variables par équipement, jamais appliqué aux adresses (option B). |
| 23/11 | Licences : PyMuPDF (AGPL) remplacé par pdfminer.six (MIT) ; ancienne interface Qt (PySide6, LGPL) retirée de la version vendue. |
| 23/11 | « Apprentissage des formats » devient un onglet dédié du menu Outils. |

Décision en attente : icônes de la barre et du ruban (dessins propres à OGIAS ou icônes Lucide, cahier V1-4-23).

## 3. Tests et couverture

Résultats du 23/11/2026 sur le dernier état, exécutés localement et en intégration continue (Linux et Windows) :

- **962 tests Python**, 1 290 sous-cas, aucun échec, aucun ignoré non justifié ;
- **136 tests navigateur** (Chromium, serveur réel), 128 sous-cas, dont l'accessibilité WCAG AA de chaque écran de
  1366 × 768 à 2560 × 1440 ;
- analyse statique (Ruff, mypy sur 70 fichiers) et audit anti-données réelles : aucune détection ;
- couverture du moteur : seuil de 85 % imposé par la CI, exports industriels à 100 % (`python outils/ci.py coverage`) ;
  la valeur chiffrée est celle du rapport de la CI (`artifacts/ci/coverage.json`).

## 4. Mesures de performance

Banc `bench/performance.py` : ouvrage synthétique de 300 équipements et 5 000 variables, aucune donnée réelle.

| Mesure | Résultat | Limite |
| --- | ---: | ---: |
| Ouverture | 0,02 s | 2 s |
| Génération | 0,02 s | 3 s |
| Adressage | 0,47 s | 2 s |
| Import de 70 fichiers TOPKAPI | 0,01 s | 10 s |
| Exports | 0,38 s | 5 s |
| Rendu de l'interface | 0,06 s | 0,2 s |
| Filtrage | 0,09 s | 0,2 s |

## 5. Précision et rappel du rapprochement

Source : `validation/hybride/SEUIL_CONFIANCE.md` (généré, vérifié par un test). Au seuil de 80/100, sur deux jeux
fictifs de validation et la méthode hybride : **5 propositions de confiance élevée sur 36 liens, toutes correctes :
précision 100 %, rappel 13,9 %.** Aucune proposition fausse connue n'atteint le seuil (plus haut faux : 79). Le rappel
est volontairement bas : la précision passe avant, et aucune correspondance n'est appliquée sans confirmation humaine.

## 6. Licences

Aucune bibliothèque AGPL ni LGPL n'est livrée ; inventaire complet dans `LICENCES_TIERCES.md`.

## 7. Essais restant à faire sur les logiciels réels

Aucune compatibilité n'est déclarée (`COMPATIBILITE.md`) tant qu'un export n'a pas été importé sans erreur dans l'outil
réel. À fournir ou à réaliser :

- export d'une table de variables **TIA Portal** (Excel) et import du fichier produit par OGIAS ;
- export de variables **Control Expert** (XSY ou Excel), comparaison au XSY généré, import du fichier produit ;
- fichier d'import ou d'export de variables de **TOPKAPI 6.3** ;
- cartes SOFREL S4W et règles S4W-Tools (sortie analogique, courant de sortie TOR) ;
- installation sur un Windows propre depuis l'artefact, et ouverture d'un ouvrage réel créé en V0.30 ;
- protection de la branche principale sur GitHub (réglage du dépôt).
