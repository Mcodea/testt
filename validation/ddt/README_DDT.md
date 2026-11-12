# Contrôle de la lecture XSY / DDT de SOREP

## Ce qui a changé

Un export XSY peut contenir des instances DDT dans `dataBlock` et les définitions
`DDTSource` de leurs structures. L'import de SOREP construit maintenant la liste
des variables principales **et** des feuilles DDT, y compris les structures imbriquées.
Il préserve le type, le commentaire, le parent, son adresse et l'attribut `ExtractBit`.

**Ne pas confondre :**
- `IO_BALLUFF_A1_F0` à `%MW500` : adresse de l'instance principale dans cet exemple ;
- `IO_BALLUFF_A1_F0.IN.I_VERIN_1_BRIDAGE_AVANCE` : chemin de champ DDT ;
- `ExtractBit=0` : attribut de définition du champ, pas une adresse mémoire ;
- Adresse Modbus du champ : **non calculée / non validée**.

Les champs DDT sont initialement **hors sélection pour la supervision**. Ils sont
consultables et peuvent être proposés par l'assistant hybride, mais l'association
métier et l'acquisition TOPKAPI doivent être vérifiées. Le moteur ne produit
aucun lien Modbus implicite.

## Tester rapidement sans Internet

Depuis la racine du projet :

```
py -m unittest discover -s tests -v
py validation/ddt/verifier_xsy_github.py validation/ddt/exemple_DDT_reconstitue.xsy
```

Le fichier `exemple_DDT_reconstitue.xsy` est un exemple **synthétique** basé sur
les formes de balises observées publiquement, **pas** le fichier de GitHub original.

## Tester sur le fichier GitHub réel

- Fichier public : https://github.com/tonycab/XSY_To_CSV_XML/blob/main/InputFile.XSY
- Télécharger `InputFile.XSY` et le déposer dans `validation/ddt/`, puis double-cliquer
  sur `VERIFIER_FICHIER_GITHUB.bat`.
- Sinon, la commande essaie le téléchargement en ligne.
- Résultats : `validation/ddt/resultats/rapport_lecture_xsy.json` et `champs_ddt.csv`.

Le diagnostic vérifie la présence des champs, leur persistance après sauvegarde et
la non-création d'adresses de communication fictives. Il **ne démontre pas**
la compatibilité de lecture/écriture dans TOPKAPI, OFS ni Control Expert.

## Limites contrôlées

- Tableaux, structures absentes, types non reconnus, DDT cycliques : avertissements
  d'import et conservation des éléments interprétables, sans suppression silencieuse.
- Une absence de DDTSource empêche d'expliquer les membres du type ; le parent reste visible.
- Des champs de type complexe ne sont pas transformés en variables simples.
- L'outil n'invente ni offsets, ni adresses, ni accès OPC.
- Les tests d'interface PySide6 doivent être exécutés sur un poste Windows adapté.

## Vérification documentaire d'une acquisition DDT

Depuis **Projet existant**, choisir le champ DDT et ouvrir **Modifier correspondance** :
- sélectionner l'équipement et la fonction du catalogue ;
- renseigner **l'adresse ou le tag d'acquisition vérifié** (ne pas copier l'adresse du parent) ;
- sélectionner le protocole, puis cocher la confirmation documentaire **uniquement après contrôle**.

La ligne passe au vert si les contrôles métier sont satisfaits ; cela **ne remplace pas**
un essai de communication réel dans TOPKAPI/OFS. En cas de changement d'adresse
parent ou de définition au réimport, la confirmation documentaire est retirée,
mais les champs manuels sont conservés pour comparaison.
