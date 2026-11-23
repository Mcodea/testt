# Modèles de livrables à variables (lot 1)

C'est l'idée centrale reprise de Typical Manager (ses « typicals »), adaptée aux règles d'OGIAS : **le format vient
d'un fichier de l'outil du client, OGIAS ne fait que le remplir.**

Cela règle le blocage des exports :
- OGIAS n'invente aucun format SOFREL, TOPKAPI, Vijeo ou Control Expert ;
- un livrable produit ainsi est « conforme au modèle fourni », à essayer dans l'outil cible, jamais présenté comme
  « compatible ».

## Utilisation

1. **Préparer le modèle.** Prendre un fichier produit par l'outil : import de supervision, table d'automate, CSV,
   texte, XML… Remplacer les valeurs par des variables `<#NOM#>` et encadrer ce qui se répète par des blocs.
2. **L'importer** dans Standards d'ingénierie › Modèles de livrables › « Importer un modèle… ».
   - OGIAS montre l'état de chaque variable (portée, signification) et le contenu du fichier.
   - Une variable inconnue, ou placée hors de sa portée, est signalée. Le modèle est gardé, mais il ne se génère
     pas tant qu'il n'est pas corrigé.
3. **Générer** dans Recette et livrables › « Vos modèles » : un fichier par modèle, rempli pour l'ouvrage ouvert.

« Variables disponibles » liste tout ce qu'OGIAS sait remplir (ouvrage, équipement, variable, E/S, compteur).

## Syntaxe

| Élément | Exemple | Effet |
| --- | --- | --- |
| Variable | `<#REPERE#>` | Remplacée par la valeur ; portée vérifiée à l'import |
| Bloc répété | `<#DEBUT_VARIABLES#>…<#FIN_VARIABLES#>` | Une fois par variable (EQUIPEMENTS, VARIABLES, ES) |
| Filtre | `<#DEBUT_VARIABLES_TS#>…<#FIN_VARIABLES_TS#>` | Seulement la famille TS (TS, TC, TM, TR, RTR, CP ; ES : ET, ST, EA, SA) |
| Imbrication | VARIABLES ou ES dans EQUIPEMENTS | Seulement les éléments de l'équipement en cours |
| Compteur | `<#N#>` | Rang dans le bloc (1, 2, 3…) |

Une balise de bloc seule sur sa ligne n'ajoute pas de ligne au résultat.

## Garanties

- **Encodage** : il est conservé (UTF-8 ou Windows-1252, comme les fichiers des outils Windows). Un caractère
  impossible à écrire dans l'encodage du modèle est refusé, avec sa valeur.
- **Échappement** : au choix, aucun (texte brut) ou XML (`& < > " '`).
- **Fichiers acceptés** : texte seulement pour l'instant, 2 Mo au plus. Les documents Word viendront avec les
  cahiers d'essais (lot 3).
- **Bibliothèque** : elle est stockée dans le dossier de données de l'atelier, avec une écriture atomique. Aucun
  modèle n'est installé d'office ; l'exemple CSV s'ajoute sur demande.
- **Données d'ouvrage** : aucun ouvrage n'est modifié par la bibliothèque ni par la génération.

## Exemples neutres

Dans le dossier `exemples/`. Ce ne sont les formats d'aucun outil : ils montrent le principe sur l'ouvrage fictif
XTST.

| Fichier | Contenu |
| --- | --- |
| `exemple_liste_variables.csv` | Une ligne par variable (c'est aussi « Ajouter l'exemple CSV ») |
| `exemple_fiche_par_equipement.txt` | Blocs imbriqués et filtres |
| `resultat_XTSTRV01_Fiche_fictive_par_equipement.txt` | Ce que produit le modèle précédent |

Les modèles réels arriveront quand vous fournirez un fichier de vos outils. Une fois anonymisé, il servira d'essai
de non-régression.

## Vérifications

- 795 essais du moteur, dont `tests/test_modeles_livrables.py` (10 essais) ;
- 111 essais navigateur, dont `test_modeles_de_livrables` ;
- ruff, mypy ;
- audit des données : 0 détection ;
- accessibilité : 0 écart.
