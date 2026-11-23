# Aperçu A1 : renommages et ajouts à approuver

Document généré par `outils/apercu_a1.py` (ne pas modifier à la main). **Rien n'est appliqué** : ni le référentiel livré, ni aucun ouvrage. Les ouvrages existants gardent leur référentiel figé quoi que vous décidiez ; ils n'adoptent une révision que par l'action volontaire « Examiner et appliquer… », ligne à ligne, avec sauvegarde.

## 1. En bref

- **57 renommages** de codes d'E/S physiques existantes (le rapport du 10/11 en annonçait 54 : le recalcul sur le catalogue actuel en trouve 57 ; l'écart est à valider avec vous).
- **49 ajouts** d'E/S absentes du catalogue, dont **22** dans 6 types à créer (AB, CE, CG, DG, FI, UV).
- 86 E/S restent inchangées (aucune décision).

**Comment répondre.** Dans le classeur `docs/APERCU_A1_A_APPROUVER.xlsx`, choisissez « Approuvé », « Refusé » ou « À discuter » à chaque ligne (une liste déroulante est prévue), ou dites simplement ici « tout approuvé », « renommages approuvés, ajouts refusés », ou « approuvé sauf le type X ». Je prépare alors un **brouillon** de référentiel avec les seules lignes approuvées, avec correspondances d'adresses, contrôles et tests : il ne sera publié qu'après votre dernier accord.

## 2. Ce que change un renommage

Le nom d'une E/S physique se construit `NATURE_repère_suffixe` ; l'information de télétransmission `FAMILLE_repère_code`. Un renommage change le code, donc ces noms, **pour les nouveaux ouvrages seulement**. Pour un ouvrage existant, la table de correspondance rattache l'ancienne clé à la nouvelle : adresses %MW, voies et repères sont conservés, jamais recalculés. Les exemples ci-dessous utilisent le repère d'essai de la bibliothèque.

## 3. Renommages

| Type | Nature | Variante | Code actuel → proposé | Nom physique actuel → proposé | Information actuelle → proposée | Décision |
| --- | --- | --- | --- | --- | --- | --- |
| AR | EA | Ventilation | `TEMP` → `TMP` | `EA_SR02AR01_TEMP` → `EA_SR02AR01_TMP` | `TM_SR02AR01_TEMP` → `TM_SR02AR01_TMP` | ☐ |
| AR | ET | Base | `ISOL` → `DEF_ISOL` | `ET_SR02AR01_ISOL` → `ET_SR02AR01_DEF_ISOL` | `TS_SR02AR01_ISOL` → `TS_SR02AR01_DEF_ISOL` | ☐ |
| AR | ET | Base | `MQ24` → `MQ_24V` | `ET_SR02AR01_MQ24` → `ET_SR02AR01_MQ_24V` | `TS_SR02AR01_MQ24` → `TS_SR02AR01_MQ_24V` | ☐ |
| AR | ET | Base | `MQU` → `MQ_U` | `ET_SR02AR01_MQU` → `ET_SR02AR01_MQ_U` | `TS_SR02AR01_MQU` → `TS_SR02AR01_MQ_U` | ☐ |
| AR | ET | Parafoudre | `PARAF` → `DEF_PARAF` | `ET_SR02AR01_PARAF` → `ET_SR02AR01_DEF_PARAF` | `TS_SR02AR01_PARAF` → `TS_SR02AR01_DEF_PARAF` | ☐ |
| AR | ET | Ventilation | `VENTIL` → `DEF_VENT` | `ET_SR02AR01_VENTIL` → `ET_SR02AR01_DEF_VENT` | `TS_SR02AR01_VENTIL` → `TS_SR02AR01_DEF_VENT` | ☐ |
| CU | ET | Contacts de niveau | `PB` → `NIV_B` | `ET_SR02CU01_PB` → `ET_SR02CU01_NIV_B` | `ES_SR02CU01_PB` → information produite par les règles du type | ☐ |
| CU | ET | Contacts de niveau | `PH` → `NIV_H` | `ET_SR02CU01_PH` → `ET_SR02CU01_NIV_H` | `ES_SR02CU01_PH` → information produite par les règles du type | ☐ |
| CU | ET | Contacts de niveau | `PTB` → `NIV_TB` | `ET_SR02CU01_PTB` → `ET_SR02CU01_NIV_TB` | `ES_SR02CU01_PTB` → information produite par les règles du type | ☐ |
| CU | ET | Contacts de niveau | `PTH` → `NIV_TH` | `ET_SR02CU01_PTH` → `ET_SR02CU01_NIV_TH` | `ES_SR02CU01_PTH` → information produite par les règles du type | ☐ |
| CU | ET | Trop-plein | `TP` → `NIV_TP` | `ET_SR02CU01_TP` → `ET_SR02CU01_NIV_TP` | `ES_SR02CU01_TP` → information produite par les règles du type | ☐ |
| EL | ET | Base | `DALIM` → `DEF_ALIM` | `ET_SR02EL01_DALIM` → `ET_SR02EL01_DEF_ALIM` | `TS_SR02EL01_DALIM` → `TS_SR02EL01_DEF_ALIM` | ☐ |
| EV | ST | Télécommandée | `FER` → `CMD_FER` | `ST_SR02EV01_FER` → `ST_SR02EV01_CMD_FER` | `TC_SR02EV01_FER` → `TC_SR02EV01_FER` | ☐ |
| EV | ST | Télécommandée | `OUV` → `CMD_OUV` | `ST_SR02EV01_OUV` → `ST_SR02EV01_CMD_OUV` | `TC_SR02EV01_OUV` → `TC_SR02EV01_OUV` | ☐ |
| FT | ET | Contact défaut TOR | `DEF_EXT` → `DEF` | `ET_SR02FT01_DEF_EXT` → `ET_SR02FT01_DEF` | `ES_SR02FT01_DEF_EXT` → information produite par les règles du type | ☐ |
| GA | ET | Base | `INTR` → `INTRUS` | `ET_SR02GA01_INTR` → `ET_SR02GA01_INTRUS` | `TS_SR02GA01_INTR` → `TS_SR02GA01_INTRUS` | ☐ |
| GE | ST | Télécommandé | `AR` → `CMD_AR` | `ST_SR02GE01_AR` → `ST_SR02GE01_CMD_AR` | `TC_SR02GE01_AR` → `TC_SR02GE01_AR` | ☐ |
| GE | ST | Télécommandé | `MA` → `CMD_MA` | `ST_SR02GE01_MA` → `ST_SR02GE01_CMD_MA` | `TC_SR02GE01_MA` → `TC_SR02GE01_MA` | ☐ |
| IV | ET | Base | `POSN` → `POS_RES` | `ET_SR02IV01_POSN` → `ET_SR02IV01_POS_RES` | `TS_SR02IV01_POSN` → `TS_SR02IV01_POS_RES` | ☐ |
| IV | ET | Base | `POSS` → `POS_SEC` | `ET_SR02IV01_POSS` → `ET_SR02IV01_POS_SEC` | `TS_SR02IV01_POSS` → `TS_SR02IV01_POS_SEC` | ☐ |
| KM | ST | Télécommandé | `AR` → `CMD_AR` | `ST_SR02KM01_AR` → `ST_SR02KM01_CMD_AR` | `TC_SR02KM01_AR` → `TC_SR02KM01_AR` | ☐ |
| KM | ST | Télécommandé | `MA` → `CMD_MA` | `ST_SR02KM01_MA` → `ST_SR02KM01_CMD_MA` | `TC_SR02KM01_MA` → `TC_SR02KM01_MA` | ☐ |
| LS | ET | Base | `ARP` → `NIV_ARP` | `ET_SR02LS01_ARP` → `ET_SR02LS01_NIV_ARP` | `TS_SR02LS01_ARP` → `TS_SR02LS01_NIV_ARP` | ☐ |
| LS | ET | 3 poires | `H` → `NIV_H` | `ET_SR02LS01_H` → `ET_SR02LS01_NIV_H` | `TS_SR02LS01_H` → `TS_SR02LS01_NIV_H` | ☐ |
| LS | ET | Base | `MAP1` → `NIV_MAP1` | `ET_SR02LS01_MAP1` → `ET_SR02LS01_NIV_MAP1` | `TS_SR02LS01_MAP1` → `TS_SR02LS01_NIV_MAP1` | ☐ |
| LS | ET | 5 poires | `MAP2` → `NIV_MAP2` | `ET_SR02LS01_MAP2` → `ET_SR02LS01_NIV_MAP2` | `TS_SR02LS01_MAP2` → `TS_SR02LS01_NIV_MAP2` | ☐ |
| LS | ET | 5 poires | `TB` → `NIV_TB` | `ET_SR02LS01_TB` → `ET_SR02LS01_NIV_TB` | `TS_SR02LS01_TB` → `TS_SR02LS01_NIV_TB` | ☐ |
| LS | ET | 5 poires | `TH` → `NIV_TH` | `ET_SR02LS01_TH` → `ET_SR02LS01_NIV_TH` | `TS_SR02LS01_TH` → `TS_SR02LS01_NIV_TH` | ☐ |
| MV | ST | Télécommandée | `FER` → `CMD_FER` | `ST_SR02MV01_FER` → `ST_SR02MV01_CMD_FER` | `ES_SR02MV01_FER` → information produite par les règles du type | ☐ |
| MV | ST | Télécommandée | `OUV` → `CMD_OUV` | `ST_SR02MV01_OUV` → `ST_SR02MV01_CMD_OUV` | `ES_SR02MV01_OUV` → information produite par les règles du type | ☐ |
| OD | ET | Base | `SBAT` → `SUR_BAT` | `ET_SR02OD01_SBAT` → `ET_SR02OD01_SUR_BAT` | `TS_SR02OD01_SBAT` → `TS_SR02OD01_SUR_BAT` | ☐ |
| PD | EA | Base | `TAUX` → `TAU` | `EA_SR02PD01_TAUX` → `EA_SR02PD01_TAU` | `TM_SR02PD01_TAUX` → `TM_SR02PD01_TAU` | ☐ |
| PD | SA | Taux réglable | `TAUX` → `CONS_TAU` | `SA_SR02PD01_TAUX` → `SA_SR02PD01_CONS_TAU` | `TR_SR02PD01_TAUX` → TR_SR02PD01_TAU / RTR_TAU | ☐ |
| PD | ST | Télécommandée | `AR` → `CMD_AR` | `ST_SR02PD01_AR` → `ST_SR02PD01_CMD_AR` | `TC_SR02PD01_AR` → `TC_SR02PD01_AR` | ☐ |
| PD | ST | Télécommandée | `MA` → `CMD_MA` | `ST_SR02PD01_MA` → `ST_SR02PD01_CMD_MA` | `TC_SR02PD01_MA` → `TC_SR02PD01_MA` | ☐ |
| PM | EA | Variateur | `FREQ` → `FRQ` | `EA_SR02PM01_FREQ` → `EA_SR02PM01_FRQ` | `ES_SR02PM01_FREQ` → information produite par les règles du type | ☐ |
| PM | ET | Base | `DEFTH` → `DEF_TH` | `ET_SR02PM01_DEFTH` → `ET_SR02PM01_DEF_TH` | `ES_SR02PM01_DEFTH` → information produite par les règles du type | ☐ |
| PM | ET | Variateur | `DEFVAR` → `DEF_VAR` | `ET_SR02PM01_DEFVAR` → `ET_SR02PM01_DEF_VAR` | `ES_SR02PM01_DEFVAR` → information produite par les règles du type | ☐ |
| PM | SA | Variateur | `CONS_FREQ` → `CONS_FRQ` | `SA_SR02PM01_FREQ` → `SA_SR02PM01_CONS_FRQ` | `ES_SR02PM01_CONS_FREQ` → information produite par les règles du type | ☐ |
| RP | EA | Pression amont | `PAM` → `PRE_AM` | `EA_SR02RP01_PAM` → `EA_SR02RP01_PRE_AM` | `TM_SR02RP01_PAM` → `TM_SR02RP01_PRE_AM` | ☐ |
| RP | EA | Pression aval | `PAV` → `PRE_AV` | `EA_SR02RP01_PAV` → `EA_SR02RP01_PRE_AV` | `TM_SR02RP01_PAV` → `TM_SR02RP01_PRE_AV` | ☐ |
| SP | ET | Base | `MQEAU` → `MQ_EAU` | `ET_SR02SP01_MQEAU` → `ET_SR02SP01_MQ_EAU` | `TS_SR02SP01_MQEAU` → `TS_SR02SP01_MQ_EAU` | ☐ |
| SP | ST | Télécommandée | `AR` → `CMD_AR` | `ST_SR02SP01_AR` → `ST_SR02SP01_CMD_AR` | `TC_SR02SP01_AR` → `TC_SR02SP01_AR` | ☐ |
| SP | ST | Télécommandée | `MA` → `CMD_MA` | `ST_SR02SP01_MA` → `ST_SR02SP01_CMD_MA` | `TC_SR02SP01_MA` → `TC_SR02SP01_MA` | ☐ |
| SV | ET | Complément | `DEFCPL` → `DEF_CPL` | `ET_SR02SV01_DEFCPL` → `ET_SR02SV01_DEF_CPL` | `TS_SR02SV01_DEFCPL` → `TS_SR02SV01_DEF_CPL` | ☐ |
| SV | ST | Télécommandée | `AR` → `CMD_AR` | `ST_SR02SV01_AR` → `ST_SR02SV01_CMD_AR` | `TC_SR02SV01_AR` → `TC_SR02SV01_AR` | ☐ |
| SV | ST | Télécommandée | `FER` → `CMD_FER` | `ST_SR02SV01_FER` → `ST_SR02SV01_CMD_FER` | `TC_SR02SV01_FER` → `TC_SR02SV01_FER` | ☐ |
| SV | ST | Télécommandée | `OUV` → `CMD_OUV` | `ST_SR02SV01_OUV` → `ST_SR02SV01_CMD_OUV` | `TC_SR02SV01_OUV` → `TC_SR02SV01_OUV` | ☐ |
| TR | ET | Base | `DEFTEMP` → `DEF_TMP` | `ET_SR02TR01_DEFTEMP` → `ET_SR02TR01_DEF_TMP` | `TS_SR02TR01_DEFTEMP` → `TS_SR02TR01_DEF_TMP` | ☐ |
| TR | ET | Base | `STEN` → `PRES_U` | `ET_SR02TR01_STEN` → `ET_SR02TR01_PRES_U` | `TS_SR02TR01_STEN` → `TS_SR02TR01_PRES_U` | ☐ |
| TT | EA | Base | `TEMP` → `TMP` | `EA_SR02TT01_TEMP` → `EA_SR02TT01_TMP` | `ES_SR02TT01_TEMP` → information produite par les règles du type | ☐ |
| VE | ET | Deux vitesses | `MAGV` → `MA_GV` | `ET_SR02VE01_MAGV` → `ET_SR02VE01_MA_GV` | `TS_SR02VE01_MAGV` → `TS_SR02VE01_MA_GV` | ☐ |
| VE | ET | Deux vitesses | `MAPV` → `MA_PV` | `ET_SR02VE01_MAPV` → `ET_SR02VE01_MA_PV` | `TS_SR02VE01_MAPV` → `TS_SR02VE01_MA_PV` | ☐ |
| XV | ET | Complément | `DEFCPL` → `DEF_CPL` | `ET_SR02XV01_DEFCPL` → `ET_SR02XV01_DEF_CPL` | `TS_SR02XV01_DEFCPL` → `TS_SR02XV01_DEF_CPL` | ☐ |
| XV | ST | Télécommandée | `AR` → `CMD_AR` | `ST_SR02XV01_AR` → `ST_SR02XV01_CMD_AR` | `TC_SR02XV01_AR` → `TC_SR02XV01_AR` | ☐ |
| XV | ST | Télécommandée | `FER` → `CMD_FER` | `ST_SR02XV01_FER` → `ST_SR02XV01_CMD_FER` | `TC_SR02XV01_FER` → `TC_SR02XV01_FER` | ☐ |
| XV | ST | Télécommandée | `OUV` → `CMD_OUV` | `ST_SR02XV01_OUV` → `ST_SR02XV01_CMD_OUV` | `TC_SR02XV01_OUV` → `TC_SR02XV01_OUV` | ☐ |

Par type : AR 6, CU 5, EL 1, EV 2, FT 1, GA 1, GE 2, IV 2, KM 2, LS 6, MV 2, OD 1, PD 4, PM 4, RP 2, SP 3, SV 4, TR 2, TT 1, VE 2, XV 4.

### Cas particuliers (hors décision A1)

- CT.ET.IMP : type CT supprimé du catalogue (consolidé dans FT, décision de la V2) ; l'E/S correspond à la nouvelle `FT.ES_IMP` (décision R1 sur le repère, déjà documentée dans docs/RAPPORT_ECARTS_V2.md).
- Signal du catalogue `MV.ARR` (index 181) absent de la bibliothèque V1 : conservé tel quel, aucune décision à prendre.

## 4. Ajouts

Les types marqués **(nouveau type)** n'existent pas encore dans le catalogue : les approuver revient aussi à créer le type.

### AB — Ballon anti-bélier (nouveau type)

| Nature | Code | Libellé | Présence | Nom physique (exemple) | Information associée | Décision |
| --- | --- | --- | --- | --- | --- | --- |
| EA | `PRE` | Pression | Par défaut · Base | `EA_SR02AB01_PRE` | `TM_PRE` | ☐ |
| ET | `DEF_COMP` | Défaut compresseur | Option · Compresseur | `ET_SR02AB01_DEF_COMP` | `TS_DEF_COMP` | ☐ |
| ET | `MA_COMP` | Compresseur en marche | Option · Compresseur | `ET_SR02AB01_MA_COMP` | `TS_MA_COMP` | ☐ |
| ET | `NIV_B` | Niveau bas | Option · Base | `ET_SR02AB01_NIV_B` | `TS_NIV_B` | ☐ |
| ET | `NIV_H` | Niveau haut | Option · Base | `ET_SR02AB01_NIV_H` | `TS_NIV_H` | ☐ |

### AL — Alimentation 24 V CC

| Nature | Code | Libellé | Présence | Nom physique (exemple) | Information associée | Décision |
| --- | --- | --- | --- | --- | --- | --- |
| ET | `DEF_SEC` | Défaut alimentation de secours | Option · Redondante | `ET_SR02AL01_DEF_SEC` | `TS_DEF_SEC` | ☐ |

### AR — Armoire électrique

| Nature | Code | Libellé | Présence | Nom physique (exemple) | Information associée | Décision |
| --- | --- | --- | --- | --- | --- | --- |
| ET | `PORTE` | Porte ouverte | Option · Base | `ET_SR02AR01_PORTE` | `TS_PORTE` | ☐ |

### CE — Compteur d'énergie électrique (nouveau type)

| Nature | Code | Libellé | Présence | Nom physique (exemple) | Information associée | Décision |
| --- | --- | --- | --- | --- | --- | --- |
| ET | `IMP` | Impulsions de comptage | Par défaut · Base | `ET_SR02CE01_IMP` | `CP_ENER` | ☐ |

### CG — Chloration gazeuse (nouveau type)

| Nature | Code | Libellé | Présence | Nom physique (exemple) | Information associée | Décision |
| --- | --- | --- | --- | --- | --- | --- |
| ET | `DEF` | Défaut général | Par défaut · Base | `ET_SR02CG01_DEF` | `TS_DEF` | ☐ |
| ET | `FUITE` | Fuite détectée | Obligatoire · Base | `ET_SR02CG01_FUITE` | `TS_FUITE` | ☐ |
| ET | `INV` | Inversion sur réserve | Option · Inverseur | `ET_SR02CG01_INV` | `TS_INV` | ☐ |
| ET | `VIDE` | Réservoir en service vide | Par défaut · Base | `ET_SR02CG01_VIDE` | `TS_VIDE` | ☐ |

### DG — Détecteur de gaz (nouveau type)

| Nature | Code | Libellé | Présence | Nom physique (exemple) | Information associée | Décision |
| --- | --- | --- | --- | --- | --- | --- |
| EA | `VAL` | Valeur de l'analyseur / détecteur | Option · Base | `EA_SR02DG01_VAL` | `TM_VAL` | ☐ |
| ET | `DEF` | Défaut général | Par défaut · Base | `ET_SR02DG01_DEF` | `TS_DEF` | ☐ |
| ET | `SEUIL_1` | Seuil 1 atteint | Par défaut · Base | `ET_SR02DG01_SEUIL_1` | `TS_SEUIL_1` | ☐ |
| ET | `SEUIL_2` | Seuil 2 atteint | Par défaut · Base | `ET_SR02DG01_SEUIL_2` | `TS_SEUIL_2` | ☐ |

### FI — Filtre (nouveau type)

| Nature | Code | Libellé | Présence | Nom physique (exemple) | Information associée | Décision |
| --- | --- | --- | --- | --- | --- | --- |
| EA | `PRE_DIF` | Pression différentielle | Option · Base | `EA_SR02FI01_PRE_DIF` | `TM_PRE_DIF` | ☐ |
| ET | `COLMAT` | Colmatage | Par défaut · Base | `ET_SR02FI01_COLMAT` | `TS_COLMAT` | ☐ |
| ET | `LAVAGE` | Lavage en cours | Option · Lavage automatique | `ET_SR02FI01_LAVAGE` | `TS_LAVAGE` | ☐ |

### FV — Vanne de régulation

| Nature | Code | Libellé | Présence | Nom physique (exemple) | Information associée | Décision |
| --- | --- | --- | --- | --- | --- | --- |
| EA | `POS` | Position | Par défaut · Base | `EA_SR02FV01_POS` | `TM_POS` | ☐ |
| ET | `DEF` | Défaut général | Par défaut · Base | `ET_SR02FV01_DEF` | `TS_DEF` | ☐ |
| ET | `FDC_FER` | Fin de course fermé | Par défaut · Base | `ET_SR02FV01_FDC_FER` | `TS_FER` | ☐ |
| ET | `FDC_OUV` | Fin de course ouvert | Par défaut · Base | `ET_SR02FV01_FDC_OUV` | `TS_OUV` | ☐ |
| ET | `LOC` | Sélecteur en local | Par défaut · Base | `ET_SR02FV01_LOC` | `TS_LOC` | ☐ |
| SA | `CONS_POS` | Consigne de position | Option · Télécommandée | `SA_SR02FV01_CONS_POS` | `TR_POS / RTR_POS` | ☐ |

### LT — Capteur de niveau

| Nature | Code | Libellé | Présence | Nom physique (exemple) | Information associée | Décision |
| --- | --- | --- | --- | --- | --- | --- |
| ET | `NIV_TB` | Niveau très bas | Option · Contact de sécurité | `ET_SR02LT01_NIV_TB` | `TS_NIV_TB` | ☐ |
| ET | `NIV_TH` | Niveau très haut | Option · Contact de sécurité | `ET_SR02LT01_NIV_TH` | `TS_NIV_TH` | ☐ |

### OU — Ouvrage (site)

| Nature | Code | Libellé | Présence | Nom physique (exemple) | Information associée | Décision |
| --- | --- | --- | --- | --- | --- | --- |
| ET | `INTRUS` | Intrusion | Option · Base | `ET_SR02OU01_INTRUS` | `TS_INTRUS` | ☐ |
| ET | `PORTE` | Porte ouverte | Option · Base | `ET_SR02OU01_PORTE` | `TS_PORTE` | ☐ |

### PD — Pompe doseuse

| Nature | Code | Libellé | Présence | Nom physique (exemple) | Information associée | Décision |
| --- | --- | --- | --- | --- | --- | --- |
| ET | `NIV_B` | Niveau bas | Option · Bac de réactif | `ET_SR02PD01_NIV_B` | `TS_NIV_B` | ☐ |
| ET | `NIV_TB` | Niveau très bas | Option · Bac de réactif | `ET_SR02PD01_NIV_TB` | `TS_NIV_TB` | ☐ |

### PM — Pompe

| Nature | Code | Libellé | Présence | Nom physique (exemple) | Information associée | Décision |
| --- | --- | --- | --- | --- | --- | --- |
| ET | `DEF_DEM` | Défaut démarreur progressif | Option · Démarreur progressif | `ET_SR02PM01_DEF_DEM` | `TS_DEF_DEM` | ☐ |
| ET | `DEF_HUM` | Défaut humidité moteur | Option · Pompe immergée | `ET_SR02PM01_DEF_HUM` | `TS_DEF_HUM` | ☐ |
| ET | `DEF_PTC` | Défaut sondes PTC moteur | Option · Pompe immergée | `ET_SR02PM01_DEF_PTC` | `TS_DEF_PTC` | ☐ |
| ST | `CMD_ACQ` | Commande réarmement | Option · Réarmement à distance | `ST_SR02PM01_CMD_ACQ` | `TC_ACQ` | ☐ |

### TT — Capteur de température

| Nature | Code | Libellé | Présence | Nom physique (exemple) | Information associée | Décision |
| --- | --- | --- | --- | --- | --- | --- |
| EA | `TMP` | Température | Option · Sonde PT100 directe | `EA_SR02TT01_TMP` | `TM_TMP` | ☐ |

### UV — Réacteur ultraviolet (nouveau type)

| Nature | Code | Libellé | Présence | Nom physique (exemple) | Information associée | Décision |
| --- | --- | --- | --- | --- | --- | --- |
| EA | `INT_UV` | Intensité UV | Par défaut · Base | `EA_SR02UV01_INT_UV` | `TM_INT_UV` | ☐ |
| ET | `DEF` | Défaut général | Par défaut · Base | `ET_SR02UV01_DEF` | `TS_DEF` | ☐ |
| ET | `DEF_LAMP` | Défaut lampe | Par défaut · Base | `ET_SR02UV01_DEF_LAMP` | `TS_DEF_LAMP` | ☐ |
| ET | `MA` | En marche | Par défaut · Base | `ET_SR02UV01_MA` | `TS_MA` | ☐ |
| ST | `CMD_MA` | Commande marche | Option · Télécommandé | `ST_SR02UV01_CMD_MA` | `TC_MA` | ☐ |

### VV — Variateur de vitesse

| Nature | Code | Libellé | Présence | Nom physique (exemple) | Information associée | Décision |
| --- | --- | --- | --- | --- | --- | --- |
| EA | `FRQ` | Fréquence | Option · Base | `EA_SR02VV01_FRQ` | `TM_FRQ` | ☐ |
| EA | `INT` | Intensité | Option · Base | `EA_SR02VV01_INT` | `TM_INT` | ☐ |
| ET | `DEF` | Défaut général | Par défaut · Base | `ET_SR02VV01_DEF` | `TS_DEF` | ☐ |
| ET | `DISPO` | Disponible / prêt | Par défaut · Base | `ET_SR02VV01_DISPO` | `TS_DISPO` | ☐ |
| ET | `MA` | En marche | Par défaut · Base | `ET_SR02VV01_MA` | `TS_MA` | ☐ |
| SA | `CONS_FRQ` | Consigne de fréquence | Option · Commandé en câblé | `SA_SR02VV01_CONS_FRQ` | `TR_FRQ / RTR_FRQ` | ☐ |
| ST | `CMD_ACQ` | Commande réarmement | Option · Commandé en câblé | `ST_SR02VV01_CMD_ACQ` | `TC_ACQ` | ☐ |
| ST | `CMD_MA` | Commande marche | Option · Commandé en câblé | `ST_SR02VV01_CMD_MA` | `TC_MA` | ☐ |

## 5. Points d'attention

- **54 ou 57 renommages ?** Le rapport du 10/11 disait 54, le recalcul en trouve 57. Je n'ai pas modifié les chiffres pour les faire concorder : la liste de la section 3 fait foi.
- **FV, VV, OU** : ces types n'ont aucune E/S dans le catalogue livré ; leurs E/S ne viennent que de ces ajouts.
- **Rien n'est supposé** pour les caractéristiques constructeur : le tableau reprend la bibliothèque V1 telle quelle.
- **Après votre accord** : brouillon du référentiel, contrôles de cohérence, essais d'adoption sur un ouvrage fictif, puis publication seulement sur votre ordre explicite. Aucun projet réel n'est touché.
