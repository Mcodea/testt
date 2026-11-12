# Contrôle de conception du référentiel — 2026-11-09 référentiel V1.2 (informations calculées justifiées)

Produit par `genvar/audit_referentiel.py` (écran Référentiel, bloc « Contrôle de conception du type »).
Le contrôle signale ; il ne corrige rien. Les points ci-dessous attendent l'arbitrage de l'exploitant.

| Type | Constat | Gravité | Détail | Clés |
| --- | --- | --- | --- | --- |
| AR | EA_SANS_DEFAUT | Alerte | TM_TEMP (Température armoire) : aucune information de défaut de mesure (rupture, hors plage) n'en découle. | TM_TEMP |
| AT | SEUILS_PAR_DEFAUT | Alerte | Alarmes de seuil générées d'office : elles ne valent que si l'exploitation les prévoit (option ou proposition sur d'autres types). | TS_B, TS_H |
| DA | SEUILS_PAR_DEFAUT | Alerte | Alarmes de seuil générées d'office : elles ne valent que si l'exploitation les prévoit (option ou proposition sur d'autres types). | TS_TB, TS_B, TS_H, TS_TH |
| FT | OPTION_SANS_EFFET | Alerte | Option « Avec totalisateur » : aucun signal ne lui est associé. |  |
| LT | SEUILS_PAR_DEFAUT | Alerte | Alarmes de seuil générées d'office : elles ne valent que si l'exploitation les prévoit (option ou proposition sur d'autres types). | TS_TB, TS_B, TS_H, TS_TH |
| MV | EA_SANS_DEFAUT | Alerte | ES_POS (Recopie de position) : aucune information de défaut de mesure (rupture, hors plage) n'en découle. | ES_POS |
| PM | EA_SANS_DEFAUT | Alerte | ES_FREQ (Retour de fréquence variateur) : aucune information de défaut de mesure (rupture, hors plage) n'en découle. | ES_FREQ |
| PT | SEUILS_PAR_DEFAUT | Alerte | Alarmes de seuil générées d'office : elles ne valent que si l'exploitation les prévoit (option ou proposition sur d'autres types). | TS_B, TS_H |

## Corrections déjà appliquées dans le référentiel V1.2 (9 novembre 2026)

| Type | Avant (V1.1) | Après (V1.2) | Justification |
| --- | --- | --- | --- |
| HV | HV-03 proposait TS_DISC seule ; aucune information pour « aucune fin de course active » | HV-03 propose TS_DISC et TS_INT (position intermédiaire) ; logique écrite : pas de défaut de manœuvre sans ordre | Brief §3 : deux FDC actives = incohérence ; aucune = intermédiaire ou anomalie selon tempo ; vanne non commandée : pas d'ordre inventé |
| MV | MV-05 : logique ambiguë | Logique distinguant discordance, manœuvre en cours, position intermédiaire ; défauts d'ordre renvoyés à MV-06/07 (vanne commandée seulement) | idem |
| EV, SV, XV | TS_DISC, TS_DEFTPS (et TS_MNV) générées d'office, même sans commande | Présence « Règle » : DISC proposée si deux retours (EV/SV/XV-01) ; DEFTPS / MNV proposées seulement si l'ordre (TC_OUV / TC_FER, option Télécommandée) existe (‑02, ‑03) | Défaut de manœuvre sur un ordre inexistant |
| IV | TS_DISC d'office | Proposée si les deux positions sont câblées (IV-01) | Information calculée : décision explicite |
| DA | Mesure analogique TM_NIV sans défaut de mesure | TS_DEF retenue par DA-01 (rupture / hors plage), comme LT-02 | Rupture de mesure |

Les ouvrages enregistrés gardent leur référentiel figé : l'écran de l'ouvrage signale la nouvelle version et
ne l'applique qu'après accord (« Examiner et appliquer… »).
