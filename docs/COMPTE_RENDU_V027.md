# OGIAS V0.27 — Compte rendu (9 novembre 2026)

Trois demandes traitées :
1. Le référentiel en Excel (exigence prioritaire).
2. Le moteur d'adressage automatique.
3. L'analyse du projet TOPKAPI réel.

Le projet TOPKAPI a été étudié sur une copie isolée. Aucune de ses données (noms, libellés, adresses) n'est
intégrée à OGIAS ni à ses tests.

## 1. Référentiel ↔ Excel (`genvar/referentiel_excel.py`, écran Référentiel)

| Exigence | Réalisation | Preuve |
| --- | --- | --- |
| 1. Tout exporter | Classeur de 8 onglets : Lisez-moi, Types, Signaux (E/S physiques, TS/TM/TC/TR/RTR/CP, informations calculées), Règles, Types de modèles, Modèles, Lignes de modèles, Valeurs | export complet de 51 types, 360 signaux et 64 règles |
| 2. Obligatoire / défaut / option / règle | colonne Présence (liste fermée) | listes déroulantes |
| 3. Règles conservées | onglet Règles : Si / Propose / Mode / Logique automate | aller-retour sans perte |
| 4. Ajout et modification | ajout de lignes ; suppression seulement avec « Supprimer = Oui » | test ajout, modification et suppression |
| 5. Classeur professionnel | 9 listes déroulantes par onglet tabulaire, volets figés, filtres, onglet Valeurs | relu par openpyxl et par OGIAS |
| 6. Identifiants stables | type, TYPE.FAMILLE_CODE, ID règle, ID modèle, ID ligne ; un renommage d'identifiant est refusé | test |
| 7. Contrôles avant import | doublons, références manquantes, types et natures, cohérence E/S ↔ télétransmission, ligne disparue (bloquant) | test des contrôles bloquants |
| 8. Aperçu des différences | ajouts, suppressions et modifications, avec les ouvrages concernés ; rien n'est appliqué sans confirmation | API d'import |
| 9. Ouvrages protégés | référentiel figé dans chaque ouvrage ; adoption explicite (V0.26) | test |
| 10. Révisions | chaque application archive la révision précédente, restaurable | écran Révisions |
| 11. Aller-retour | export puis réimport sans modification : 0 différence ; idem après réenregistrement par Excel / openpyxl | tests |
| 12. Source de vérité | JSON interne versionné ; Excel n'est qu'une interface d'échange ; une règle qui exige un algorithme reste décrite en texte, jamais exécutée depuis Excel | conception |

## 2. Moteur d'adressage (`genvar/adressage.py`, écran Variables › Adressage automatique)

### Audit de l'existant

Avant cette version, trois mécanismes séparés pouvaient diverger :
- l'implantation des voies (`cartes_es.implanter`, étape Matériel) ;
- le plan %MW (`modele.plan_adresses`) ;
- l'adressage protocolaire, qui n'existait pas.

Le moteur les réunit derrière **un seul point d'entrée** (`calculer` puis `appliquer`). Il réutilise les
algorithmes qualifiés au lieu de les dupliquer.

### Trois niveaux, jamais confondus

| Niveau | Contenu |
| --- | --- |
| Physique | équipement · signal · contrôleur · carte · voie · %I / %Q / %IW / %QW |
| Automate | variable d'échange · %MW (BOOL = un bit, INT = un mot, DINT/REAL = deux mots alignés) ; une variable interne ne prend aucune voie |
| Télétransmission | point (identifiant = variable, jamais deux fois) · adresse protocolaire · variable source |

L'adresse protocolaire n'est calculée que si l'automaticien déclare la convention « registre = mot %MW + décalage ».

### Règles de fiabilité

- **Deux phases.** L'aperçu ne modifie rien. L'application exige l'empreinte du plan montré et refuse s'il reste
  un conflit.
- **Tout ou rien.** Le fichier de l'ouvrage est sauvegardé avant l'application ; en cas d'erreur, l'ouvrage est
  restauré.
- **Aucun déplacement.** Une adresse existante ou validée n'est jamais déplacée.
- **Réservations respectées.** Voies, plages mémoire et points réservés ne sont pas utilisés sans décision.
- **Rien d'inventé.** Une donnée manquante laisse l'affectation « non résolue », avec l'information qui manque.
- **Simulation.** Les cartes manquantes sont calculées mais jamais ajoutées.
- **Traçabilité.** Chaque affectation garde son origine (importée, proposée, saisie), la règle appliquée, et la
  date et l'auteur de sa validation.
- **Projet existant.** Aucune réaffectation. Aucune nouvelle adresse tant que la disponibilité de la mémoire
  n'est pas attestée (« disponibilité non vérifiée »).
- **Ordre documenté et déterministe.**
  - Équipements dans l'ordre de l'arbre (type, puis numéro).
  - Signaux dans l'ordre du référentiel.
  - E/S d'un équipement groupées sur une carte : si elles ne tiennent pas en entier, elles ne sont pas coupées
    et restent non résolues.
  - Cartes par rack, puis par position.
  - Familles %MW dans l'ordre TR, TS, TC, TM, CP, RTR.

### Scénarios de qualification (`tests/test_moteur_adressage.py`, 13 tests, attendus écrits à la main)

| Scénario | Vérifié |
| --- | --- |
| A — M340 | voies attendues (%I0.1.0 à 6, %Q0.2.0 à 3, %IW0.3.0) ; E/S groupées par équipement ; variables calculées sans voie ; justification de chaque adresse ; aucun chevauchement ; déterminisme |
| B — M580 | CPU sur les positions 0 et 1, jamais de carte dessus ; BOOL sur un bit ; 32 bits sur adresse paire ; TR/RTR en miroir. **E/S distantes EIO non prises en charge** (pas de catalogue vérifié) |
| C — S4W | rien n'est proposé : physique, mémoire et points restent non résolus avec leur motif (numérotation S4W-Tools inconnue) |
| D — Existant | adresses historiques intactes ; aucune proposition sans disponibilité vérifiée, puis aucune proposition sur un mot historique ; conflit introduit détecté |
| E — Modifications | réservations respectées ; ajout puis retrait d'un équipement sans décalage ; réexécution sans changement ; adresse validée non écrasée |
| F — Robustesse | saturation et manque de voies analogiques, avec simulation des cartes ; adresse déjà utilisée (application refusée) ; plan périmé ; coupure simulée pendant l'application (rien de partiel) ; automate non renseigné ; réservations illisibles ; convention protocolaire ; persistance des affectations et des traces |

## 3. Projet TOPKAPI réel — constats (copie de travail, données non reproduites)

- Il s'agit d'une sauvegarde complète d'application multi-stations. On y trouve :
  - des fichiers d'import de variables `.$$t` « Version 1 » (70 fichiers, 38 colonnes tabulées, Windows-1252, CRLF) ;
  - des tables de variables par station `.imp` « Version 2 » (41 colonnes) ;
  - une table des stations `.api` (plages de mots et de bits, fichier source de l'import) ;
  - des variables calculées `.txt` (formules).
- La table des stations indique que l'import a été fait à partir d'un fichier de symboles automate **PL7 (.scy)**.
- Les 70 fichiers `.$$t` sont relus et réécrits par OGIAS **à l'octet près**.
- Adresse = numéro de mot, ou mot$bit avec le bit en hexadécimal.
- Codes de format relevés :
  - 0 : bit ;
  - 2 : mot ;
  - 102 : compteurs (temps de fonctionnement, nombres de démarrages), probablement un entier 32 bits ;
  - 105 : mesures électriques, probablement un réel 32 bits.

  102 et 105 sont toujours sur adresse paire. Leur sens reste à confirmer : OGIAS ne les écrit pas.
- Export OGIAS → `.$$t` disponible, **non qualifié** : il exige la convention déclarée et refuse tout conflit.

## 4. Formats

| Format | Statut |
| --- | --- |
| Control Expert XSY / TXT (E/S et variables) | identique aux exports CE V14.1 reçus ; **import dans Control Expert non essayé** |
| TOPKAPI `.$$t` Version 1 | lu et réécrit sans perte sur un projet réel ; **import TOPKAPI 6.3 non essayé** |
| Référentiel Excel OGIAS | format propre à OGIAS, aller-retour vérifié |
| SOFREL S4W-Tools | non produit (fichier de référence attendu) |
| TOPKAPI `.imp`, `.api`, `.txt` | identifiés, non produits |

Aucun format n'est déclaré qualifié.

## 5. Limites restantes

1. Import réel du `.$$t` dans une copie TOPKAPI 6.3, et confirmation des codes 102 et 105.
2. Convention « adresse TOPKAPI = indice du %MW » : à confirmer pour vos stations M340/M580. Le projet de 2008
   était en PL7.
3. S4W : implantation et identification des points dans S4W-Tools (export de référence attendu).
4. M580 : E/S distantes (EIO) et DDT d'équipement non pris en charge.
5. Projet existant : la proposition de nouvelles adresses suppose que l'import couvre toute la mémoire ; c'est
   l'automaticien qui l'atteste.
6. Les télécommandes du projet de référence sont des mots entiers ; celles d'OGIAS sont des bits. La convention
   d'exploitation est à arbitrer.

## 6. Inspiration LINA (modèles de structure)

Trois idées retenues pour la suite, rien n'est implémenté :
1. Le modèle d'équipement OGIAS devient une « structure » : un type de variables par modèle, instancié par
   équipement (proche des DDT).
2. Les bits regroupés dans un mot (BIT dans INT), comme le fait déjà le plan %MW.
3. L'import des structures par fichier à colonnes configurables.
