# OGIAS V0.26 — Compte rendu de livraison (9 novembre 2026)

Base : V0.25, sans nouvelle archive reçue. Projets, repères et adresses existants : aucun renommage, aucune
migration automatique.

## 1. Ce qui fonctionnait déjà (conservé)

- Parcours en 5 étapes : Équipements → Liste des E/S → Matériel → Variables → Recette.
- Charte ESB / RESO : codes lieu par règle, repère sur 12 caractères.
- Matériel M340 / M580 calculé depuis les E/S validées ; proposition S4W indicative.
- Exports XSY / TXT au format Control Expert V14.1.
- Moteur de règles : signaux « Règle » auto ou proposés, `GEN-01` TR → RTR.
- Catalogue figé dans chaque ouvrage enregistré.

## 2. Cause de l'anomalie « discordance oubliée » (vanne HV)

La règle HV-03 proposait bien TS_DISC. Mais une proposition :
- n'était **affichée nulle part** dans l'interface ;
- ne **bloquait pas** la validation de l'équipement ;
- n'était **signalée par aucun contrôle**.

L'information disparaissait donc en silence. Le même mécanisme touchait 9 règles : MV-05/06/07, PM-06/10,
FT-04/05, CU-02/04/10/11.

## 3. Ce qui a été modifié

| Domaine | Modification |
| --- | --- |
| Moteur | `decider_proposition` / `decider_propositions` : retenir, écarter (motif obligatoire, conservé dans l'ouvrage), revoir. |
| Moteur | `informations_fonctionnelles` : état, provenance, E/S sources et logique de chaque information non physique. |
| Moteur | `manques_parametrage` : une seule liste (échelles, impulsions, décisions) pour la validation et l'affichage. |
| Contrôles | « Information attendue non décidée » (erreur) ; « écartée sans motif » (alerte) ; information calculée sans E/S pour la calculer ; équipement de projet neuf sans aucune E/S physique. |
| Contrôles | Chaque anomalie porte son étape (Équipements, Liste des E/S et matériel, Variables). |
| Référentiel V1.2 | HV, MV, EV, SV, XV, IV, DA : voir `AUDIT_REFERENTIEL.md` ; aucun ordre inventé pour une vanne non commandée. |
| Audit du référentiel | `genvar/audit_referentiel.py` (8 contrôles de conception), affiché dans l'écran Référentiel. |
| Versions | Écarts entre le référentiel figé de l'ouvrage et celui de l'outil ; application seulement sur accord. |
| Interface | Bloc « Informations fonctionnelles » dans la fiche, états d'équipement (arbre, tableaux, fiche), contrôles de l'équipement dans sa fiche, « Reste à faire » sur l'ouvrage, recette classée par étape avec accès direct, E/S portées visibles. |
| Interface | Un refus métier déjà affiché ne laisse plus d'erreur JavaScript non traitée. |

## 4. Anomalies corrigées

1. Informations proposées omises sans trace (HV-03 et 9 autres règles).
2. Défaut de temps de manœuvre (et manœuvre en cours) généré d'office pour EV, SV et XV non commandées.
3. Discordance d'IV et d'EV générée sans décision.
4. Cuve DA : mesure analogique sans défaut de mesure.
5. Fiche d'un équipement « porté » (DJ, EV…) : le texte « aucune E/S prédéfinie » s'affichait alors que des
   contacts câblés existent.
6. CP_VOL d'un débitmètre à impulsions : la justification mélangeait l'intégration du débit (FT-04) et le comptage
   (FT-03). Seule la règle appliquée est montrée ; il existe toujours un seul compteur.
7. Recette : « adresse manquante » en double pour chaque variable.

## 5. Tests exécutés

274 tests, tous réussis (5 ignorés : ils exigent Windows ou des fichiers absents).

Nouveaux tests :
- `test_scenarios_industriels.py` : 13 scénarios dont les signaux attendus sont écrits avant la génération :
  - HV à 2 fins de course, et HV à 1 fin de course ;
  - EV commandée et EV non commandée ;
  - pompe commandée et pompe non commandée ;
  - débitmètre analogique avec impulsions, et débitmètre sans impulsions ;
  - niveau analogique ;
  - cuve DA ;
  - architectures M340 et M580 (implantation, absence de doublon d'adresse, relecture du XSY) ;
  - S4W indicatif ;
  - conservation des adresses à la réouverture.
- `test_audit_referentiel.py` : constats du catalogue livré, détection des cas de la V1.1 (défaut de manœuvre
  sans ordre), doublon, règle inapplicable, référentiel figé puis adopté (adresses conservées).

Parcours navigateur (Playwright, 1440 × 900) :
- création de l'ouvrage, 5 équipements, puis refus de validation avec le message attendu ;
- motif vide refusé, puis TS_DISC retenue et TS_INT écartée avec motif, puis validation ;
- écrans Ouvrage, Référentiel et Recette ;
- aucune erreur JavaScript.

## 6. Ce qui reste à réaliser

1. **Arbitrages de l'exploitant**, détaillés dans `AUDIT_REFERENTIEL.md` :
   - les seuils TB / B / H / TH générés d'office pour LT, PT, AT et DA doivent-ils passer en option ?
   - l'option « Avec totalisateur » de FT n'a aucun effet ;
   - les défauts de mesure de ES_POS (MV), ES_FREQ (PM) et TM_TEMP (AR) sont à définir.
2. Implantation S4W et export S4W-Tools : il faut un fichier S4W-Tools de référence.
3. Export TOPKAPI : il faut les fichiers décrits dans `TOPKAPI_FICHIERS_A_FOURNIR.md`.
4. Mode brouillon des livrables : les exports ne sont pas encore bloqués tant que la recette contient des erreurs.
   Ils sont aujourd'hui seulement signalés comme non qualifiés.

## 7. Qualifications industrielles encore nécessaires

| Vérification | Python (fait) | Essai réel (à faire) |
| --- | --- | --- |
| Informations attendues, décisions, absence de doublon | oui | — |
| Format XSY / TXT d'E/S et de variables | relecture et réécriture identiques à vos exports CE | import dans Control Expert V14.1 |
| Adresses %I / %Q / %IW / %MW sans conflit | oui | génération de l'application dans Control Expert |
| Références de cartes et de racks Schneider | catalogue cohérent | confirmation des références (catalogue « à confirmer ») |
| Poste S4W | dimensionnement indicatif | configuration S4W-Tools |
| Supervision | libellés de 40 caractères au plus | import SOFTLINK dans une copie d'application TOPKAPI 6.3 |
| Logique des informations calculées (discordance, défauts) | texte de la logique fourni | programmation et essais sur site |
