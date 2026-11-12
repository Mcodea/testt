# Qualification Control Expert — environnement et preuves attendues

État : **en attente de preuves utilisateur**. Aucun import industriel validé.

| Champ | Valeur connue / à renseigner lors de l'essai |
| --- | --- |
| Logiciel cible | EcoStruxure Control Expert **14.1** (version indiquée par l'utilisateur) |
| Build exact, correctifs, langue | À relever dans À propos |
| Windows | Version et architecture du poste d'essai à relever |
| Automate | M340 ou M580 ; référence CPU et firmware à relever |
| Matériel | Références des racks/cartes, emplacements, nombre de voies et mode topologique/DDT à relever |
| Projet d'essai | Copie isolée fictive ou anonymisée, jamais un projet d'exploitation |
| OGIAS | Version et commit indiqués dans le lot de fichiers à importer |
| Date et validateur | À renseigner après les essais |

## Premier lot à fournir : référence native CE 14.1

Sur un projet de test hors exploitation dans Control Expert 14.1 :

1. Relever les informations ci-dessus et conserver une capture de la version du
   logiciel. Ne pas inclure de numéro de licence, compte, adresse réseau ou nom
   d'ouvrage réel.
2. Exporter depuis l'éditeur des données une petite table de variables en XSY,
   puis en TXT et SCY si ces formats sont proposés par cette installation.
   Conserver les octets originaux, l'encodage et les fins de ligne.
3. Couvrir dans la table fictive : BOOL, INT, DINT, REAL, variable sans adresse,
   variable mémoire, commentaire avec accents et caractères XML, valeur initiale,
   réserve physique lorsque disponible. Les adresses sont choisies et vérifiées
   dans le projet d'essai CE, jamais déduites d'un exemple OGIAS.
4. Pour les E/S physiques, fournir une capture ou un inventaire anonymisé des
   modules et positions réellement configurés. Un fichier de variables seul ne
   recrée pas le matériel de l'automate.
5. Si les structures DDT doivent être couvertes, exporter un exemple avec instance,
   définition et membres ; garder les adresses ou chemins tels qu'ils sortent de
   CE. Ne pas fabriquer l'adresse d'un membre depuis celle de son parent.
6. Refaire les exports pour l'autre famille M340/M580 si sa qualification fait
   partie du périmètre visé. Un résultat M340 ne prouve pas un résultat M580.

À ramener sous `references/` :

- `CE141_<famille>_reference.xsy` ;
- les `.txt` et `.scy` correspondants si disponibles ;
- `CE141_<famille>_materiel.csv` ou PDF/captures anonymisées de la configuration ;
- `ENVIRONNEMENT_ESSAI.md`, copie renseignée de la présente fiche ;
- `VERSION_LOGICIEL.png`, sans identifiant ni licence visible.

## Deuxième lot : import des fichiers générés par OGIAS

Ce lot sera préparé depuis les références reçues. Il doit rester distinct des
fichiers de référence natifs.

1. Créer une copie vierge du projet d'essai avec la même configuration matérielle.
2. Importer le XSY OGIAS fourni pour cette configuration, sans conversion manuelle
   ni correction préalable du fichier. Si CE propose un choix d'import, noter le
   choix exact au lieu de supposer une valeur standard.
3. Conserver tous les messages : erreurs, avertissements, refus, adaptations et
   doublons. Un avertissement n'est pas accepté silencieusement comme compatible.
4. Comparer le nombre de variables, les noms, types, adresses, commentaires,
   valeurs initiales et voies de réserve. Contrôler les variables non localisées
   et les caractères accentués. Ne réaliser aucune mise en service ni chargement
   sur automate de production.
5. Réexporter la table importée depuis CE 14.1, au minimum en XSY et dans les
   autres formats testés si disponibles. Les différences seront analysées
   automatiquement contre les références et le lot OGIAS.
6. Refaire le scénario pour les variantes effectivement utilisées. Noter tout
   élément non testé au lieu de l'annoncer compatible.

À ramener sous `imports_ogias/<date>_<famille>/` :

- le fichier OGIAS importé **sans modification** ;
- le réexport CE `CE141_<famille>_reexport.xsy` et ses équivalents éventuels ;
- `COMPTE_RENDU_IMPORT.md` renseigné selon le modèle de ce dossier ;
- les journaux complets et captures anonymisées des messages et de la table ;
- l'empreinte SHA-256 du fichier importé et le commit OGIAS qui l'a produit.

Les fichiers natifs non anonymisables ne doivent pas être ajoutés au dépôt.
L'utilisateur peut produire directement un projet fictif respectant le même
profil. La qualification reste en attente jusqu'à examen des résultats réels.
