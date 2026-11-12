# Rapport d'écarts — référentiel V2 cible contre le schéma réel d'OGIAS

Branche `claude/referentiel-v2`, base `release/1.0` @ `c3e506e`. Spécification : `docs/referentiel/OGIAS_REFERENTIEL_V2.xlsx`.

## 1. Format d'import

- Le classeur V2 **n'est pas importable** tel quel : l'import du référentiel attend un export OGIAS
  (`Lisez-moi` → `Format = OGIAS-REFERENTIEL-1`, onglets Types, Signaux, Règles, Types de modèles, Modèles,
  Lignes de modèles, Lexique, Dictionnaire E-S). Aucun adaptateur n'est créé : la V2 est intégrée **dans les
  fichiers du référentiel livré** (`genvar/data/catalogue_defaut.json`, `referentiel_modeles.json`), publiés
  comme nouvelle révision par le cycle existant. Les projets gardent leur référentiel figé.
- Colonnes V2 → champs réels :

| Colonne V2 | Champ OGIAS | État |
| --- | --- | --- |
| Signaux · « Suffixe ES V2 (facultatif) » | `suffixe_es` du signal (nouveau, facultatif) | L3 |
| Signaux · « Précision physique V2 » | `remarque` du signal (existant) | L3 |
| E-S physiques · « Nom physique cible V2 » | calculé, non stocké | L3 (test) |
| Règles · « Statut V2 / gouvernance » | `gouvernance` de la règle (nouveau) | L5 |
| Règles · « Logique automate » vidée | `logique` vidée ; texte d'origine dans `docs/referentiel/REGLES_AVANT.csv` | L5 |
| Correspondances (absent du V2) | `correspondances` du référentiel des modèles (nouveau, versionné) | L2 |

## 2. Données clés par l'équipement (ce que l'adoption doit reporter)

`Equipement` indexe par `FAMILLE_CODE` : `adresses` (%MW), `adresses_es` (voie physique), `exclus`,
`commentaires`, `libelles`, `validees`, `acceptes`, `motifs`, `traces` (« niveau:clé »), `es_meta`. L'ouvrage
référence aussi la clé dans `existantes[].cle` et `table_tt[].cle` (correspondances TOPKAPI des projets
existants), par `ident_eq`. Aucun autre stockage de clé n'a été trouvé.

## 3. Table ancienne clé → nouvelle clé

| Ancienne | Nouvelle | Nom physique | Nom fonctionnel | Adresses |
| --- | --- | --- | --- | --- |
| `CT.CP_VOL` | `FT.CP_VOL` | `ET_…CT01_VOL` → `ET_…FT01_IMP` (porté par `FT.ES_IMP`) | `CP_…CT01_VOL` → `CP_…FT01_VOL` | %MW et voie conservés |
| `CT.TS_ABSIMP` | `FT.TS_ABSIMP` | — | `TS_…CT01_ABSIMP` → `TS_…FT01_ABSIMP` | %MW conservé |
| 9 signaux à organe `FDC` (CL, DJ, EV, IS, SV, XV) | clé inchangée | `ET_…_FDC_OUV` → `ET_…_OUV` | inchangé | inchangées |
| 5 signaux à `suffixe_es` (MV, PM) | clé inchangée | `ET_…_FDC_OUV` → `ET_…_OUV`, `SA_…_CONS_POS` → `SA_…_POS`, `ST_…_CMD_MA` → `ST_…_MA`, `SA_…_CONS_FREQ` → `SA_…_FREQ` | inchangé | inchangées |

**Point bloquant CT → FT (décision à valider, R1)** : le repère contient le code du type
(`…CT01` → `…FT01`). Changer le type d'un équipement change donc **tous** ses noms et le repère, que la
décision impose de préserver. Tant qu'un mécanisme de repère conservé n'est pas validé, OGIAS ne convertit
**aucun** équipement CT : un projet existant garde CT dans son référentiel figé ; l'adoption signale la
conversion comme « à valider ». Les nouveaux projets n'ont plus CT.

## 4. Points `A_VERIFIER` encore ouverts

A1 (renommages V1 et 49 ajouts, non appliqués), A2 (`FT.ES_DEB` en « Option »), A3 (paramètre 0/1 de
`ET_SENS`, à créer en L4), A5 (106 textes `logique` de signaux, non modifiés), A7 (types de modèles A--P, PV,
CI, SC), A8 (53 alertes source à réévaluer), A10, A11. R1 ci-dessus.

## 5. Fichiers impactés

`genvar/referentiel_depot.py`, `genvar/referentiel_excel.py`, `genvar/session.py`, `genvar/modele.py`,
`genvar/catalogue.py`, `genvar/data/catalogue_defaut.json`, `genvar/data/referentiel_modeles.json`,
`sorep_web/serveur.py`, `sorep_web/static/app.js`, tests dédiés. Aucun exporteur industriel n'est modifié.
