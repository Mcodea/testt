# Compatibilité et qualification des formats

Aucun export n'est actuellement déclaré compatible par un essai dans le logiciel
industriel réel. Les tests automatiques vérifient les comportements logiciels
sur des données synthétiques ; ils ne remplacent pas ces essais.

| Cible | Version visée | État et preuves manquantes |
| --- | --- | --- |
| Control Expert M340/M580 | **14.1** | En attente des exports natifs, environnement matériel, imports OGIAS et réexports ; procédure dans `validation/controlexpert/ENVIRONNEMENT.md` |
| TOPKAPI / SOFTLINK | **6.3**, build et options à relever | En attente d'un projet d'essai anonymisé/fictif, export natif, paramètres de pilote confirmés, journal d'import OGIAS et réexport sans perte |
| SOFREL S4W-Tools | Version exacte à fournir | En attente d'un export natif de station fictive avec boîtier/modules, identifiants réels des voies, import du fichier OGIAS, journal et réexport |

Pour TOPKAPI : relever la version, la disponibilité de SOFTLINK, le pilote et la
convention d'adressage sur la copie d'essai ; exporter les variables dans le
format natif disponible, importer le lot OGIAS correspondant sans le modifier,
conserver tous les messages et réexporter pour comparaison. Ne pas déduire les
codes de type ou une convention Modbus d'un simple numéro de mot.

Pour S4W-Tools : relever version, firmware et configuration de la station ;
exporter la configuration tabulaire du projet fictif avec ses identifiants ;
après préparation de l'adaptateur correspondant, importer le lot OGIAS sur une
copie, conserver tous les messages et réexporter. Aucune numérotation de voie
S4W n'est inventée en attendant cette référence.

Une déclaration future précisera la version exacte, la date, les fichiers et
leurs empreintes, le périmètre réellement importé et les éventuelles limites.
Un essai partiel ne qualifie pas les autres matériels, versions ou protocoles.
