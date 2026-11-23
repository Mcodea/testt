# Journal des modifications

Toutes les évolutions notables d'OGIAS sont consignées ici. Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).
Numérotation : `MAJEUR.MINEUR.CORRECTIF` à partir de la version 1.0.0 (cahier des charges § 10).

## [Non publié]

Le numéro de version (`genvar/__init__.py`) est encore 0.32 ; il passera à 1.0.0 à la livraison (V1-10-19).

### Ajouté — depuis la fusion du 23/11/2026
- **Annuler / rétablir** (Ctrl+Z, Ctrl+Y, menu Édition) : 30 dernières modifications de l'ouvrage, enregistrées dans
  le fichier ; un indice livré n'est jamais annulé.
- **Copies de sauvegarde** consultables et restaurables : Fichier › Copies de sauvegarde.
- **Verrou d'ouvrage** : un ouvrage n'est jamais modifié par deux OGIAS à la fois ; reprise explicite d'un ouvrage
  ouvert sur un autre poste, qui ne peut alors plus enregistrer.
- **Journal technique** tournant, consultable par Aide › Journal technique.
- **Dupliquer un équipement** au ruban : numéro libre suivant, aucune adresse ni voie reprise.
- **Onglet « Apprentissage des formats »** (menu Outils, explorateur) : exporter depuis l'outil du constructeur, importer
  le fichier, dire de quel format il s'agit, qualifier. Les formats appris n'apparaissent plus dans Standards.
- **Ordre d'export des variables** par équipement (ruban › Ordre d'export) : suivi par toutes les tables exportées,
  sans jamais changer une adresse.
- **Ancienne interface Qt retirée** (`genvar_qt`, `lancer_qt.py`, PySide6) : OGIAS s'ouvre par `OGIAS.bat` ou
  `python -m sorep_web`. Plus aucune bibliothèque LGPL livrée.
- **Licences** : la lecture des PDF PL7 passe de PyMuPDF (AGPL-3.0) à pdfminer.six (MIT), inventaires identiques.
- **Indices de livraison** et **liste des modifications** entre deux indices (Excel, « Tous les livrables »).
- Documentation : guide de l'administrateur, manuel de l'utilisateur, licences tierces, ce journal.

### Corrigé
- La duplication d'un équipement reprenait la carte et la voie de chaque E/S : deux équipements pouvaient revendiquer
  les mêmes voies physiques.
- Une valeur nulle (décalage Modbus 0) apparaissait vide dans la photo d'un indice.

### Ajouté — fusionné dans `release/1.0` le 23/11/2026 (e031ef1), sans nouveau numéro de version
- **Refonte industrielle de l'interface** : menus, ruban, explorateur, panneau de sortie, écrans refondus,
  accessibilité WCAG AA vérifiée sur chaque écran, de 1366 × 768 à 2560 × 1440.
- **Chartes de nommage** construites dans OGIAS ; standards d'ingénierie par client (charte, plan d'adressage,
  chaîne d'outils).
- **Livrables** : modèles de livrables à variables, assistant « créer depuis un export », modèles rangés par logiciel
  cible, génération groupée de tous les livrables avec journal, cahiers d'essais FAT / SAT, grille d'ingénierie,
  attributs d'équipement, aller-retour Excel de la liste des équipements.
- **Formats d'export appris** : liste des E/S physiques, télétransmission et IHM de tout constructeur, appris depuis
  un fichier CSV, TXT ou un classeur Excel (tables TIA Portal) ; chaque export est relu ; qualification après un
  premier essai réel.
- **Gammes de matériel** déclarées par l'atelier pour tout automate ; gamme **Siemens S7-1500** livrée (références
  vérifiées sur le catalogue Siemens).
- Règles de cohérence nommées (R-…) et constats de recette groupés par règle ; alerte d'homonymes entre ouvrages sans
  programme automate déclaré (R-NOM-05).

## [0.32] — 12/11/2026

### Ajouté
- Référentiel V2 : adoption contrôlée d'une nouvelle révision, noms physiques alignés, règles documentaires,
  lexique et dictionnaire des codes, gestion des profils.
- Rapprochement des projets existants avec seuil de confiance et confirmation en lot annulable.
- Copies horodatées avant chaque opération lourde.
- Détail : `docs/NOTES_VERSION_0.32.md`.
