# OGIAS V0.26 — Module 1 : Inbound / Validation

## Statut

Implémentation Python autonome et tests pytest fournis. **Pas encore reliée à l'interface web**. Les données des projets présents dans l'archive source sont intactes. Ce module n'exporte pas les variables vers Control Expert, S4W-Tools ou TOPKAPI.

## Architecture

- `genvar/inbound/schemas.py` : contrats typés (source, diagnostics, lignes, aperçu, copie préparée).
- `genvar/inbound/readers.py` : lecture bornée et en lecture seule des CSV/TXT, XLSX/XLSM, ODS et SCY textuels.
- `genvar/inbound/normalization.py` : identification des colonnes et synonymes à partir des lecteurs existants.
- `genvar/inbound/validation.py` : contrôles de format, métier, doublons et conflits avec la session courante.
- `genvar/inbound/commit.py` : **intégration en mémoire sur copie**, avec nouvelle prévalidation et refus de toute modification silencieuse.
- `genvar/inbound/__main__.py` : aperçu en ligne de commande, aucun enregistrement.
- `tests/inbound/test_inbound.py` : tests pytest fictifs, y compris panne en milieu d'intégration.

## Contrats fonctionnels

1. Chaque ligne de données lue est classée : `a_creer`, `deja_present`, `refuse`, `ligne_vide`.
2. Les anomalies sont typées `erreur`, `avertissement`, `information` et localisées (feuille et ligne quand possible).
3. Une erreur bloque **tout le lot**. Un avertissement n'empêche pas de préparer un brouillon, mais ne constitue pas une validation métier du matériel ou de l'installation.
4. L'ouvrage doit déjà être identifié. Aucun lieu, type, numéro, repère ou adresse n'est inventé.
5. Une adresse de variable importée reste strictement telle que trouvée ; le module n'effectue pas d'adressage automatique.
6. L'intégration n'est autorisée qu'avec `confirmed=True`. Elle compare le SHA-256 du fichier et l'empreinte de l'ouvrage/référentiel avec l'état de prévisualisation, puis recalcule intégralement l'aperçu.
7. L'intégration travaille sur un clone `Session`, **sans toucher la session initiale**. Le clone est détaché de tout chemin de sauvegarde (`chemin=None`), ce qui évite d'écraser un ancien projet par inadvertance.
8. Aucune API de ce module n'enregistre le projet ni ne modifie un fichier source. Le workflow UI de validation/sauvegarde fera l'objet d'un autre lot explicite.

## API Python

```python
from genvar.inbound import InputKind, preview_import, stage_import

apercu = preview_import("inventaire.xlsx", InputKind.INVENTORY, session)
rapport = apercu.to_report()  # Dict sérialisable en JSON pour l'interface
if not apercu.errors:
    operation = stage_import(apercu, session, confirmed=True)
    copie_non_enregistree = operation.session
```

Modes supportés :
- `InputKind.INVENTORY` : inventaire équipement, avec conservation des anciens formats de repère.
- `InputKind.PLC_VARIABLES` : variables d'un **projet existant**, préservation des types et adresses.
- `InputKind.PHYSICAL_IO` : points E/S documentaires pour rapprochement d'un **projet existant**.

### CLI en lecture seule

```bash
python -m genvar.inbound --projet chemin/ouvrage.ouvrage.json --source inventaire.xlsx --kind inventaire --resume
```

Retour 0 : pas d'erreur bloquante. Retour 2 : anomalie bloquante ou lecture impossible. **Aucune modification de projet**, y compris si le retour est 0.

## Limites et qualifications à prévoir

- L'analyse XML XSY et les formats binaires propriétaires ne sont pas couverts par ce module. Il est interdit de simuler leur compatibilité.
- Un SCY textuel non documenté est accepté uniquement si le lecteur legacy reconnaît explicitement l'adresse et le nom. Les numéros affichés peuvent être logiques après normalisation du contenu SCY.
- La couche de validation des adresses mémoire n'est **pas** le futur moteur d'adressage : les adresses historiques sont conservées, sans supposer qu'elles sont disponibles ou physiquement compatibles.
- Une donnée de modèle absente/inconnue reste à compléter et ne provoque pas la création silencieuse d'un modèle métier.
- L'absence de défaut détecté dans ces tests ne garantit pas zéro bug ; les validations dans les logiciels industriels devront être réalisées sur leurs formats réels.
- Le navigateur et la sauvegarde UI doivent être branchés ultérieurement : `stage_import` ne doit pas être appelé silencieusement au chargement d'un fichier.

## Tests

Depuis la racine OGIAS :

```bash
python -m pytest -q tests/inbound/test_inbound.py
python -m pytest -q tests tests_qt
```

Les tests créent uniquement des sources fictives temporaires. Ils vérifient les doublons, lignes vides, fichiers altérés, réimport, repères historiques, champs manquants, formules Excel, conflits, réapplication et rollback.

### Non-régression du test historique

`tests/test_plan_amelioration_lot1.py` attendait encore « écran en préparation » ; cette assertion échouait déjà dans la V0.26 fournie. Elle a été actualisée pour contrôler l'existence des écrans Variables, Supervision et Recette effectivement présents dans la V0.26, sans toucher à l'interface.
