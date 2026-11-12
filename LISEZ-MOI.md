# OGIAS — Outil de Gestion des Informations d'Automatisme et de Supervision — V0.32

OGIAS part de l'inventaire codé des équipements d'un ouvrage pour produire, par règles écrites, les E/S
physiques, les cartes, les variables automate et les informations de télétransmission. Aucune
intelligence artificielle, rien d'inventé : l'outil propose, l'automaticien valide.

## Nouveautés V0.32 (version stable de travail)

Référentiel V2 : adoption contrôlée type par type (aperçu, confirmation, sauvegarde, retour arrière,
adresses conservées), noms physiques harmonisés (`ET_MV01_OUV` / `TS_MV01_OUV`), CT consolidé dans FT,
règles documentaires sans algorithme imposé, lexique, dictionnaire des codes et correspondances,
versions par profil et état de synchronisation, rapport d'impact multi-ouvrages et journal des décisions,
variables internes déclarées (BI, EI, MI, RI) sur sélection, contrôle des homonymes. Détail :
`docs/NOTES_VERSION_0.32.md`. Les exports industriels restent **non qualifiés** tant que les essais
dans Control Expert, SOFREL S4W et TOPKAPI ne sont pas faits.

## Interface V0.30

Nouvelle fenêtre locale au style OGIAS : barre de titre, ruban contextuel, onglets de documents,
arborescence et inspecteur repliables, jalons des cinq étapes, thème clair/sombre mémorisé.
Les icônes SVG sont incluses dans les fichiers locaux ; les polices sont celles du poste
Windows (Segoe UI Variable et Consolas, avec polices système de secours). Aucune requête
réseau n'est requise. Voir `docs/COMPTE_RENDU_V030.md` pour la matrice de conservation
des fonctions, les essais et les limites de qualification.

## Démarrer

1. Extraire l'archive dans un **nouveau dossier** (garder une copie de la version précédente et de ses données).
2. Double-cliquer **OGIAS.bat** (Python 3.11 ou plus récent, rien d'autre à installer).
   OGIAS s'ouvre dans sa propre fenêtre (Edge ou Chrome en mode application), à défaut dans un onglet.
3. Une seule fois : **CREER_RACCOURCI_OGIAS.bat** crée un raccourci OGIAS avec son icône sur le Bureau et
   dans le menu Démarrer ; clic droit sur le raccourci > *Épingler à la barre des tâches*.
4. Vérification facultative : **VERIFIER_SUR_WINDOWS.bat** lance les tests automatiques.

Les ouvrages sont enregistrés automatiquement dans le dossier *Projets* indiqué sur la page « Mes ouvrages ».

## Parcours d'un projet neuf (5 étapes)

| Étape | Ce qu'on fait | Terminé quand |
| --- | --- | --- |
| 1 Équipements | fiche ouvrage, UF, équipements, modèles ; validation du paramétrage | tous les équipements validés |
| 2 Liste des E/S | contenu des E/S physiques : nature, sens du contact, désignation | toutes les E/S validées |
| 3 Matériel | OGIAS **calcule** racks et cartes (réserve 20 %) ; ajustement, validation ; implantation sur les voies ; exports de la liste d'E/S | matériel validé, voies validées |
| 4 Variables | table d'échange automate ; onglet Télétransmission et supervision | adresses validées |
| 5 Recette | contrôles consolidés, livrables | aucune erreur |

La barre d'étapes montre l'état de chaque étape (✓ validée, orange en cours, gris à faire) ; chaque écran
se termine par « précédent / étape suivante » avec ce qui reste à faire.

## Matériel (étape 3)

- **Plateforme** prise dans la fiche ouvrage (champ Automate) : M340 (défaut), M580, ou SOFREL S4W.
- **Schneider M340 / M580** : densité par défaut 64 voies TOR / 8 voies analogiques (BMX DDI 6402K,
  DDO 6402K, AMI 0810, AMO 0802), modifiable (32/8, 16/4). Voies utiles = 80 % de la carte ; rack le plus
  court contenant le CPU et les cartes ; racks d'extension au-delà. Catalogue : `genvar/data/materiel_schneider.json`
  (références à confirmer).
- **SOFREL S4W** : boîtier le plus petit (Small, Medium, Large) dont les voies intégrées et les extensions
  couvrent le besoin, d'après votre catalogue (`genvar/data/materiel_sofrel_s4w.json`, fiche LACROIX DC54).
  Proposition **indicative** : l'implantation et l'export S4W-Tools attendent un fichier S4W-Tools de référence.
- Les cartes se modifient en cliquant dessus ; toute modification remet le matériel « à valider ».

## Codification (charte ESB / RESO du 9 novembre 2026)

- **Lieu** = commune, 4 lettres tirées du nom par règle : Athis-Mons → ATMS, Morangis → MRGS
  (exception écrite : Cachan → CACH). Dans *Gérer les listes… > Lieux*, le code est proposé dès que l'on
  tape le nom de la commune ; un code déjà pris est refusé avec des variantes libres.
- **Code ouvrage** = lieu + type d'ouvrage + numéro : ATMSRV01.
- **Repère d'équipement** = code ouvrage + type + numéro, **12 caractères, sans sous-ensemble** : ATMSRV01HV01.
  Le numéro est unique par type dans l'ouvrage ; le sous-ensemble reste un regroupement facultatif.
- **Noms automate** (sans le lieu, 32 caractères au plus) : ET_RV01HV01_FDC_OUV, TS_RV01HV01_OUV.
- Les ouvrages enregistrés avant la charte gardent leurs repères : **aucun renommage automatique**.
- Les 15 communes sont préremplies avec les codes de la charte. Une installation qui contenait les
  anciennes propositions (ATHM, MORG…) les voit remplacées, **sauf** si un ouvrage enregistré utilise déjà l'ancien code.

Charte complète : document « Charte de codification ESB / RESO ».

## Statut des exports

| Export | Statut |
| --- | --- |
| E/S pour Control Expert (XSY, TXT), voies de réserve comprises | **conforme à vos exports Control Expert V14.1** : import à essayer |
| Variables (XSY) | même format ; import à essayer |
| Liste d'E/S, cartes d'E/S, table des variables (Excel) | documents de travail |
| SOFREL S4W-Tools, TOPKAPI 6.3 (SOFTLINK) | **non produits** : il faut un fichier réel de chaque format |

Vérification faite sur vos exports du 9 novembre (XSY, TXT, SCY ; le XVM est chiffré) : relus sans perte,
le TXT régénéré par OGIAS est identique octet pour octet, les lignes de variables du XSY sont identiques.

## Nouveautés V0.28

- **Une seule base** : V0.27, plus le Module 1 (import contrôlé) et le Module 2 (référentiel versionné).
- **Référentiel** : le cycle brouillon → validation → publication couvre tout le référentiel (types, signaux,
  règles, modèles). La révision publiée est en lecture seule ; les modifications se font dans un brouillon, à l'écran
  ou par Excel. Historique et restauration sous forme de brouillon. Détail : `docs/COMPTE_RENDU_V028.md`.

## Nouveautés V0.27

- **Adressage automatique** (Variables › Adressage automatique) : un seul moteur pour les voies, la table
  %MW et les points de télétransmission. Aperçu chiffré par niveau, conflits bloquants, simulation des cartes
  manquantes, réservations, conventions déclarées, application tout ou rien après sauvegarde, validation
  tracée (date, auteur, règle). Détail et scénarios : `docs/COMPTE_RENDU_V027.md`.
- **Référentiel ↔ Excel** (écran Référentiel) : export complet, modification, contrôle, aperçu des différences,
  application, révisions et restauration.
- **TOPKAPI** : lecture et écriture des fichiers d'import `.$$t` (format relevé sur un projet réel) ; export non
  qualifié depuis l'écran Adressage.

## Nouveautés V0.26

- **Informations fonctionnelles** dans la fiche de chaque équipement : TS, TM, CP, TC, TR, RTR avec leur
  état (retenue, à décider, écartée, non retenue), leur provenance (modèle, option, règle) et leur justification
  (E/S sources + logique à programmer). Une information **proposée** par une règle (ex. discordance d'une vanne
  à deux fins de course) se **retient** ou s'**écarte avec un motif écrit** : l'équipement ne peut pas être validé
  avant, et la recette signale toute information attendue non décidée.
- **États des équipements** partout (arbre, tableaux, fiche) : validé, prêt à valider, incomplet, en erreur,
  avec la raison ; les contrôles de l'équipement s'affichent dans sa fiche.
- **Référentiel V1.2** : vanne manuelle HV (discordance + position intermédiaire), électrovannes et vannes
  EV / SV / XV (plus de défaut de manœuvre sans ordre), inverseur IV, cuve DA (défaut de mesure). Détail :
  `docs/AUDIT_REFERENTIEL.md`.
- **Contrôle de conception du référentiel** (écran Référentiel) : informations calculées sans source, défaut de
  manœuvre sans ordre, entrée analogique sans défaut de mesure, seuils d'office, options sans effet, doublons,
  règles inapplicables.
- **Référentiel figé par ouvrage** : un ouvrage enregistré garde son référentiel ; la fiche de l'ouvrage signale
  une version plus récente et ne l'applique qu'après accord (équipements concernés à revalider, adresses conservées).
- **Recette** classée par étape, avec accès direct à la fiche ou à l'étape à corriger.
- E/S câblées portées par une information (contacts des types « disjoncteur », « électrovanne »…) visibles
  dans le paramétrage des E/S.
- TOPKAPI : fichiers à fournir et procédure dans `docs/TOPKAPI_FICHIERS_A_FOURNIR.md`.

## Nouveautés V0.25

- Parcours en 5 étapes : Équipements → Liste des E/S → **Matériel** → Variables → Recette.
- Liste des E/S : validation du **contenu** (nature, sens, désignation), distincte de la validation de la voie.
- Matériel : racks et cartes **calculés** depuis les E/S validées, rack visuel avec jauges de remplissage
  (vert réserve respectée, orange sous la réserve, rouge dépassement), implantation, validation.
- Exports XSY et TXT au format exact de Control Expert V14.1, voies de réserve « RESERVE » comprises.
- Lecture des exports Control Expert XSY, TXT et SCY (`genvar/formats_control_expert.py`).
- Catalogue SOFREL S4W intégré (proposition indicative de poste).

## Nouveautés V0.24

- Charte ESB / RESO appliquée : codes lieu par règle, proposition automatique, doublons refusés,
  repère d'équipement sur 12 caractères.
- Barre d'étapes lisible (libellés courts, états) et pied d'étape commun sur chaque écran.
- Corrections : écrans Variables et Recette qui ne s'affichaient pas (erreur « ind is not defined ») ;
  message d'erreur d'un écran qui restait affiché sur le suivant ; niveaux Erreur / Alerte en couleurs distinctes.
- Fenêtre d'application et raccourci Windows avec l'icône OGIAS ; un seul lanceur (OGIAS.bat).
- Notes des versions précédentes rangées dans `docs/historique/`.

## Vérifications faites / à faire

- Faites (V0.26) : 274 tests automatiques dont 13 scénarios industriels (signaux attendus écrits avant
  génération) ; parcours navigateur des informations fonctionnelles sans erreur JavaScript.
- Faites (V0.25) : 257 tests automatiques ; parcours complet dans un navigateur (création d'ouvrage, 8 équipements,
  validation des E/S, calcul du matériel, implantation, exports, variables) sans erreur JavaScript ; captures relues à 1440 et 1280 px.
- À faire : essai sur poste Windows (fenêtre d'application, raccourci) ; import réel dans Control Expert,
  S4W-Tools et TOPKAPI 6.3.
