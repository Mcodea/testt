# Pilotage PDF de programmes existants — SOREP

## Ce qui est réalisé

Le moteur **lit uniquement les PDF disposant d'une couche de texte**. Il repère les adresses `%I`, `%Q`, `%M`, `%MW` et formes associées, les occurrences avec numéros de pages, les pages de références croisées et certains indices `R/W`. Sur **deux instructions IL directement consécutives** `LD %...` puis `ST %...`, il produit un **indice** de dépendance. Il repère les séquences de mots `%MW` sans les déclarer zones de supervision.

Les résultats peuvent être exportés en `analyse_pdf.json`, `occurrences_pdf.csv` et `bilan_pdf.txt`. **Aucune modification automatique des ouvrages ou des variables SOREP** n'est effectuée.

## Comment tester sous Windows

1. Installer les dépendances du projet dans le terminal : `py -m pip install -r requirements-qt.txt`.
2. Dans l'application, ouvrir un ouvrage **Existant** puis cliquer sur **Analyser dossier PDF (PL7)…**.
3. Choisir le PDF et consulter les pages/occurrences. Enregistrer le diagnostic séparément si utile.
4. Ou exécuter `py analyser_dossier_pl7.py "C:\\MonDossier\\programme.pdf" --sortie "C:\\MonDossier\\rapport"`.
5. Pour le dossier HABILIS public, tenter `TESTER_HABILIS_WINDOWS.bat`. Si le site bloque le téléchargement, récupérer le PDF depuis le navigateur et utiliser le point 4.

**HABILIS :** https://www.lycee-desfontaines.eu/si/sequences-ts/performance-energetique/res/dossier-technique-habilis.pdf

## Mesures de test (document inventé pour ce seul contrôle)

L'exemple `EXEMPLE_FICTIF_PL7.pdf` comporte quatre pages : sommaire, programme IL minimal, références croisées, variables. L'analyse retrouve 6 adresses distinctes, 13 occurrences, la vraie page de références croisées (p.3), 2 liens IL stricts et 1 groupe de mots consécutifs. **Ces résultats ne sont pas un score de correspondances de supervision et ne valident pas le dossier public HABILIS.**

## Limites bloquantes

- Un **PDF scanné**, sans texte sélectionnable, nécessite une préparation externe ; aucun OCR implicite.
- Les références croisées montrent des utilisations, pas une affectation sémantique entre variables. La lecture `R/W` est un indice documentaire.
- Le moteur ne reconstruit **pas** les réseaux Ladder, les schémas FBD, Grafcet, les DFB, ni les blocs fonctionnels depuis leurs représentations graphiques.
- Les mentions `%MW` consécutives ne prouvent pas une table d'échange ni une adresse TOPKAPI.
- L'extraction et la localisation des symboles sont à contrôler sur la mise en page de chaque éditeur PL7. Les tableaux complexes ou éclatés sur plusieurs colonnes peuvent être mal récupérés.
- **Pas de taux de réussite industriel** tant qu'un corrigé de référence indépendant n'est pas produit à partir d'un dossier réel.

## Ajout : suivi d'affectations `OPERATE` et symboles

Le moteur extrait désormais, **en tant qu'indices documentaires seulement**, les expressions imprimées du type `OPERATE` suivi de `%MW10:=%IW0.2/10`, ou des tableaux `REPERE / SYMBOLE / COMMENTAIRE` sur lignes séparées.

Fichier fictif reproductible : `EXEMPLE_FICTIF_OPERATE_PL7.pdf` ; générateur : `generer_exemple_operate.py`. Rapport produit : dossier `RESULTATS_OPERATE`, avec `affectations_pdf.csv`, `symboles_pdf.csv` et `traces_cible.json`.

Exemple de commande : `py analyser_dossier_pl7.py validation/pdf_pl7/EXEMPLE_FICTIF_OPERATE_PL7.pdf --sortie validation/pdf_pl7/RESULTATS_OPERATE --cible "%MW11"`.

Cela **ne vaut ni preuve de l'état du procédé ni attestation d'accès TOPKAPI**. Les pages Ladder et FBD restent à vérifier par l'automaticien. La validation réelle doit être faite sur le PDF HABILIS téléchargé et conserver un corrigé indépendant du moteur.
