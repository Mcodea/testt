# Modèle de données des E/S V1 — proposition soumise à validation

Établi le 10/11/2026 (Claude), suite à la décision utilisateur consignée dans
`docs/INSTRUCTIONS_EN_COURS.md`. **Aucune modification ni migration n'est appliquée
tant que l'utilisateur n'a pas validé ce document.** Chiffres issus de
`outils/correspondance_es_v1.py` (test : `tests/test_correspondance_es_v1.py`).

## 1. Constat : le principe demandé existe déjà dans OGIAS

Un signal du catalogue porte deux objets distincts et associés :

| Objet | Nom généré | Adressage | Exemple (vanne MV01) |
| --- | --- | --- | --- |
| E/S physique | `<nature>_<repère>_<suffixe point>` (`modele.suffixe_point` : organe + code) | `adresses_es` : voie Schneider %I/%Q/%IW, voie S4W | `ET_..MV01_FDC_OUV` |
| Information fonctionnelle | `<famille>_<repère>_<code>` | `adresses` : %MW de la table d'échange, **uniquement** pour TS/TM/TC/TR/RTR/CP | `TS_..MV01_OUV` |

- Une E/S sans supervision est de famille `ES` : affectation matérielle seule, **aucun %MW**.
- Les états calculés sont des signaux `Interne` produits par les règles (`regles`).
- Les règles de cohérence des vannes existent : MV-05 (deux fins de course :
  discordance au-delà de `T_DISC`, position intermédiaire après `T_TRANSIT`),
  EV-01, SV-01, XV-01 (discordance des retours de position).

Les règles 1 à 4 et 6 de la décision sont donc déjà respectées. Aucune duplication
n'est à créer : le classeur V1 décrit le même modèle avec des codes harmonisés.

## 2. Modèle proposé (évolution minimale, compatible)

1. **Signal** (inchangé) = une E/S physique et/ou une information fonctionnelle.
2. Ajout d'un champ **`code_es`** (suffixe physique explicite) quand il ne se déduit
   pas de `organe` + `code` (ex. TC `OUV` piloté par ST `CMD_OUV`). Absent = règle actuelle.
3. Ajout d'un champ **`ident_v1`** (« Identifiant » du classeur, ex. `AB.ET.NIV_B`)
   pour tracer chaque E/S jusqu'à la bibliothèque.
4. Ajout dans le référentiel d'une table **`alias`** : `(type, ancienne clé
   FAMILLE_CODE) → nouvelle clé`, versionnée, utilisée par la migration et par
   l'import des projets existants (rapprochement « preuve »).
5. Les adresses restent indexées par la clé du signal ; l'alias garantit qu'elles
   suivent le renommage sans être recalculées.

## 3. Ce que change la bibliothèque V1

| Catégorie | Nombre | Effet |
| --- | ---: | --- |
| E/S identiques (physique et fonctionnel) | 86 | aucun |
| Renommage du **nom physique seul** | 30 | ex. `ST_..EV01_OUV` → `ST_..EV01_CMD_OUV`, `ET_..CU01_PB` → `ET_..CU01_NIV_B` ; TS/TC inchangés |
| Renommage **physique et fonctionnel** | 28 | ex. `TS_..GA01_INTR` → `TS_..GA01_INTRUS`, `TM_..AR01_TEMP` → `TM_..AR01_TMP`, `TS_..LS01_H` → `TS_..LS01_NIV_H` |
| E/S ajoutées (types CG, UV, FI, AB, CE, DG ; FV, VV, OU ; variantes) | 49 | nouvelles E/S, uniquement pour les équipements qui les utilisent |
| Références de règles à mettre à jour | 21 (19 règles) | via la table d'alias, sans référence cassée |

## 4. Conséquences

- **Projets existants** : aucune modification. Ils gardent leur révision figée.
  L'adoption de la nouvelle révision est une action explicite, avec aperçu des
  renommages, sauvegarde préalable et retour arrière. Par défaut, l'adoption
  **conserve les anciens noms fonctionnels** (TS/TM/TC/TR) et toutes les adresses
  (%MW, %I/%Q/%IW, voies S4W) ; seuls les noms physiques peuvent suivre la V1.
  Les anciens repères restent consultables.
- **Listes d'E/S** : nouveaux projets avec les 58 noms physiques V1 et les
  49 ajouts ; colonnes Identifiant V1, signal électrique et sens par défaut.
- **Variables / table d'échange** : **aucun %MW supplémentaire** ; même nombre de
  variables pour les 144 E/S existantes ; adresses inchangées après adoption.
- **Schneider (XSY/SCY)** : noms et commentaires des E/S renommées dans les
  nouveaux projets ; adresses inchangées ; contrôle 32 caractères maintenu.
- **SOFREL S4W** : voies et modules inchangés ; aucune adresse S4W inventée ;
  correspondances « à confirmer » conservées.
- **TOPKAPI** : les 28 renommages fonctionnels changent les mnémoniques
  **des nouveaux projets seulement** ; un projet existant qui les adopterait
  devrait reprendre ses synoptiques : c'est pourquoi l'adoption les conserve par défaut.
- **Jeux de référence** : régénérés pour les nouveaux projets uniquement, avec
  justification ligne à ligne ; les jeux des projets existants restent inchangés.

## 5. Points soumis à validation

1. Champs `code_es`, `ident_v1` et table `alias` (§ 2).
2. Adoption par défaut : noms fonctionnels anciens conservés, noms physiques V1.
3. Vannes : garder MV-05 / EV-01 / SV-01 / XV-01 tels quels (temporisations
   `T_DISC` et `T_TRANSIT` saisies par l'automaticien, aucune valeur inventée),
   et les étendre aux nouveaux types FV et VV si leurs fins de course le permettent.
