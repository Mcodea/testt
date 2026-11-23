# Règles de nommage OGIAS

Document généré par `outils/documenter_regles_nommage.py` depuis le code et le référentiel livrés (« 2026-11-11 référentiel V2 (noms physiques, CT consolidé dans FT, règles documentaires, profil VANNE_MV) ») : ne pas modifier à la main. Les exemples sont fictifs (lieu XTST).

## 1. Repères

La charte de nommage est un réglage du client (Outils › Standards d'ingénierie). Charte OGIAS par défaut :

- lieu : 4 lettres ou chiffres
- type d'ouvrage : 2 lettres
- numéro d'ouvrage sur 2 chiffre(s)
- code et numéro d'équipement (référentiel métier)
- séparateur : aucun

Exemple : ouvrage **XTSTRV01**, équipement **XTSTRV01PM01** (longueur maximale d'un repère : 32 caractères).

## 2. Noms de variables

Une variable se nomme **FAMILLE_REPÈRE_CODE** : la famille, le repère court de l'équipement dans l'ouvrage (sans le lieu), puis le code du signal du référentiel.

Exemple, pompe XTSTRV01PM01 :

| Famille | Signification | Nom produit |
|---|---|---|
| CP | Télécomptage | `CP_RV01PM01_HF` |
| TS | Télésignalisation | `TS_RV01PM01_MA` |

Un nom de variable fait au plus **32 caractères** (Control Expert), n'emploie que des lettres, des chiffres et le tiret bas simple `_`, et est unique dans l'ouvrage. Le libellé de supervision fait au plus 40 caractères (réglable par ouvrage).

OGIAS ne renomme jamais une variable de lui-même : un nom en collision est signalé, pas modifié.

## 3. Règles de contrôle sur les noms

| Règle | Titre | Gravité | Où corriger |
|---|---|---|---|
| R-OUV-01 | Identification de l'ouvrage incomplète | Erreur | Compléter la fiche de l'ouvrage. |
| R-OUV-02 | Lieu mal formé | Erreur | Saisir 4 caractères (lettres majuscules ou chiffres) dans la fiche de l'ouvrage. |
| R-OUV-03 | Code d'ouvrage mal formé | Erreur | Saisir 2 lettres majuscules dans la fiche de l'ouvrage. |
| R-OUV-04 | Numéro d'ouvrage invalide | Erreur | Saisir un numéro de 01 à 99, ou le laisser vide pour un ouvrage historique. |
| R-OUV-05 | Sous-ensemble mal formé | Erreur | Saisir 2 caractères (lettres majuscules ou chiffres). |
| R-OUV-06 | Sous-ensemble déclaré deux fois | Erreur | Supprimer ou renommer le doublon dans la fiche de l'ouvrage. |
| R-EQ-06 | Numéro d'équipement mal formé | Erreur | Saisir 2 chiffres (01 à 99). |
| R-EQ-07 | Repère en double | Erreur | Renuméroter l'un des deux équipements. |
| R-NOM-01 | Nom trop long | Erreur | Raccourcir le code du signal ou du repère. |
| R-NOM-02 | Caractères non autorisés dans un nom | Erreur | N'utiliser que lettres, chiffres et _ simple. |
| R-NOM-03 | Nom en double | Erreur | Renommer l'un des signaux ou renuméroter l'équipement. |
| R-NOM-04 | Ouvrages du même programme en collision de noms | Erreur | Mettre le lieu dans les noms ou renuméroter l'un des ouvrages (aucun renommage automatique). |
| R-NOM-05 | Ouvrages sans programme déclaré aux noms identiques | Alerte | Déclarer le nom du programme automate de chaque ouvrage (aucun renommage automatique). |

## 4. Types d'équipement du référentiel

50 types.

**Hydraulique** : `CL` Clapet, `CU` Cuve (réservoir, bâche), `DA` Cuve de stockage, `EV` Électrovanne, `FQ` Compteur d’achat d’eau en gros, `FV` Vanne de régulation, `HV` Vanne manuelle, `MV` Vanne motorisée, `PD` Pompe doseuse, `PE` Pompe d’épuisement, `PM` Pompe, `RP` Régulateur / réducteur de pression, `RT` Rétention, `SP` Groupe de surpression, `SV` Vanne de trop-plein, `XV` Vanne de sécurité

**Instrumentation** : `AT` Analyseur de qualité, `FS` Contrôleur de circulation, `FT` Débitmètre, `LH` Détecteur de niveau (contact), `LS` Poires de niveau, `LT` Capteur de niveau, `PS` Pressostat, `PT` Capteur de pression, `TT` Capteur de température

**Électricité et automatisme** : `AL` Alimentation 24 V CC, `AR` Armoire électrique, `AU` Automate programmable, `DJ` Disjoncteur, `EL` Électricité, `GE` Groupe électrogène, `IS` Interrupteur-sectionneur, `IV` Inverseur de source, `KM` Contacteur / départ moteur, `LI` Liaison de communication, `OD` Onduleur, `TR` Transformateur, `VV` Variateur de vitesse

**Bâtiment et sécurité** : `CH` Chauffage, `CM` Climatisation, `DE` Déshumidificateur, `EX` Extracteur d’air, `GA` Gestion d’accès, `IC` Incendie, `IN` Inondation, `VE` Ventilateur d’air, `XT` Détecteur TOR (contact)

**Structure** : `AP` Source, `OU` Ouvrage (site), `UF` Unité fonctionnelle
