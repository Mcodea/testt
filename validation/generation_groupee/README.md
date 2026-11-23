# Génération groupée des livrables (lot 6, 19/11/2026)

Dernier lot de la feuille de route inspirée de Typical Manager : un seul geste produit tous les livrables de
l'ouvrage ouvert, rangés par destination, avec un journal.

## Où

Recette et livrables > ruban « Livraison » > **Tous les livrables**. Une boîte propose les destinations (toutes
cochées) ; « Générer le zip » télécharge `<ouvrage>_livrables.zip`. Le message de fin donne le nombre de pièces
produites et non produites.

## Contenu de l'archive

| Dossier | Pièces |
|---|---|
| `01_Automate/` | E/S au format automate (XSY, TXT), table de télétransmission (XSY) |
| `02_Telegestion_SOFREL/` | rien : format SOFREL non décrit, signalé « non disponible » au journal |
| `03_Supervision/` | table TOPKAPI ; Vijeo signalé « non disponible » |
| `04_Documents/` | E/S par carte, tableau de travail, télétransmission (études), variables, cartes, nomenclature, liste des équipements (aller-retour) |
| `05_Essais/` | cahiers FAT et SAT |
| `06_Modeles_client/` | chaque modèle de la bibliothèque, rempli pour l'ouvrage |
| `00_journal.html` / `00_journal.csv` | pièce par pièce : produite (fichier, taille, SHA-256) ou non produite / non disponible, avec le motif |

## Règles

- Chaque pièce est produite par **l'export unitaire existant** : mêmes contrôles, mêmes refus, même texte de
  refus (vérifié par test). Rien n'est assoupli parce que l'export est groupé.
- Une pièce refusée ne bloque pas les autres et n'est jamais remplacée.
- Un modèle client en erreur n'est pas rempli : il figure au journal avec ses erreurs.
- Aucun format nouveau. Exports Control Expert, TOPKAPI et modèles client **non qualifiés** : le journal le dit.
- Le « Dossier de recette » existant est inchangé (aucune fonction retirée).

## Vérifications

- `tests/test_generation_groupee.py` (5) : rangement, empreintes, motifs identiques aux exports unitaires,
  choix des destinations, modèle rempli / refusé.
- `tests_web/test_coque_bureau.py::test_generation_groupee` : boîte, destination décochée absente, refus sans
  destination.
- Audit d'accessibilité : 0 contraste, 0 sans nom, 0 hors clavier.

## Captures (données fictives XTST)

- `choix_destinations_clair.png`, `choix_destinations_sombre.png` : boîte de choix.
- `apres_generation.png` : message de fin.
- `journal.png` : journal imprimable (12 produites, 4 non produites ou non disponibles).
