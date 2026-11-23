# OGIAS — Guide de l'administrateur

Ce guide s'adresse à la personne qui installe OGIAS, sauvegarde les données de l'atelier et assure le support. Il
décrit le comportement réel de la version en cours (voir `CHANGELOG.md`). Le manuel de l'utilisateur est
`MANUEL_UTILISATEUR.md`.

## 1. Installation

### Version portable Windows (recommandée)

- Archive `OGIAS_portable_<version>.zip`, accompagnée de sa somme SHA-256. Vérifiez la somme avant de décompresser :
  `Get-FileHash .\OGIAS_portable_<version>.zip -Algorithm SHA256` sous PowerShell.
- Décompressez le dossier `OGIAS` où vous voulez (pas besoin de droits administrateur). Il contient son propre Python
  (`runtime/`), le programme et le lanceur `OGIAS.bat`.
- Double-cliquez sur `OGIAS.bat`. OGIAS démarre un serveur local et ouvre l'interface dans une fenêtre Edge ou Chrome
  (à défaut, dans le navigateur par défaut).
- Aucune connexion réseau n'est nécessaire, ni à l'installation ni à l'usage.

### Depuis les sources (développement)

`py -m sorep_web` dans le dossier du dépôt, après `py -m pip install -r requirements-runtime.lock`.

## 2. Sécurité du poste

- Le serveur n'écoute que sur `127.0.0.1` (le poste lui-même) : il n'est pas joignable depuis le réseau.
- Il refuse les requêtes d'un autre site ouvert dans le navigateur (contrôle de l'origine et de l'hôte) et les
  requêtes de plus de 50 Mo.
- OGIAS n'effectue aucun appel réseau sortant.
- Les classeurs Excel contenant des formules sont refusés à l'import du référentiel.

## 3. Où sont les données

Les données sont **séparées du programme** : remplacer le dossier `OGIAS` par une nouvelle version ne touche jamais
aux ouvrages.

Dossier de données par défaut :

- Windows : `%LOCALAPPDATA%\SOREP\GenerateurVariables_Atelier`
- Linux : `~/.local/share/SOREP/GenerateurVariables_Atelier`

La variable d'environnement `SOREP_DATA_DIR` choisit un autre dossier (par exemple un dossier partagé par l'atelier,
voir § 5).

| Élément | Contenu |
| --- | --- |
| `Projets/*.ouvrage.json` | Les ouvrages. |
| `Projets/*.ouvrage.json.bak` | L'avant-dernière version de chaque ouvrage (enregistrement automatique). |
| `Projets/*.avant-<opération>-<date>-…` | Copies horodatées avant chaque opération lourde, restaurables. |
| `Projets/*.ouvrage.json.verrou` | Verrou de l'ouvrage ouvert (voir § 5). |
| `Referentiel/` | Référentiel métier : révisions publiées et brouillon. |
| `referentiel_identification.json` | Listes de l'atelier : lieux, types d'ouvrage, automates, protocoles, supervisions, IHM. |
| `standards_ingenierie.json` | Standards d'ingénierie des clients (chartes, plans d'adressage, chaînes d'outils). |
| `attributs_equipements.json` | Attributs d'équipement de l'atelier. |
| `gammes_materiel/` | Gammes de matériel déclarées par l'atelier. |
| `formats_appris/` | Formats d'export appris (et classeurs gabarits des formats Excel). |
| `modeles_livrables/` | Modèles de livrables de l'atelier. |
| `Exports/` | Fichiers exportés. |
| `journal.log` (+ `journal.1.log`, `journal.2.log`) | Journal technique (§ 6). |

## 4. Sauvegarde et restauration

- **Sauvegardez le dossier de données complet**, de préférence chaque jour, avec l'outil de sauvegarde de
  l'entreprise. Il contient tout ce qui est propre à l'atelier : ouvrages, référentiel, standards, gammes, formats.
- Restaurer un ouvrage : copier le fichier `.ouvrage.json` sauvegardé dans `Projets/`, OGIAS fermé.
- Revenir sur une opération lourde (adressage, implantation, import, adoption d'un référentiel…) : depuis l'ouvrage,
  les copies horodatées sont proposées à la restauration ; la restauration crée elle-même une copie de l'état courant.
- Dernière modification d'un ouvrage : `Ctrl+Z` dans OGIAS (30 pas, ouvrage ouvert).

## 5. Travail à plusieurs

- Plusieurs utilisateurs peuvent partager un même dossier de données (`SOREP_DATA_DIR` sur un partage réseau).
- **Un ouvrage n'est jamais modifié par deux OGIAS à la fois.** À l'ouverture, OGIAS pose un verrou
  (`<ouvrage>.verrou` : poste, utilisateur, heure, aucune donnée de l'ouvrage). Un second OGIAS est refusé avec ces
  informations.
- Verrou d'un OGIAS arrêté brutalement sur **le même poste** : repris automatiquement à la réouverture.
- Verrou d'**un autre poste** : OGIAS propose de reprendre l'ouvrage, après confirmation. Le poste qui le perd ne
  peut plus enregistrer ; prévenez son utilisateur avant de reprendre.
- Verrou resté après une panne d'un autre poste et impossible à reprendre : OGIAS fermé partout, supprimez le
  fichier `.verrou` correspondant.

## 6. Journal technique et assistance

- `journal.log` dans le dossier de données, consultable dans OGIAS par **Aide › Journal technique**.
- Il enregistre les démarrages (version, Python, système), ouvertures, créations, fermetures, exports, reprises de
  verrou, annulations et erreurs inattendues avec leur trace technique. Aucune donnée d'ouvrage n'y est écrite
  volontairement (ni repère, ni nom de fichier).
- Renouvelé au-delà de 1 Mo : `journal.1.log` puis `journal.2.log` sont gardés.
- Pour une demande d'assistance, joignez `journal.log` et le numéro de version (Aide › À propos).
- L'utilisateur ne voit jamais d'erreur technique brute : une erreur inattendue s'affiche comme « Erreur inattendue :
  le détail est enregistré dans journal.log ».

## 7. Mise à jour

1. Fermez OGIAS sur le poste.
2. Sauvegardez le dossier de données (§ 4).
3. Remplacez le dossier du programme `OGIAS` par celui de la nouvelle version.
4. Relancez `OGIAS.bat`.

Les ouvrages, le référentiel et les bibliothèques de l'atelier sont conservés. Une nouvelle révision du référentiel
livrée n'est jamais appliquée en silence aux ouvrages existants : chacun garde sa révision figée tant qu'on ne
l'adopte pas, avec aperçu et confirmation.

## 8. Qualification des exports

OGIAS ne déclare aucun format « compatible » sans essai réel dans le logiciel cible (`COMPATIBILITE.md`). Les formats
d'export appris sont qualifiés format par format, après un premier import réel confirmé dans OGIAS
(`validation/formats_appris/README.md`).

## 9. Licences

OGIAS : tous droits réservés (`LICENCE.md`). Composants tiers : `LICENCES_TIERCES.md`.
