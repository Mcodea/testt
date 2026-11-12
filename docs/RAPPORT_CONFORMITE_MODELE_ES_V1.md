# Rapport de conformité — modèle des E/S V1 face aux décisions du 10/11/2026

Établi par Claude après examen du code de `release/1.0`. **Aucun code, aucune donnée et aucune bibliothèque
n'ont été modifiés pour ce rapport.** Chiffres recalculés avec `outils/correspondance_es_v1.py`, le catalogue
livré et ses règles, en appliquant la nomenclature validée : même suffixe quand l'E/S physique et
l'information fonctionnelle décrivent la même chose.

## 0. Ce que fait OGIAS aujourd'hui (vérifié dans le code)

- Un signal est identifié par `TYPE.FAMILLE_CODE` (`referentiel_excel.id_signal`), unique par type. Les
  adresses d'un équipement sont indexées par cette clé : `adresses` (%MW) et `adresses_es` (%I/%Q/%IW, voies).
- Nom physique : `<nature>_<repère>_<suffixe_point(code, organe)>` (`modele.py`). L'organe ne sert que sur
  une ET : `FDC` + `OUV` → `FDC_OUV` ; `MA` + `MA` → `MA` ; `DEF` + `DEFTH` → `DEFTH`.
- Nom fonctionnel : `<famille>_<repère>_<code>`. Famille `ES` = E/S purement physique.
- **Deux montages coexistent**, tous deux conformes au principe de séparation :
  1. *signal unique* (EV, SV, XV, CL, DJ, IS, AR, LS…) : un signal TS de nature ET porte l'E/S et
     l'information (`ET_EV01_FDC_OUV` + `TS_EV01_OUV`) ;
  2. *E/S + jumeau par règle* (MV, HV, PM, CU, LT, PT, TT, AT, FT) : une E/S `ES_…` et une information
     interne produite par une règle d'une seule entrée (MV-01 : `ES_FDC_OUV` → `TS_OUV`, « recopie directe »).
- Projets protégés : chaque ouvrage fige `catalogue_snapshot` / `modeles_snapshot` ; ses noms ne changent
  pas tant qu'il n'adopte pas une nouvelle révision.
- `Session.adopter_referentiel` : acte explicite, mais **en bloc**, sans sauvegarde dédiée, sans retour
  arrière, sans choix ligne à ligne et **sans correspondance des codes renommés** : l'adresse d'un code
  renommé reste attachée à l'ancienne clé et n'est plus utilisée.
- Aucun mécanisme d'alias de signaux n'existe (les « ALIASES » de `liste_es.py` / `inbound` sont des
  synonymes d'en-têtes de colonnes). Un renommage de code = suppression + création.

## 1. Tableau de conformité

| Fonctionnalité ou règle | Existe déjà | Modification nécessaire | Justification |
| --- | --- | --- | --- |
| Séparation E/S physique / information fonctionnelle | Oui | Non | Deux montages existants, tous deux séparent le physique et le fonctionnel. |
| Pas de %MW supplémentaire par E/S | Oui | Non | %MW seulement pour TS/TM/TC/TR/RTR/CP (`modele.plan_adresses`). |
| E/S purement physique possible | Oui | Non | Famille `ES`. |
| Information calculée sur plusieurs signaux | Oui | Non | Règles à plusieurs entrées (MV-05, MV-06…). |
| Même suffixe pour la même information (§ 1) | Partiel | **Oui** | 9 signaux à organe `FDC` ; 30 E/S à jumeau dont le code diffère (`FDC_OUV`/`TS_OUV`, `CMD_MA`/`TC_MA`, `PB`/`TS_B`…). |
| Champ de nommage physique (§ 2) | Non | **Oui, limité à 5 signaux** | Cas concret de collision de clé interne, voir § 2.2. |
| Traçabilité de l'origine, `ident_v1` (§ 3) | Oui | **Non** | Équipement (`ident` stable) → modèle → signal `TYPE.FAMILLE_CODE` → règle (`propose`), dans le référentiel figé de l'ouvrage. Seul un renommage de code casse ce lien : rôle des correspondances (§ 2.3). |
| Correspondance ancien / nouveau code (§ 4) | Non | **Oui** | Aucun mécanisme existant ; indispensable pour conserver les adresses à l'adoption. |
| Adoption facultative, présentée avant validation (§ 6) | Partiel | **Oui** | Aperçu des écarts par type existe ; manquent choix ligne à ligne, confirmation de chaque renommage, sauvegarde, retour arrière. |
| Conservation des adresses à l'adoption | Partiel | **Oui** | Conservées pour les codes inchangés ; inutilisées pour un code renommé. |
| Référentiel modifiable depuis l'interface (§ 5) | Oui | Partiel | Types, modèles, lignes, signaux, règles : création, modification, suppression, validation ; brouillon → validation → publication ; révisions, restauration, comparaison ; import/export Excel. |
| Archiver / désactiver | Partiel | Oui (petit) | Signal : statut « Écarté ». Modèle, type : pas d'archivage. |
| Bloquer la suppression d'un élément utilisé | Partiel | Oui (petit) | Bloquée si une règle l'utilise ; pas si un projet enregistré l'utilise (`ouvrages_utilisant` existe, non consulté). |
| Dupliquer un modèle | Non | Oui (petit) | Absent. |
| Remplacer un modèle ou un signal | Non | Oui | Reposera sur les correspondances (§ 2.3). |
| Identifiant interne stable | Oui | Non | Lignes : 8 caractères ; signaux : `TYPE.FAMILLE_CODE` ; équipements : `ident`. |
| Source de référence unique | Oui | Non | Dépôt `referentiel_depot` ; lexique et dictionnaire (ajoutés le 10/11) y sont intégrés, sans fichier parallèle. |
| Règles MV-05, EV-01, SV-01, XV-01 | Oui | **Non** | Avec la solution du § 2.2, aucune de leurs références ne change ; `T_DISC`, `T_TRANSIT` restent paramétrables, aucune valeur inventée. |
| Extension FV / VV | — | **Non, à ce stade** | FV et VV n'ont **aucune E/S** dans le catalogue livré ; elles n'existent que dans les 49 ajouts V1. Cas d'application à présenter après leur intégration. |

## 2. Modifications strictement nécessaires

### 2.1 Fins de course à organe `FDC` (montage « signal unique ») — données seulement

- **Actuel** : `ET_EV01_FDC_OUV` / `TS_EV01_OUV` pour 9 signaux (CL, DJ, EV, IS, SV, XV).
- **Attendu** : `ET_EV01_OUV` / `TS_EV01_OUV`.
- **Mécanisme** : dans la **nouvelle révision**, retirer l'organe `FDC` de ces 9 signaux. `suffixe_point` n'est
  pas modifié : les projets existants gardent leurs noms. Aucune clé ne change, aucune règle n'est touchée.
- **Conséquence** : le libellé de l'E/S perd le préfixe automatique « Fin de course » (`information_point`)
  et reprend celui de l'information (« Ouverte »), sauf à le compléter.
- **Test** : EV neuf → `ET_…_OUV` / `TS_…_OUV` ; projet existant avec référentiel figé → noms identiques.

### 2.2 Champ de nommage physique — indispensable pour 5 signaux

**Exemple concret (MV01)** : la fin de course `ET_MV01_OUV` (signal `ES_FDC_OUV`) et la commande
`ST_MV01_OUV` (signal `ES_OUV`) sont deux E/S purement physiques du même type. Pour qu'elles portent toutes
deux le suffixe `OUV`, leur clé interne deviendrait `ES_OUV` deux fois : **impossible**, la clé est unique
par type. Même situation pour MV `EA POS` / `SA CONS_POS`, PM `ET MA` / `ST CMD_MA`, PM `EA FREQ` / `SA CONS_FREQ`.

- **Solution minimale** : un champ facultatif `suffixe_es` (vide par défaut), qui remplace le suffixe du
  **nom physique** sans changer le code interne. Renseigné sur 5 signaux seulement : MV `FDC_OUV` → `OUV`,
  MV `FDC_FER` → `FER`, MV `CONS_POS` → `POS`, PM `CMD_MA` → `MA`, PM `CONS_FREQ` → `FRQ`.
- **Avantages** : aucune clé ni règle modifiée (MV-01 à MV-11 intactes), aucune variable ni adresse créée ;
  un projet existant (référentiel figé sans ce champ) garde ses noms.
- **Alternative écartée** : inclure la nature dans la clé des E/S physiques. Plus invasif : clés des adresses,
  références de toutes les règles `ES_…`, identifiants Excel et référentiels figés des ouvrages.
- **Fichiers** : `modele.py` (2 appels de `suffixe_point`), `catalogue.py` (contrôle : format, unicité du
  nom physique par équipement), `referentiel_excel.py` (colonne).
- **Tests** : MV neuf → `ET_…_OUV`, `ST_…_OUV`, `TS_…_OUV`, `TC_…_OUV` ; deux E/S d'un équipement avec le
  même nom physique → erreur ; ouvrage existant → noms identiques à l'octet.

### 2.3 Correspondances anciennes / nouvelles références (§ 4)

- **Actuel** : aucune ; un code renommé perd ses adresses à l'adoption.
- **Attendu** : dans le référentiel (même dépôt, même révision), une liste `correspondances`
  `{type, ancienne clé, nouvelle clé}`. Refus si une ancienne clé est citée deux fois ou si deux anciennes
  visent la même nouvelle (ambiguïté). Aucune variable, aucune adresse créée.
- **Fichiers** : `referentiel_depot.py`, `referentiel_excel.py`, `session.py` (adoption uniquement).
- **Risque** : nul tant qu'aucune adoption n'est confirmée.
- **Tests** : correspondance ambiguë refusée ; code renommé adopté → mêmes %MW, même voie physique,
  même point TOPKAPI ; ancien nom consultable.

### 2.4 Adoption contrôlée d'une révision (§ 6)

- **Actuel** : `adopter_referentiel` remplace tout le référentiel figé d'un coup.
- **Attendu** :
  1. aperçu ligne à ligne : ajouts, retraits, renommages physiques, renommages fonctionnels, règles ;
  2. chaque renommage, physique **et** fonctionnel, décoché par défaut, confirmé explicitement ;
  3. sauvegarde horodatée du projet avant application (mécanisme `.bak` de `projets.py` réutilisé) et
     retour arrière en un geste ;
  4. adresses (%MW, %I/%Q/%IW, voies S4W) et correspondances TOPKAPI reportées par les correspondances,
     jamais recalculées ; un renommage refusé garde l'ancien code.
- **Fichiers** : `session.py`, `sorep_web/serveur.py`, écran d'adoption.
- **Tests** : « adoption refusée → fichier identique à l'octet » ; « adoption puis retour arrière → fichier
  identique » ; « renommage non confirmé → ancien nom et adresse conservés ».

### 2.5 Compléments de gestion du référentiel (§ 5)

Dupliquer un modèle ; archiver un modèle ou un type ; bloquer la suppression d'un élément utilisé par un
projet enregistré en proposant l'archivage ; remplacer = déclarer une correspondance (§ 2.3).

## 3. Les chiffres de la proposition, recalculés

| Catégorie | Proposition initiale | Avec la nomenclature validée |
| --- | ---: | ---: |
| E/S inchangées (sur 144) | 86 | **90** |
| Renommage du nom physique seul | 30 | **16** : 9 organes `FDC` retirés (§ 2.1), 4 par `suffixe_es` (MV `FDC_OUV`, `FDC_FER`, `CONS_POS`, PM `CMD_MA`), 3 codes renommés sans collision (HV `FDC_OUV`, `FDC_FER` → `OUV`, `FER` ; PM `CMD_AR` → `AR`) |
| Renommage physique et fonctionnel | 28 | **38** : les 28 initiaux + 10 E/S dont le jumeau doit suivre (`PB`/`TS_B` → `NIV_B`/`TS_NIV_B` ×5 pour CU, PM `DEFTH`, `DEFVAR`, `FREQ`, `CONS_FREQ`, TT `TEMP`) |
| Renommages V1 écartés | — | **3** : CT `VOL` (≠ impulsion), FT `IMP` / `CP_VOL` (≠), FT `DEF_EXT` (garderait `TS_DEF` en double avec FT-02) |
| Préfixes V1 `CMD_` / `CONS_` écartés | — | EV, GE, KM, PD, MV (commandes) et PD (consigne) : même information que la TC / TR |
| E/S ajoutées | 49 | **49**, intégrées avec la même nomenclature |
| Clés renommées | — | **50** (28 + 22) |
| Références de règles à mettre à jour | 21 (19 règles) | **34 (19 règles)** ; **aucune** dans MV-05, EV-01, SV-01, XV-01 |

Total : 16 + 38 = **54 E/S modifiées**, 90 inchangées (dont les 3 renommages V1 écartés). Le 5ᵉ signal
à `suffixe_es` (PM `CONS_FREQ` → `FRQ`) est compté parmi les 38, car son jumeau `TR_FREQ` devient `TR_FRQ`.
Ces chiffres seront reproduits par un outil de contrôle avant toute application ; ils restent à approuver.

## 4. Ordre proposé après validation

1. Correspondances (§ 2.3) et adoption contrôlée (§ 2.4), avec leurs tests de non-régression, avant toute
   modification de données, pour que l'adoption soit sûre.
2. `suffixe_es` (§ 2.2), avec ses contrôles et tests.
3. Nouvelle révision du référentiel **en brouillon** : § 2.1, renommages, 49 ajouts, correspondances
   déclarées ; aperçu des différences soumis à l'utilisateur avant publication.
4. Compléments du § 2.5.
5. Extension des règles de cohérence à FV / VV : présentation des cas après intégration de leurs E/S.

## 5. Décisions demandées

1. Champ `suffixe_es` limité aux 5 signaux du § 2.2 : oui / non.
2. Renommages V1 écartés (CT, FT `IMP`, FT `DEF_EXT`) : confirmés.
3. Libellé des fins de course sans préfixe automatique « Fin de course » : accepté, ou libellés à compléter.
4. Ordre du § 4.
