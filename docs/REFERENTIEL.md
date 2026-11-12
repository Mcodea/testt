# Référentiel SOREP livré — 2026-11-05 référentiel V1 (règles fonctionnelles)

51 types · 354 signaux · 51 règles. Document généré par `outils/documenter_referentiel.py` : ne pas modifier à la main.

Lecture : **ES** = E/S physique (ET/ST/EA/SA) ; un signal fonctionnel avec « ← ES_x » est acquis ou commandé par cette E/S. Présence **Règle** : proposé seulement par une règle. ⚙ = logique automate à programmer (générer la variable ne programme pas la fonction).

## Sommaire

- **Hydraulique** : CL Clapet, CT Compteur d'eau à impulsions, CU Cuve (réservoir, bâche), DA Cuve de stockage, EV Électrovanne, FQ Compteur d’achat d’eau en gros, FV Vanne de régulation, HV Vanne manuelle, MV Vanne motorisée, PD Pompe doseuse, PE Pompe d’épuisement, PM Pompe, RP Régulateur / réducteur de pression, RT Rétention, SP Groupe de surpression, SV Vanne de trop-plein, XV Vanne de sécurité
- **Instrumentation** : AT Analyseur de qualité, FS Contrôleur de circulation, FT Débitmètre, LH Détecteur de niveau (contact), LS Poires de niveau, LT Capteur de niveau, PS Pressostat, PT Capteur de pression, TT Capteur de température
- **Électricité et automatisme** : AL Alimentation 24 V CC, AR Armoire électrique, AU Automate programmable, DJ Disjoncteur, EL Électricité, GE Groupe électrogène, IS Interrupteur-sectionneur, IV Inverseur de source, KM Contacteur / départ moteur, LI Liaison de communication, OD Onduleur, TR Transformateur, VV Variateur de vitesse
- **Bâtiment et sécurité** : CH Chauffage, CM Climatisation, DE Déshumidificateur, EX Extracteur d’air, GA Gestion d’accès, IC Incendie, IN Inondation, VE Ventilateur d’air, XT Détecteur TOR (contact)
- **Structure** : AP Source, OU Ouvrage (site), UF Unité fonctionnelle

## AP — Source

*Structure* · options : Réarmement général, Mise à l’heure par télécommande

Automate ou poste de télégestion. La perte de communication est élaborée par SOREP (§ 2.4) : pas de variable dans la source. Code proposé, à valider.

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TM | MDV | Mot de vie | INT |  | Par défaut |  |
| TC | REARM | Réarmement des défauts | BOOL |  | Option (Réarmement général) |  |
| TC | MAH | Mise à l’heure | BOOL |  | Option (Mise à l’heure par télécommande) |  |

## OU — Ouvrage (site)

*Structure* · options : Détection incendie

Informations du site, sans équipement précis. Code proposé, à valider.

## UF — Unité fonctionnelle

*Structure* · options : Mode commandable, Réarmement par UF

Mode de conduite et état de service portés par l’en-tête du cadre (§ 3.3).

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | AUTO | Mode automatique | BOOL |  | Par défaut |  |
| TS | MANU | Mode manuel | BOOL |  | Par défaut |  |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |
| TC | AUTO | Passage en automatique | BOOL |  | Option (Mode commandable) |  |
| TC | MANU | Passage en manuel | BOOL |  | Option (Mode commandable) |  |
| TC | HS | Mise hors service | BOOL |  | Option (Mode commandable) | ⚙ |
| TC | ES | Remise en service | BOOL |  | Option (Mode commandable) |  |
| TC | REARM | Réarmement des défauts | BOOL |  | Option (Réarmement par UF) |  |

## CL — Clapet

*Hydraulique* · options : Fin de course

Clapet anti-retour, éventuellement équipé d'un fin de course.

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | OUV | Clapet ouvert | BOOL | ET | Option (Fin de course) |  |
| TS | DEF | Défaut clapet | BOOL |  | Option (Fin de course) | ⚙ |

## CT — Compteur d'eau à impulsions

*Hydraulique* · options : Seuils d’alarme

Compteur de volume (hors achat d'eau en gros : FQ).

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| CP | VOL | Volume compté | DINT | ET | Par défaut | ⚙ |
| TS | ABSIMP | Absence d'impulsions | BOOL |  | Option (Seuils d’alarme) | ⚙ |

## CU — Cuve (réservoir, bâche)

*Hydraulique* · options : Mesure de niveau, Contacts de niveau, Trop-plein, Seuils réglables

Équipement fonctionnel : niveaux, seuils, volume calculé et défauts selon l'instrumentation réellement installée.

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| ES | NIV | Mesure de niveau (4-20 mA) | INT | EA | Option (Mesure de niveau) |  |
| ES | PTB | Contact de niveau très bas | EBOOL | ET | Option (Contacts de niveau) |  |
| ES | PB | Contact de niveau bas | EBOOL | ET | Option (Contacts de niveau) |  |
| ES | PH | Contact de niveau haut | EBOOL | ET | Option (Contacts de niveau) |  |
| ES | PTH | Contact de niveau très haut | EBOOL | ET | Option (Contacts de niveau) |  |
| ES | TP | Détection de trop-plein | EBOOL | ET | Option (Trop-plein) |  |
| TM | NIV | Niveau mesuré | REAL | ← ES_NIV | Règle | ⚙ |
| TM | VOL | Volume calculé | REAL |  | Règle | ⚙ |
| TS | TB | Niveau très bas | BOOL | ← ES_PTB | Règle | ⚙ |
| TS | B | Niveau bas | BOOL | ← ES_PB | Règle | ⚙ |
| TS | H | Niveau haut | BOOL | ← ES_PH | Règle | ⚙ |
| TS | TH | Niveau très haut | BOOL | ← ES_PTH | Règle | ⚙ |
| TS | TP | Trop-plein | BOOL | ← ES_TP | Règle |  |
| TS | DEFMES | Défaut mesure de niveau | BOOL |  | Règle | ⚙ |
| TS | DISCMES | Discordance mesure / contacts | BOOL |  | Règle | ⚙ |
| TS | INCOH | Incohérence des contacts de niveau | BOOL |  | Règle | ⚙ |
| TS | HS | Cuve hors service | BOOL |  | Par défaut | ⚙ |
| TR | SH | Consigne de seuil haut | REAL |  | Option (Seuils réglables) |  |
| RTR | SH | Retour de consigne de seuil haut | REAL |  | Règle |  |
| TR | SB | Consigne de seuil bas | REAL |  | Option (Seuils réglables) |  |
| RTR | SB | Retour de consigne de seuil bas | REAL |  | Règle |  |

**Règles**

- `CU-01` *auto* — Mesure analogique → TM niveau : si ES_NIV → TM_NIV
- `CU-02` *proposition* — Mesure analogique → seuils calculés : si ES_NIV → TS_TB, TS_B, TS_H, TS_TH. Comparaison de la mesure à un seuil paramétrable, avec hystérésis et temporisation ; seuils à définir avec l'exploitant. Sans contact physique, ces TS sont CALCULÉES par l'automate.
- `CU-03` *auto* — Mesure analogique → défaut de mesure : si ES_NIV → TS_DEFMES. Mesure hors plage (< 3,8 mA ou > 20,5 mA) ou défaut transmis par le capteur, temporisé.
- `CU-04` *proposition* — Mesure analogique → volume calculé : si ES_NIV → TM_VOL. Volume = f(niveau) selon la géométrie de la cuve (section constante ou table de barémage) : géométrie à fournir ; sans elle, ne pas générer.
- `CU-05` *auto* — Contact très bas → TS très bas : si ES_PTB → TS_TB
- `CU-06` *auto* — Contact bas → TS bas : si ES_PB → TS_B
- `CU-07` *auto* — Contact haut → TS haut : si ES_PH → TS_H
- `CU-08` *auto* — Contact très haut → TS très haut : si ES_PTH → TS_TH
- `CU-09` *auto* — Détection trop-plein → TS trop-plein : si ES_TP → TS_TP
- `CU-10` *proposition* — Mesure + contact haut → discordance : si ES_NIV + ES_PH → TS_DISCMES. Contact haut actif alors que la mesure est sous le seuil haut (ou l'inverse) pendant T_DISC.
- `CU-11` *proposition* — Contacts bas + haut → incohérence : si ES_PB + ES_PH → TS_INCOH. Contact haut actif et contact bas inactif : ordre physique impossible, défaut de contact démontré.

## DA — Cuve de stockage

*Hydraulique* · options : aucune

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TM | NIV | Niveau | REAL | EA | Par défaut |  |
| TS | TB | Niveau très bas | BOOL |  | Par défaut |  |
| TS | B | Niveau bas | BOOL |  | Par défaut |  |
| TS | H | Niveau haut | BOOL |  | Par défaut |  |
| TS | TH | Niveau très haut | BOOL |  | Par défaut |  |

## EV — Électrovanne

*Hydraulique* · options : Télécommandée, Boutons locaux

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| ES | BP_OUV | Bouton local Ouvrir | EBOOL | ET | Option (Boutons locaux) |  |
| ES | BP_FER | Bouton local Fermer | EBOOL | ET | Option (Boutons locaux) |  |
| TS | OUV | Ouverte | BOOL | ET | Par défaut |  |
| TS | FER | Fermée | BOOL | ET | Par défaut |  |
| TS | DEF | Défaut général | BOOL | ET | Par défaut |  |
| TS | DISC | Discordance de position | BOOL |  | Par défaut | ⚙ |
| TS | DEFTPS | Temps de manœuvre dépassé | BOOL |  | Par défaut |  |
| TS | DISPO | Disponible | BOOL |  | Par défaut | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |
| TS | AUTO | Mode automatique | BOOL |  | Par défaut |  |
| TS | MANU | Mode manuel | BOOL |  | Par défaut |  |
| TS | LOC | Mode local | BOOL | ET | Par défaut |  |
| TC | AUTO | Passage en automatique | BOOL |  | Option (Télécommandée) |  |
| TC | MANU | Passage en manuel | BOOL |  | Option (Télécommandée) |  |
| TC | OUV | Commande ouverture | BOOL | ST | Option (Télécommandée) |  |
| TC | FER | Commande fermeture | BOOL | ST | Option (Télécommandée) |  |

## FQ — Compteur d’achat d’eau en gros

*Hydraulique* · options : Calcul dans la source, Seuils d’alarme

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TM | DEB | Débit instantané | REAL | EA | Par défaut |  |
| CP | IDX | Index cumulé | DINT |  | Par défaut |  |
| TS | DEF | Défaut capteur | BOOL |  | Par défaut |  |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |
| TM | VOLJ | Volume du jour | REAL |  | Option (Calcul dans la source) |  |
| TM | DEBN | Débit de nuit | REAL |  | Option (Calcul dans la source) |  |
| TS | B | Débit bas | BOOL |  | Option (Seuils d’alarme) |  |
| TS | H | Débit haut | BOOL |  | Option (Seuils d’alarme) |  |

## FV — Vanne de régulation

*Hydraulique* · options : aucune

## HV — Vanne manuelle

*Hydraulique* · options : aucune

Vanne à manœuvre manuelle, avec ou sans fins de course.

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| ES | FDC_OUV | Fin de course ouverte | EBOOL | ET | Par défaut |  |
| ES | FDC_FER | Fin de course fermée | EBOOL | ET | Par défaut |  |
| TS | OUV | Ouverte | BOOL | ← ES_FDC_OUV | Règle |  |
| TS | FER | Fermée | BOOL | ← ES_FDC_FER | Règle |  |
| TS | DISC | Discordance de position | BOOL |  | Règle | ⚙ |

**Règles**

- `HV-01` *auto* — Fin de course ouverte → TS ouverte : si ES_FDC_OUV → TS_OUV
- `HV-02` *auto* — Fin de course fermée → TS fermée : si ES_FDC_FER → TS_FER
- `HV-03` *proposition* — Deux fins de course → discordance : si ES_FDC_OUV + ES_FDC_FER → TS_DISC. Les deux fins de course actifs simultanément pendant plus de T_DISC = défaut. Aucune active = position intermédiaire, pas un défaut.

## MV — Vanne motorisée

*Hydraulique* · options : Télécommandée, Modulante, Complément, Boutons locaux

Fins de course, commandes, recopie de position. Retirer une fin de course absente : les informations qui en dépendent disparaissent ou restent à proposer.

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| ES | FDC_OUV | Fin de course ouverte | EBOOL | ET | Par défaut |  |
| ES | FDC_FER | Fin de course fermée | EBOOL | ET | Par défaut |  |
| ES | DEF | Contact de défaut actionneur | EBOOL | ET | Par défaut |  |
| ES | LOC | Sélecteur local / distance | EBOOL | ET | Par défaut |  |
| ES | OUV | Commande d'ouverture | EBOOL | ST | Option (Télécommandée) |  |
| ES | FER | Commande de fermeture | EBOOL | ST | Option (Télécommandée) |  |
| ES | POS | Recopie de position | INT | EA | Option (Modulante) |  |
| ES | CONS_POS | Consigne de position | INT | SA | Option (Modulante) |  |
| ES | BP_OUV | Bouton local ouvrir | EBOOL | ET | Option (Boutons locaux) |  |
| ES | BP_FER | Bouton local fermer | EBOOL | ET | Option (Boutons locaux) |  |
| ES | BP_AR | Bouton local arrêt | EBOOL | ET | Option (Boutons locaux) |  |
| TS | OUV | Ouverte | BOOL | ← ES_FDC_OUV | Règle |  |
| TS | FER | Fermée | BOOL | ← ES_FDC_FER | Règle |  |
| TS | DEF | Défaut actionneur | BOOL | ← ES_DEF | Règle |  |
| TS | LOC | Mode local | BOOL | ← ES_LOC | Règle |  |
| TS | DISC | Discordance de position | BOOL |  | Règle | ⚙ |
| TS | INT | Position intermédiaire | BOOL |  | Règle | ⚙ |
| TS | MNV | En manœuvre | BOOL |  | Règle | ⚙ |
| TS | DEFTPS | Temps de manœuvre dépassé | BOOL |  | Règle | ⚙ |
| TS | DEFMNV | Défaut de manœuvre (commande sans effet) | BOOL |  | Règle | ⚙ |
| TM | TPS | Temps de manœuvre | INT |  | Règle | ⚙ |
| TS | DEFCPL | Défaut couple | BOOL |  | Option (Complément) | ⚙ |
| TS | DISPO | Disponible | BOOL |  | Par défaut | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |
| TS | AUTO | Mode automatique | BOOL |  | Par défaut | ⚙ |
| TS | MANU | Mode manuel | BOOL |  | Par défaut | ⚙ |
| TC | OUV | Commande ouverture | BOOL | ← ES_OUV | Règle |  |
| TC | FER | Commande fermeture | BOOL | ← ES_FER | Règle |  |
| TC | AR | Commande arrêt | BOOL |  | Option (Télécommandée) | ⚙ |
| TC | AUTO | Passage en automatique | BOOL |  | Option (Télécommandée) | ⚙ |
| TC | MANU | Passage en manuel | BOOL |  | Option (Télécommandée) | ⚙ |
| TM | POS | Position mesurée | REAL | ← ES_POS | Règle | ⚙ |
| TR | POS | Consigne de position | REAL | ← ES_CONS_POS | Règle |  |
| RTR | POS | Retour de consigne de position | REAL |  | Règle |  |

**Règles**

- `MV-01` *auto* — Fin de course ouverte → TS ouverte : si ES_FDC_OUV → TS_OUV. Recopie directe de l'entrée ; vérifier une éventuelle inversion (contact NF) ou temporisation.
- `MV-02` *auto* — Fin de course fermée → TS fermée : si ES_FDC_FER → TS_FER. Recopie directe de l'entrée ; vérifier une éventuelle inversion (contact NF) ou temporisation.
- `MV-03` *auto* — Contact de défaut → TS défaut : si ES_DEF → TS_DEF
- `MV-04` *auto* — Sélecteur local → TS mode local : si ES_LOC → TS_LOC
- `MV-05` *proposition* — Deux fins de course → discordance et position intermédiaire : si ES_FDC_OUV + ES_FDC_FER → TS_DISC, TS_INT. Discordance : les deux fins de course actifs simultanément pendant plus de T_DISC (paramétrable) = défaut démontré. Aucune fin de course active = vanne en manœuvre ou en position intermédiaire : état normal, PAS un défaut (TS_INT, après T_MNV sans commande).
- `MV-06` *proposition* — Commande d'ouverture + retour ouvert → surveillance de manœuvre : si ES_OUV + ES_FDC_OUV → TS_MNV, TS_DEFTPS, TS_DEFMNV, TM_TPS. En manœuvre : commande active et position finale non atteinte. Temps dépassé : commande active et fin de course non atteinte après T_MAN (paramétrable). Défaut de manœuvre : commande active et fin de course de départ toujours actif après T_DEPART. Temps mesuré : chronométrage commande → retour. Une sortie seule ne suffit pas : le retour de position est indispensable.
- `MV-07` *proposition* — Commande de fermeture + retour fermé → surveillance de manœuvre : si ES_FER + ES_FDC_FER → TS_MNV, TS_DEFTPS, TS_DEFMNV, TM_TPS. Mêmes conditions que MV-06 dans le sens de la fermeture.
- `MV-08` *auto* — Sortie de commande ouverture → TC ouverture : si ES_OUV → TC_OUV. Impulsion ou maintien de la sortie, interverrouillages et mode distance à programmer.
- `MV-09` *auto* — Sortie de commande fermeture → TC fermeture : si ES_FER → TC_FER. Impulsion ou maintien de la sortie, interverrouillages et mode distance à programmer.
- `MV-10` *auto* — Recopie de position → TM position : si ES_POS → TM_POS
- `MV-11` *auto* — Consigne analogique → TR position : si ES_CONS_POS → TR_POS. Limitation et mise à l'échelle de la consigne avant écriture sur la sortie.

## PD — Pompe doseuse

*Hydraulique* · options : Télécommandée, Taux réglable, Boutons locaux

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| ES | BP_MA | Bouton local Marche | EBOOL | ET | Option (Boutons locaux) |  |
| ES | BP_AR | Bouton local Arrêt | EBOOL | ET | Option (Boutons locaux) |  |
| TS | MA | En marche | BOOL | ET | Par défaut |  |
| TS | DEF | Défaut général | BOOL | ET | Par défaut |  |
| TS | DISPO | Disponible | BOOL |  | Par défaut | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |
| TS | AUTO | Mode automatique | BOOL |  | Par défaut |  |
| TS | MANU | Mode manuel | BOOL |  | Par défaut |  |
| TS | LOC | Mode local | BOOL | ET | Par défaut |  |
| TC | AUTO | Passage en automatique | BOOL |  | Option (Télécommandée) |  |
| TC | MANU | Passage en manuel | BOOL |  | Option (Télécommandée) |  |
| TM | TAUX | Taux de sortie | REAL | EA | Par défaut |  |
| TR | TAUX | Consigne de taux | REAL | SA | Option (Taux réglable) |  |
| RTR | TAUX | Retour de consigne de taux | REAL |  | Option (Taux réglable) |  |
| TC | MA | Commande marche | BOOL | ST | Option (Télécommandée) |  |
| TC | AR | Commande arrêt | BOOL | ST | Option (Télécommandée) |  |

## PE — Pompe d’épuisement

*Hydraulique* · options : aucune

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | MA | En marche | BOOL | ET | Par défaut |  |
| TS | DEF | Défaut général | BOOL | ET | Par défaut |  |
| TS | DISPO | Disponible | BOOL |  | Par défaut | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |

## PM — Pompe

*Hydraulique* · options : Télécommandée, Variateur, Complément, Boutons locaux

Démarrage direct par défaut ; option Variateur pour une pompe à vitesse variable.

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| ES | MA | Retour de marche (contacteur) | EBOOL | ET | Par défaut |  |
| ES | DEFTH | Relais thermique / protection moteur | EBOOL | ET | Par défaut |  |
| ES | LOC | Sélecteur local / distance | EBOOL | ET | Par défaut |  |
| ES | CMD_MA | Commande de marche | EBOOL | ST | Option (Télécommandée) |  |
| ES | CMD_AR | Commande d'arrêt | EBOOL | ST | Option (Télécommandée) |  |
| ES | INT | Mesure d'intensité | INT | EA | Option (Complément) |  |
| ES | DEFVAR | Défaut variateur | EBOOL | ET | Option (Variateur) |  |
| ES | FREQ | Retour de fréquence variateur | INT | EA | Option (Variateur) |  |
| ES | CONS_FREQ | Consigne de fréquence variateur | INT | SA | Option (Variateur) |  |
| ES | BP_MA | Bouton local marche | EBOOL | ET | Option (Boutons locaux) |  |
| ES | BP_AR | Bouton local arrêt | EBOOL | ET | Option (Boutons locaux) |  |
| TS | MA | En marche | BOOL | ← ES_MA | Règle |  |
| TS | DEFTH | Défaut thermique | BOOL | ← ES_DEFTH | Règle |  |
| TS | LOC | Mode local | BOOL | ← ES_LOC | Règle |  |
| TS | DEFVAR | Défaut variateur | BOOL | ← ES_DEFVAR | Règle |  |
| TS | DEF | Défaut général | BOOL |  | Par défaut | ⚙ |
| TS | DISC | Discordance de marche | BOOL |  | Règle | ⚙ |
| TS | DEFDEM | Défaut démarrage | BOOL |  | Règle | ⚙ |
| TS | DISPO | Disponible | BOOL |  | Par défaut | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |
| TS | AUTO | Mode automatique | BOOL |  | Par défaut | ⚙ |
| TS | MANU | Mode manuel | BOOL |  | Par défaut | ⚙ |
| TS | DEFINT | Intensité anormale | BOOL |  | Règle | ⚙ |
| TC | MA | Commande marche | BOOL | ← ES_CMD_MA | Règle |  |
| TC | AR | Commande arrêt | BOOL | ← ES_CMD_AR | Règle |  |
| TC | AUTO | Passage en automatique | BOOL |  | Option (Télécommandée) | ⚙ |
| TC | MANU | Passage en manuel | BOOL |  | Option (Télécommandée) | ⚙ |
| CP | HF | Heures de fonctionnement | DINT |  | Règle | ⚙ |
| CP | NDEM | Nombre de démarrages | DINT |  | Règle | ⚙ |
| TM | INT | Intensité moteur | REAL | ← ES_INT | Règle | ⚙ |
| TM | FREQ | Fréquence moteur | REAL | ← ES_FREQ | Règle | ⚙ |
| TR | FREQ | Consigne de fréquence | REAL | ← ES_CONS_FREQ | Règle |  |
| RTR | FREQ | Retour de consigne de fréquence | REAL |  | Règle |  |

**Règles**

- `PM-01` *auto* — Retour de marche → TS en marche : si ES_MA → TS_MA
- `PM-02` *auto* — Relais thermique → TS défaut thermique : si ES_DEFTH → TS_DEFTH. Vérifier la logique du contact (souvent NF : défaut = entrée à 0).
- `PM-03` *auto* — Sélecteur local → TS mode local : si ES_LOC → TS_LOC
- `PM-04` *auto* — Défaut variateur → TS défaut variateur : si ES_DEFVAR → TS_DEFVAR
- `PM-05` *auto* — Retour de marche → compteurs : si ES_MA → CP_HF, CP_NDEM. Totalisation par l'automate à partir du retour de marche (heures, fronts montants) ; sauvegarde des compteurs à prévoir.
- `PM-06` *proposition* — Commande + retour de marche → discordance et défaut démarrage : si ES_CMD_MA + ES_MA → TS_DISC, TS_DEFDEM. Défaut démarrage : commande de marche active sans retour de marche après T_DEM (paramétrable). Discordance : retour de marche sans commande, ou commande sans retour, au-delà de T_DISC.
- `PM-07` *auto* — Sortie de marche → TC marche : si ES_CMD_MA → TC_MA. Impulsion ou maintien, mode distance et interverrouillages à programmer.
- `PM-08` *auto* — Sortie d'arrêt → TC arrêt : si ES_CMD_AR → TC_AR
- `PM-09` *auto* — Mesure d'intensité → TM intensité : si ES_INT → TM_INT
- `PM-10` *proposition* — Intensité + marche → intensité anormale : si ES_INT + ES_MA → TS_DEFINT. Intensité hors seuils bas / haut pendant la marche, après la phase de démarrage (seuils à définir).
- `PM-11` *auto* — Retour de fréquence → TM fréquence : si ES_FREQ → TM_FREQ
- `PM-12` *auto* — Consigne de fréquence → TR fréquence : si ES_CONS_FREQ → TR_FREQ. Limitation et mise à l'échelle de la consigne avant écriture sur la sortie.

## RP — Régulateur / réducteur de pression

*Hydraulique* · options : Pression amont, Pression aval

Détendeur ou régulateur de pression ; mesures amont / aval si instrumenté.

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TM | PAM | Pression amont | REAL | EA | Option (Pression amont) |  |
| TM | PAV | Pression aval | REAL | EA | Option (Pression aval) |  |
| TS | DEF | Défaut régulation | BOOL |  | Par défaut | ⚙ |

## RT — Rétention

*Hydraulique* · options : aucune

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | FUITE | Fuite rétention | BOOL | ET | Par défaut |  |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |

## SP — Groupe de surpression

*Hydraulique* · options : Télécommandée

Ensemble de pompes et régulation de pression livré en skid ; informations transmises par le coffret.

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | MA | En marche | BOOL | ET | Par défaut |  |
| TS | DEF | Défaut général | BOOL | ET | Par défaut |  |
| TS | MQEAU | Manque d'eau | BOOL | ET | Par défaut |  |
| TS | DISPO | Disponible | BOOL |  | Par défaut | ⚙ |
| TM | PRE | Pression de refoulement | REAL | EA | Par défaut |  |
| TC | MA | Commande marche | BOOL | ST | Option (Télécommandée) |  |
| TC | AR | Commande arrêt | BOOL | ST | Option (Télécommandée) |  |

## SV — Vanne de trop-plein

*Hydraulique* · options : Télécommandée, Complément, Boutons locaux

Mêmes informations que la vanne motorisée.

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| ES | BP_OUV | Bouton local Ouvrir | EBOOL | ET | Option (Boutons locaux) |  |
| ES | BP_FER | Bouton local Fermer | EBOOL | ET | Option (Boutons locaux) |  |
| ES | BP_AR | Bouton local Arrêt | EBOOL | ET | Option (Boutons locaux) |  |
| TS | OUV | Ouverte | BOOL | ET | Par défaut |  |
| TS | FER | Fermée | BOOL | ET | Par défaut |  |
| TS | MNV | En manœuvre | BOOL |  | Par défaut |  |
| TS | DEF | Défaut général | BOOL |  | Par défaut |  |
| TS | DISC | Discordance de position | BOOL |  | Par défaut | ⚙ |
| TS | DEFTPS | Temps de manœuvre dépassé | BOOL |  | Par défaut |  |
| TS | DEFCPL | Défaut couple | BOOL | ET | Option (Complément) |  |
| TS | DISPO | Disponible | BOOL |  | Par défaut | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |
| TS | AUTO | Mode automatique | BOOL |  | Par défaut |  |
| TS | MANU | Mode manuel | BOOL |  | Par défaut |  |
| TS | LOC | Mode local | BOOL | ET | Par défaut |  |
| TC | AUTO | Passage en automatique | BOOL |  | Option (Télécommandée) |  |
| TC | MANU | Passage en manuel | BOOL |  | Option (Télécommandée) |  |
| TM | TPS | Temps de manœuvre | INT |  | Option (Complément) |  |
| TC | OUV | Commande ouverture | BOOL | ST | Option (Télécommandée) |  |
| TC | FER | Commande fermeture | BOOL | ST | Option (Télécommandée) |  |
| TC | AR | Commande arrêt | BOOL | ST | Option (Télécommandée) |  |

## XV — Vanne de sécurité

*Hydraulique* · options : Télécommandée, Complément, Boutons locaux

Mêmes informations que la vanne motorisée ; autres informations à définir.

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| ES | BP_OUV | Bouton local Ouvrir | EBOOL | ET | Option (Boutons locaux) |  |
| ES | BP_FER | Bouton local Fermer | EBOOL | ET | Option (Boutons locaux) |  |
| ES | BP_AR | Bouton local Arrêt | EBOOL | ET | Option (Boutons locaux) |  |
| TS | OUV | Ouverte | BOOL | ET | Par défaut |  |
| TS | FER | Fermée | BOOL | ET | Par défaut |  |
| TS | MNV | En manœuvre | BOOL |  | Par défaut |  |
| TS | DEF | Défaut général | BOOL |  | Par défaut |  |
| TS | DISC | Discordance de position | BOOL |  | Par défaut | ⚙ |
| TS | DEFTPS | Temps de manœuvre dépassé | BOOL |  | Par défaut |  |
| TS | DEFCPL | Défaut couple | BOOL | ET | Option (Complément) |  |
| TS | DISPO | Disponible | BOOL |  | Par défaut | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |
| TS | AUTO | Mode automatique | BOOL |  | Par défaut |  |
| TS | MANU | Mode manuel | BOOL |  | Par défaut |  |
| TS | LOC | Mode local | BOOL | ET | Par défaut |  |
| TC | AUTO | Passage en automatique | BOOL |  | Option (Télécommandée) |  |
| TC | MANU | Passage en manuel | BOOL |  | Option (Télécommandée) |  |
| TM | TPS | Temps de manœuvre | INT |  | Option (Complément) |  |
| TC | OUV | Commande ouverture | BOOL | ST | Option (Télécommandée) |  |
| TC | FER | Commande fermeture | BOOL | ST | Option (Télécommandée) |  |
| TC | AR | Commande arrêt | BOOL | ST | Option (Télécommandée) |  |

## AT — Analyseur de qualité

*Instrumentation* · options : Seuils réglables

Chlore, ozone, pH, conductivité, turbidité, CO2… : préciser la grandeur et l'unité dans le libellé de l'équipement (un seul code pour la fonction « analyseur »).

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| ES | VAL | Mesure de valeur (4-20 mA) | INT | EA | Par défaut |  |
| TM | VAL | Valeur mesurée | REAL | ← ES_VAL | Règle | ⚙ |
| TS | DEF | Défaut capteur | BOOL |  | Règle | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |
| TS | B | Seuil bas | BOOL |  | Par défaut | ⚙ |
| TS | H | Seuil haut | BOOL |  | Par défaut | ⚙ |
| TR | SH | Consigne de seuil haut | REAL |  | Option (Seuils réglables) |  |
| RTR | SH | Retour de consigne de seuil haut | REAL |  | Règle |  |
| TR | SB | Consigne de seuil bas | REAL |  | Option (Seuils réglables) |  |
| RTR | SB | Retour de consigne de seuil bas | REAL |  | Règle |  |

**Règles**

- `AT-01` *auto* — Entrée analogique → TM valeur : si ES_VAL → TM_VAL
- `AT-02` *auto* — Entrée analogique → défaut capteur : si ES_VAL → TS_DEF. Mesure hors plage (< 3,8 mA ou > 20,5 mA) ou défaut transmis par le capteur, temporisé.

## FS — Contrôleur de circulation

*Instrumentation* · options : aucune

Contact de présence de débit (débitmètre à seuil, palette).

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | CIRC | Circulation présente | BOOL | ET | Par défaut |  |
| TS | DEFCIRC | Défaut de circulation | BOOL |  | Par défaut | ⚙ |

## FT — Débitmètre

*Instrumentation* · options : Seuils d’alarme, Seuils réglables, Avec totalisateur

Débitmètre électromagnétique ou à ultrasons.

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| ES | DEB | Mesure de débit (4-20 mA) | INT | EA | Par défaut |  |
| ES | IMP | Impulsions de comptage | EBOOL | ET | Option (Avec totalisateur) |  |
| TM | DEB | Débit instantané | REAL | ← ES_DEB | Règle | ⚙ |
| TS | DEF | Défaut capteur | BOOL |  | Règle | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |
| TS | B | Débit bas | BOOL |  | Option (Seuils d’alarme) | ⚙ |
| TS | H | Débit haut | BOOL |  | Option (Seuils d’alarme) | ⚙ |
| TR | SH | Consigne de seuil haut | REAL |  | Option (Seuils réglables) |  |
| RTR | SH | Retour de consigne de seuil haut | REAL |  | Règle |  |
| TR | SB | Consigne de seuil bas | REAL |  | Option (Seuils réglables) |  |
| RTR | SB | Retour de consigne de seuil bas | REAL |  | Règle |  |
| CP | VOL | Volume totalisé | DINT | ← ES_IMP | Règle | ⚙ |
| TS | ABSIMP | Absence d'impulsions | BOOL |  | Règle | ⚙ |

**Règles**

- `FT-01` *auto* — Entrée analogique → TM débit : si ES_DEB → TM_DEB
- `FT-02` *auto* — Entrée analogique → défaut capteur : si ES_DEB → TS_DEF. Mesure hors plage (< 3,8 mA ou > 20,5 mA) ou défaut transmis par le capteur, temporisé.
- `FT-03` *auto* — Impulsions de comptage → CP volume : si ES_IMP → CP_VOL. Comptage des impulsions (poids d'impulsion à paramétrer) ; sauvegarde du compteur à prévoir.
- `FT-04` *proposition* — Mesure de débit → volume par intégration : si ES_DEB → CP_VOL. Intégration du débit par l'automate : précision limitée, à n'employer qu'en l'absence d'impulsions.
- `FT-05` *proposition* — Mesure + impulsions → absence d'impulsions : si ES_DEB + ES_IMP → TS_ABSIMP. Débit mesuré supérieur au seuil sans impulsion reçue pendant T (défaut de comptage).

## LH — Détecteur de niveau (contact)

*Instrumentation* · options : aucune

Détecteur TOR de niveau (rétention, fuite, bâche).

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | NIV | Niveau atteint | BOOL | ET | Par défaut |  |

## LS — Poires de niveau

*Instrumentation* · options : 3 poires, 5 poires

Par défaut : 2 poires.

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | ARP | Poire arrêt pompes | BOOL | ET | Par défaut |  |
| TS | MAP1 | Poire marche pompe | BOOL | ET | Par défaut |  |
| TS | H | Niveau haut | BOOL | ET | Option (3 poires) |  |
| TS | MAP2 | Poire marche pompe 2 | BOOL | ET | Option (5 poires) |  |
| TS | TH | Niveau très haut | BOOL | ET | Option (5 poires) |  |
| TS | TB | Niveau très bas | BOOL | ET | Option (5 poires) |  |

## LT — Capteur de niveau

*Instrumentation* · options : Seuils réglables

Transmetteur de niveau ; seuils calculés par l'automate.

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| ES | NIV | Mesure de niveau (4-20 mA) | INT | EA | Par défaut |  |
| TM | NIV | Niveau mesuré | REAL | ← ES_NIV | Règle | ⚙ |
| TS | DEF | Défaut capteur | BOOL |  | Règle | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |
| TS | TB | Niveau très bas | BOOL |  | Par défaut | ⚙ |
| TS | B | Niveau bas | BOOL |  | Par défaut | ⚙ |
| TS | H | Niveau haut | BOOL |  | Par défaut | ⚙ |
| TS | TH | Niveau très haut | BOOL |  | Par défaut | ⚙ |
| TR | SH | Consigne de seuil haut | REAL |  | Option (Seuils réglables) |  |
| RTR | SH | Retour de consigne de seuil haut | REAL |  | Règle |  |
| TR | SB | Consigne de seuil bas | REAL |  | Option (Seuils réglables) |  |
| RTR | SB | Retour de consigne de seuil bas | REAL |  | Règle |  |

**Règles**

- `LT-01` *auto* — Entrée analogique → TM niveau : si ES_NIV → TM_NIV
- `LT-02` *auto* — Entrée analogique → défaut capteur : si ES_NIV → TS_DEF. Mesure hors plage (< 3,8 mA ou > 20,5 mA) ou défaut transmis par le capteur, temporisé.

## PS — Pressostat

*Instrumentation* · options : aucune

Contact de seuil de pression.

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | SEUIL | Seuil de pression atteint | BOOL | ET | Par défaut |  |

## PT — Capteur de pression

*Instrumentation* · options : Seuils réglables

Transmetteur de pression.

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| ES | PRE | Mesure de pression (4-20 mA) | INT | EA | Par défaut |  |
| TM | PRE | Pression mesurée | REAL | ← ES_PRE | Règle | ⚙ |
| TS | DEF | Défaut capteur | BOOL |  | Règle | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |
| TS | B | Pression basse | BOOL |  | Par défaut | ⚙ |
| TS | H | Pression haute | BOOL |  | Par défaut | ⚙ |
| TR | SH | Consigne de seuil haut | REAL |  | Option (Seuils réglables) |  |
| RTR | SH | Retour de consigne de seuil haut | REAL |  | Règle |  |
| TR | SB | Consigne de seuil bas | REAL |  | Option (Seuils réglables) |  |
| RTR | SB | Retour de consigne de seuil bas | REAL |  | Règle |  |

**Règles**

- `PT-01` *auto* — Entrée analogique → TM pression : si ES_PRE → TM_PRE
- `PT-02` *auto* — Entrée analogique → défaut capteur : si ES_PRE → TS_DEF. Mesure hors plage (< 3,8 mA ou > 20,5 mA) ou défaut transmis par le capteur, temporisé.

## TT — Capteur de température

*Instrumentation* · options : Seuils d’alarme, Seuils réglables

Sonde de température (armoire, local, process).

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| ES | TEMP | Mesure de température (4-20 mA) | INT | EA | Par défaut |  |
| TM | TEMP | Température mesurée | REAL | ← ES_TEMP | Règle | ⚙ |
| TS | DEF | Défaut capteur | BOOL |  | Règle | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |
| TS | B | Température basse | BOOL |  | Option (Seuils d’alarme) | ⚙ |
| TS | H | Température haute | BOOL |  | Option (Seuils d’alarme) | ⚙ |
| TR | SH | Consigne de seuil haut | REAL |  | Option (Seuils réglables) |  |
| RTR | SH | Retour de consigne de seuil haut | REAL |  | Règle |  |
| TR | SB | Consigne de seuil bas | REAL |  | Option (Seuils réglables) |  |
| RTR | SB | Retour de consigne de seuil bas | REAL |  | Règle |  |

**Règles**

- `TT-01` *auto* — Entrée analogique → TM température : si ES_TEMP → TM_TEMP
- `TT-02` *auto* — Entrée analogique → défaut capteur : si ES_TEMP → TS_DEF. Mesure hors plage (< 3,8 mA ou > 20,5 mA) ou défaut transmis par le capteur, temporisé.

## AL — Alimentation 24 V CC

*Électricité et automatisme* · options : aucune

Alimentation de commande, avec contact de défaut.

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | DEF | Défaut alimentation | BOOL | ET | Par défaut |  |

## AR — Armoire électrique

*Électricité et automatisme* · options : Ventilation, Parafoudre

Défauts communs de l'armoire.

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | MQU | Manque tension réseau | BOOL | ET | Par défaut |  |
| TS | MQ24 | Manque 24 V commande | BOOL | ET | Par défaut |  |
| TS | ISOL | Défaut d'isolement | BOOL | ET | Par défaut |  |
| TS | PARAF | Défaut parafoudre | BOOL | ET | Option (Parafoudre) |  |
| TS | VENTIL | Défaut ventilation | BOOL | ET | Option (Ventilation) |  |
| TM | TEMP | Température armoire | REAL | EA | Option (Ventilation) |  |

## AU — Automate programmable

*Électricité et automatisme* · options : Redondance

Diagnostic de l'automate.

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | DEFCPU | Défaut automate | BOOL |  | Par défaut | ⚙ |
| TS | DEFES | Défaut de module d'E/S | BOOL |  | Par défaut | ⚙ |
| TS | PILE | Défaut pile | BOOL |  | Par défaut | ⚙ |
| TM | MDV | Mot de vie | INT |  | Par défaut | ⚙ |
| TS | REDOK | Redondance opérationnelle | BOOL |  | Option (Redondance) | ⚙ |

## DJ — Disjoncteur

*Électricité et automatisme* · options : aucune

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | FER | Fermé | BOOL | ET | Par défaut |  |
| TS | DECL | Disjoncteur déclenché | BOOL | ET | Par défaut |  |
| TS | DISPO | Disponible | BOOL |  | Par défaut | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |

## EL — Électricité

*Électricité et automatisme* · options : aucune

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | DALIM | Défaut alimentation | BOOL | ET | Par défaut |  |

## GE — Groupe électrogène

*Électricité et automatisme* · options : Télécommandé

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | MA | En marche | BOOL | ET | Par défaut |  |
| TS | DEF | Défaut groupe électrogène | BOOL | ET | Par défaut |  |
| TS | DISPO | Disponible | BOOL |  | Par défaut | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |
| TS | AUTO | Mode automatique | BOOL |  | Par défaut |  |
| TS | MANU | Mode manuel | BOOL |  | Par défaut |  |
| TS | LOC | Mode local | BOOL | ET | Par défaut |  |
| TC | AUTO | Passage en automatique | BOOL |  | Option (Télécommandé) |  |
| TC | MANU | Passage en manuel | BOOL |  | Option (Télécommandé) |  |
| TC | MA | Commande marche | BOOL | ST | Option (Télécommandé) |  |
| TC | AR | Commande arrêt | BOOL | ST | Option (Télécommandé) |  |

## IS — Interrupteur-sectionneur

*Électricité et automatisme* · options : aucune

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | FER | Fermé | BOOL | ET | Par défaut |  |
| TS | DECL | Déclenché | BOOL | ET | Par défaut |  |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |

## IV — Inverseur de source

*Électricité et automatisme* · options : aucune

Code provisoire : IN est utilisé deux fois dans le standard (inondation et inverseur). À valider.

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | POSN | Position réseau | BOOL | ET | Par défaut |  |
| TS | POSS | Position secours | BOOL | ET | Par défaut |  |
| TS | DISC | Discordance inverseur | BOOL |  | Par défaut | ⚙ |
| TS | DISPO | Disponible | BOOL |  | Par défaut | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |

## KM — Contacteur / départ moteur

*Électricité et automatisme* · options : Télécommandé

Départ moteur hors pompe (agitateur, ventilateur…).

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | MA | En marche | BOOL | ET | Par défaut |  |
| TS | DEF | Défaut départ (thermique) | BOOL | ET | Par défaut |  |
| TC | MA | Commande marche | BOOL | ST | Option (Télécommandé) |  |
| TC | AR | Commande arrêt | BOOL | ST | Option (Télécommandé) |  |
| CP | HF | Heures de fonctionnement | DINT |  | Par défaut | ⚙ |

## LI — Liaison de communication

*Électricité et automatisme* · options : aucune

Liaison vers un équipement communicant (skid, télétransmetteur, variateur).

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | DEFCOM | Défaut de communication | BOOL |  | Par défaut | ⚙ |

## OD — Onduleur

*Électricité et automatisme* · options : Complément

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | SBAT | Onduleur sur batterie | BOOL | ET | Par défaut |  |
| TS | DEF | Défaut onduleur | BOOL | ET | Par défaut |  |
| TS | DISPO | Disponible | BOOL |  | Par défaut | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |
| TM | AUTON | Autonomie | REAL |  | Option (Complément) |  |

## TR — Transformateur

*Électricité et automatisme* · options : aucune

Même code que la famille TR (téléréglage) : la position dans le nom les distingue.

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | STEN | Sous tension | BOOL | ET | Par défaut |  |
| TS | DEFTEMP | Défaut température | BOOL | ET | Par défaut |  |
| TS | DISPO | Disponible | BOOL |  | Par défaut | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |

## VV — Variateur de vitesse

*Électricité et automatisme* · options : aucune

## CH — Chauffage

*Bâtiment et sécurité* · options : aucune

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | MA | En marche | BOOL | ET | Par défaut |  |
| TS | DEF | Défaut général | BOOL | ET | Par défaut |  |
| TS | DISPO | Disponible | BOOL |  | Par défaut | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |

## CM — Climatisation

*Bâtiment et sécurité* · options : aucune

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | MA | En marche | BOOL | ET | Par défaut |  |
| TS | DEF | Défaut général | BOOL | ET | Par défaut |  |
| TS | DISPO | Disponible | BOOL |  | Par défaut | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |

## DE — Déshumidificateur

*Bâtiment et sécurité* · options : aucune

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | MA | En marche | BOOL | ET | Par défaut |  |
| TS | DEF | Défaut général | BOOL | ET | Par défaut |  |
| TS | DISPO | Disponible | BOOL |  | Par défaut | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |

## EX — Extracteur d’air

*Bâtiment et sécurité* · options : aucune

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | MA | En marche | BOOL | ET | Par défaut |  |
| TS | DEF | Défaut général | BOOL | ET | Par défaut |  |
| TS | DISPO | Disponible | BOOL |  | Par défaut | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |

## GA — Gestion d’accès

*Bâtiment et sécurité* · options : aucune

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | INTR | Intrusion | BOOL | ET | Par défaut |  |
| TS | PORTE | Porte ouverte | BOOL | ET | Par défaut |  |

## IC — Incendie

*Bâtiment et sécurité* · options : aucune

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | INCEN | Détection incendie | BOOL | ET | Option (Détection incendie) |  |

## IN — Inondation

*Bâtiment et sécurité* · options : aucune

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | INOND | Inondation | BOOL | ET | Par défaut |  |

## VE — Ventilateur d’air

*Bâtiment et sécurité* · options : Deux vitesses

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | MA | En marche | BOOL | ET | Par défaut |  |
| TS | MAPV | Marche petite vitesse | BOOL | ET | Option (Deux vitesses) |  |
| TS | MAGV | Marche grande vitesse | BOOL | ET | Option (Deux vitesses) |  |
| TS | DEF | Défaut général | BOOL | ET | Par défaut |  |
| TS | DISPO | Disponible | BOOL |  | Par défaut | ⚙ |
| TS | HS | Hors service | BOOL |  | Par défaut | ⚙ |

## XT — Détecteur TOR (contact)

*Bâtiment et sécurité* · options : aucune

Contact de détection générique (intrusion, porte, fuite).

| Famille | Code | Information | Type | E/S | Présence | ⚙ |
|---|---|---|---|---|---|---|
| TS | DET | Détection | BOOL | ET | Par défaut |  |

## Règles communes à tous les types

- `GEN-01` *auto* — Téléréglage → retour de téléréglage : Recopie par l'automate de la consigne effectivement prise en compte, pour confirmer la réception côté supervision.
