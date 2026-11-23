# Brouillon A1 : renommages approuvés

Généré par `outils/brouillon_a1.py` : ne pas modifier à la main. **Candidat non publié** : le référentiel livré (`genvar/data/`) est inchangé, aucun ajout n'est appliqué, aucun ouvrage n'est touché.

- Clés de signaux renommées dans le candidat : **37** (pour les 38 renommages approuvés sur 57 ; refusés : 19).
- Ajouts : **49 non appliqués** (aucune réponse de l'utilisateur).
- Contrôles du dépôt de référentiel : 0 erreur(s), 19 alerte(s) ; 0 clé(s) en double.

## Renommages appliqués

| Type | Nature | Clé actuelle → nouvelle | Nom physique après renommage (exemple) |
| --- | --- | --- | --- |
| AR | EA | `TM_TEMP` → `TM_TMP` | `EA_SR02AR01_TMP` |
| AR | ET | `TS_ISOL` → `TS_DEF_ISOL` | `ET_SR02AR01_DEF_ISOL` |
| AR | ET | `TS_MQ24` → `TS_MQ_24V` | `ET_SR02AR01_MQ_24V` |
| AR | ET | `TS_MQU` → `TS_MQ_U` | `ET_SR02AR01_MQ_U` |
| AR | ET | `TS_PARAF` → `TS_DEF_PARAF` | `ET_SR02AR01_DEF_PARAF` |
| AR | ET | `TS_VENTIL` → `TS_DEF_VENT` | `ET_SR02AR01_DEF_VENT` |
| CU | ET | `ES_PB` → `ES_NIV_B` | `ET_SR02CU01_NIV_B` |
| CU | ET | `ES_PH` → `ES_NIV_H` | `ET_SR02CU01_NIV_H` |
| CU | ET | `ES_PTB` → `ES_NIV_TB` | `ET_SR02CU01_NIV_TB` |
| CU | ET | `ES_PTH` → `ES_NIV_TH` | `ET_SR02CU01_NIV_TH` |
| CU | ET | `ES_TP` → `ES_NIV_TP` | `ET_SR02CU01_NIV_TP` |
| EL | ET | `TS_DALIM` → `TS_DEF_ALIM` | `ET_SR02EL01_DEF_ALIM` |
| FT | ET | `ES_DEF_EXT` → `ES_DEF` | `ET_SR02FT01_DEF` |
| IV | ET | `TS_POSN` → `TS_POS_RES` | `ET_SR02IV01_POS_RES` |
| IV | ET | `TS_POSS` → `TS_POS_SEC` | `ET_SR02IV01_POS_SEC` |
| LS | ET | `TS_ARP` → `TS_NIV_ARP` | `ET_SR02LS01_NIV_ARP` |
| LS | ET | `TS_H` → `TS_NIV_H` | `ET_SR02LS01_NIV_H` |
| LS | ET | `TS_MAP1` → `TS_NIV_MAP1` | `ET_SR02LS01_NIV_MAP1` |
| LS | ET | `TS_MAP2` → `TS_NIV_MAP2` | `ET_SR02LS01_NIV_MAP2` |
| LS | ET | `TS_TB` → `TS_NIV_TB` | `ET_SR02LS01_NIV_TB` |
| LS | ET | `TS_TH` → `TS_NIV_TH` | `ET_SR02LS01_NIV_TH` |
| OD | ET | `TS_SBAT` → `TS_SUR_BAT` | `ET_SR02OD01_SUR_BAT` |
| PD | EA | `TM_TAUX` → `TM_TAU` | `EA_SR02PD01_TAU` |
| PM | EA | `ES_FREQ` → `ES_FRQ` | `EA_SR02PM01_FRQ` |
| PM | ET | `ES_DEFTH` → `ES_DEF_TH` | `ET_SR02PM01_DEF_TH` |
| PM | ET | `ES_DEFVAR` → `ES_DEF_VAR` | `ET_SR02PM01_DEF_VAR` |
| PM | SA | `ES_CONS_FREQ` → `ES_CONS_FRQ` | `SA_SR02PM01_CONS_FRQ` |
| RP | EA | `TM_PAM` → `TM_PRE_AM` | `EA_SR02RP01_PRE_AM` |
| RP | EA | `TM_PAV` → `TM_PRE_AV` | `EA_SR02RP01_PRE_AV` |
| SP | ET | `TS_MQEAU` → `TS_MQ_EAU` | `ET_SR02SP01_MQ_EAU` |
| SV | ET | `TS_DEFCPL` → `TS_DEF_CPL` | `ET_SR02SV01_DEF_CPL` |
| TR | ET | `TS_DEFTEMP` → `TS_DEF_TMP` | `ET_SR02TR01_DEF_TMP` |
| TR | ET | `TS_STEN` → `TS_PRES_U` | `ET_SR02TR01_PRES_U` |
| TT | EA | `ES_TEMP` → `ES_TMP` | `EA_SR02TT01_TMP` |
| VE | ET | `TS_MAGV` → `TS_MA_GV` | `ET_SR02VE01_MA_GV` |
| VE | ET | `TS_MAPV` → `TS_MA_PV` | `ET_SR02VE01_MA_PV` |
| XV | ET | `TS_DEFCPL` → `TS_DEF_CPL` | `ET_SR02XV01_DEF_CPL` |

## Renommages refusés (conservés tels quels)

`EV.ST.FER`, `EV.ST.OUV`, `GA.ET.INTR`, `GE.ST.AR`, `GE.ST.MA`, `KM.ST.AR`, `KM.ST.MA`, `MV.ST.FER`, `MV.ST.OUV`, `PD.ST.AR`, `PD.ST.MA`, `SP.ST.AR`, `SP.ST.MA`, `SV.ST.AR`, `SV.ST.FER`, `SV.ST.OUV`, `XV.ST.AR`, `XV.ST.FER`, `XV.ST.OUV`

## Noms physiques qui restent différents de la bibliothèque

Le renommage change la clé fonctionnelle ; le nom de l'E/S physique garde son suffixe explicite (`suffixe_es`, décision D4). La bibliothèque V1 proposait un autre suffixe : à confirmer.

| Renommage | Suffixe physique du candidat | Suffixe de la bibliothèque |
| --- | --- | --- |
| `PM.SA.CONS_FREQ` | `FREQ` | `CONS_FRQ` |

## À examiner

- PD.SA.TAUX : le code physique proposé CONS_TAU diffère du code fonctionnel TAU (TR_TAU / RTR_TAU) ; les rapprocher exigerait un `suffixe_es`, que la décision D4 réserve à 5 collisions de clé : non appliqué, décision à prendre.

## Effet sur les ouvrages

Chaque renommage est déclaré dans les **correspondances** du référentiel : à l'adoption d'une révision par un ouvrage existant (action volontaire, ligne à ligne, avec sauvegarde), adresses %MW, voies et commentaires sont reportés de l'ancienne clé vers la nouvelle (tests/test_brouillon_a1.py). Les nouveaux ouvrages utilisent directement les nouveaux codes.
