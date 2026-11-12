# OGIAS 1.0 — Cahier des charges de la version finale

Ce document est la référence unique pour livrer OGIAS 1.0. Il est conservé dans le dépôt (`docs/CAHIER_DES_CHARGES_V1.md`) et prime sur toute consigne antérieure en cas de contradiction, sauf les contraintes permanentes (section 11), qui priment toujours.

## 1. Le produit

OGIAS (Outil de Gestion des Informations d'Automatisme et de Supervision) génère et contrôle les informations d'automatisme et de supervision d'un ouvrage d'eau :

- équipements ;
- entrées et sorties physiques ;
- matériel (cartes Schneider M340 / M580, postes SOFREL S4W) ;
- variables et table d'échange ;
- télétransmission TOPKAPI 6.3 ;
- recette.

Il couvre les projets neufs et les projets existants (import Control Expert, TOPKAPI, Excel).

Cible commerciale : régies et intégrateurs de l'eau. Le niveau attendu est celui d'un logiciel d'ingénierie professionnel vendu : stable, fiable, rapide, documenté, installable sans assistance.

## 2. Données de référence (dans le dépôt)

| Fichier | Rôle |
| --- | --- |
| `docs/referentiel/OGIAS_V031_informations_modeles.xlsx` | 740 lignes des 25 modèles (clé « ID ligne »), lexique |
| `docs/referentiel/OGIAS_V031_bibliotheque_ES_physiques.xlsx` | 193 E/S (clé « Identifiant »), dictionnaire de 81 entrées (80 codes distincts, NIV existe en nature ET et en nature EA), variantes, correspondances Schneider / SOFREL S4W |
| `docs/maquettes/OGIAS_maquette_*.png` | Référence visuelle de l'interface (tableau de bord, Variables, Variables avec panneau de détail) |
| `validation/` | Jeux de validation fictifs et leur provenance (`validation/README.md`) |
| `validation/controlexpert/` | Exports Control Expert anonymisés ou fictifs, comptes rendus d'import, réexports |

## 3. Référentiel de base

### Informations des modèles (classeur 1)

- Le référentiel livré contient exactement les 732 lignes conservées, avec le suffixe et le libellé du classeur, rapprochées par « ID ligne ». Les 8 lignes « Retiré » sont absentes.
- `_suffixe_propose` ne tronque jamais. Il utilise d'abord le code du catalogue ou du dictionnaire des E/S, puis le lexique. Un suffixe de plus de 12 caractères déclenche une alerte « suffixe à raccourcir ».
- Le lexique est un objet du référentiel : exporté, importé, versionné, modifiable dans le brouillon.
- Les noms sont en majuscules, de la forme `<Rôle>_<Repère>_<Suffixe>` (exemple : `TS_SR02AT01_HS`).

### Bibliothèque des E/S physiques (classeur 2)

- Le référentiel livré contient exactement les 193 E/S, rapprochées par « Identifiant », dont les 49 lignes « Ajouté » :
  - nouveaux types CG, UV, FI, AB, CE et DG ;
  - E/S des types FV, VV et OU ;
  - variantes manquantes des types existants.
- Les codes « Harmonisé » remplacent l'ancien code, et toutes les règles qui le citaient sont mises à jour. Aucune référence ne reste cassée.
- La télétransmission suit la colonne « Télétransmission ». Chaque variante de l'onglet « Variantes » génère exactement ses E/S.
- Le dictionnaire des codes est un objet du référentiel. Contrôles :
  - code de 2 à 9 caractères (A–Z, 0–9, « _ ») ;
  - un code non standard déclenche une alerte ;
  - deux codes pour un même libellé déclenchent une alerte ;
  - un même code avec deux sens est une erreur.
- Les correspondances Schneider / SOFREL S4W alimentent l'écran Matériel :
  - une sortie analogique sur S4W impose un module AO ;
  - une sortie TOR au-delà de 150 mA impose un relais d'interface ou un module 4DO+.
  - BMX EHC, BMX ART et l'identification des voies S4W-Tools restent « à confirmer ». Aucune adresse S4W n'est inventée.
- Le modèle « Vanne de régulation » est rattaché à FV, et « Détection de gaz » à DG.

### Migration

- Installation vierge : ce référentiel est publié comme révision 1.
- Installation existante : il est publié comme nouvelle révision, historique conservé. Les ouvrages existants gardent leur révision figée tant qu'ils ne l'adoptent pas.
- Un projet existant importé garde ses noms et adresses d'origine.

## 4. Interface

### Principes

Application moderne et haut de gamme, conforme aux maquettes :

- fond lavande doux ;
- grandes cartes blanches arrondies, sans bordure grise ;
- barre latérale indigo à icônes ;
- indigo principal, corail en contraste ;
- grands chiffres, beaucoup d'espace.

Le contenu d'abord : la donnée est l'élément le plus visible.

### Système de design (variables CSS, définies une seule fois)

- **Couleurs :**
  - fond `#EEF1FB`, cartes `#FFFFFF`, survol `#F5F7FE`, ligne sélectionnée `#EEF0FD` ;
  - barre latérale en dégradé `#4F5BD5` → `#3D47B8` ;
  - principal `#5B63E6` (teinte claire `#E4E6FB`) ;
  - corail `#F28C5B`, au plus un élément par écran ;
  - texte `#1E2340`, texte secondaire `#7A80A0`, séparateurs `#EDEFF7` ;
  - états : validé `#2BA36B` / `#E3F5EC`, à valider `#E39B2D` / `#FCF1DE`, erreur et conflit `#E0524A` / `#FCE6E4`.
- **Formes :**
  - cartes : rayon de 20 px, ombre `0 10px 30px rgba(61,71,184,.08)`, marge intérieure de 24 px ;
  - boutons et champs : rayon de 12 px, 40 px de haut ;
  - pastilles et filtres en gélule ;
  - panneaux et fenêtres : rayon de 24 px.
  - Jamais de carte dans une carte.
- **Typographie :**
  - Inter et JetBrains Mono, embarquées ;
  - échelle 12 / 13 / 14 / 16 / 20 / 32 px ;
  - noms de variables, repères et adresses en police à chasse fixe.
- **Icônes :** Lucide (licence ISC), embarquées. Jamais d'emoji.
- **Transitions :** 180 ms, sans animation décorative.

### Structure

- Barre latérale de 80 px : Accueil, Ouvrages, Référentiel, Paramètres, À propos.
- Aucun menu horizontal, ruban ou onglet de documents.
- Dans un ouvrage, les 5 étapes en gélules forment la seule navigation : Équipements → Liste des E/S → Matériel → Variables → Recette. Chaque étape affiche son état et le nombre de points à traiter.
- Le tableau de bord de l'ouvrage est la page d'arrivée :
  - indicateurs ;
  - avancement de la recette ;
  - répartition des E/S ;
  - points à traiter, avec un lien vers chacun ;
  - activité récente.
- Les écrans de travail sont faits d'une grande carte qui contient la table. Le panneau de détail glisse depuis la droite à la sélection d'une ligne et se ferme avec Échap.
- Rien d'inutile :
  - aucun compteur à zéro ;
  - aucun texte d'aide permanent (infobulle « i » ou état vide) ;
  - au plus 3 actions visibles.

### Écran Variables

- Une seule table. Colonnes : variable, famille, source, adresse automate, adresse de télétransmission, statut, règle.
- « Table d'échange » et « Télétransmission » sont des préréglages de cette table, pas des écrans séparés.
- Le bouton principal « Valider les propositions · n » est dans la table.
- Le panneau de détail propose : Valider, Saisir (avec contrôle immédiat), Déverrouiller (avec motif), Réserver.
- Un blocage (référentiel non publié, propositions non décidées, conflit) laisse le bouton visible mais désactivé, avec la raison et un lien vers la correction.
- Projet existant : les adresses importées sont validées et protégées. Aucune n'est recalculée.

### Qualité de l'interface

- Accessibilité WCAG AA et navigation complète au clavier.
- Affichage correct de 1366×768 à 2560×1440.
- Annulation (Ctrl+Z) des modifications de l'ouvrage.
- Chaque action a un retour visible : chargement, succès, erreur avec la cause et la solution.

## 5. Productivité

- Dupliquer un équipement : aucune adresse recopiée, nouveau numéro proposé.
- Dupliquer, réordonner et déplacer des lignes de variables, avec un ordre stable dans les exports.
- Sens de chaque variable (lecture, commande, consigne, retour, réserve), affiché et filtrable.
- Profils d'import Excel enregistrés et réutilisables, avec aperçu avant import.
- Création en série d'équipements d'un même type.
- Recherche globale (repère, variable, adresse, libellé).

## 6. Rapprochement hybride (projets existants)

- La précision passe avant le rappel. Aucune correspondance n'est appliquée sans confirmation humaine.
- Chaque proposition affiche son niveau de confiance et sa raison. Sous le seuil, la ligne est marquée « à rapprocher manuellement ».
- Le seuil est réglé pour qu'aucune proposition fausse connue ne passe au-dessus, sur tous les jeux de validation.
- Précision et rappel sont mesurés et publiés dans le compte rendu.
- Les confirmations (une par une, ou en lot pour les confiances élevées) sont tracées et annulables.

## 7. Fiabilité, sécurité, performance

- **Données :**
  - écriture atomique et sauvegarde automatique ;
  - copies horodatées avant chaque opération lourde, restaurables depuis l'interface ;
  - verrou d'ouvrage ;
  - reprise sans perte après un arrêt brutal.
- **Journal :** fichier tournant, sans donnée sensible, consultable dans l'interface. Aucune exception brute n'est affichée à l'utilisateur.
- **Sécurité :**
  - le serveur n'écoute que sur 127.0.0.1 ;
  - aucun appel réseau sortant ;
  - toutes les entrées sont échappées ;
  - aucun chemin hors des dossiers autorisés ;
  - les classeurs piégés (macros, liens externes, formules) sont refusés ;
  - les dépendances sont auditées, sans vulnérabilité connue.
- **Performance** (ouvrage synthétique de 300 équipements et 5 000 variables) :
  - ouverture en moins de 2 s ;
  - génération des variables en moins de 3 s ;
  - adressage en moins de 2 s ;
  - interface en moins de 200 ms, y compris le filtrage d'une table de 5 000 lignes ;
  - import de 70 fichiers .$$t en moins de 10 s ;
  - exports en moins de 5 s.
  - Un banc reproductible est dans `bench/`.

## 8. Qualification des formats industriels

- **Control Expert :**
  - les exports de référence de `validation/controlexpert/references/` (anonymisés ou fictifs) définissent le format attendu pour la version indiquée dans `ENVIRONNEMENT.md` ;
  - le XSY généré par OGIAS doit leur être équivalent ;
  - leur lecture se fait sans perte ;
  - chaque compte rendu d'import et chaque réexport de `imports_ogias/` est analysé, et tout avertissement ou toute perte est un défaut à corriger ;
  - ces fichiers deviennent des tests automatiques (génération, lecture, aller-retour).
- **TOPKAPI 6.3 et S4W-Tools :** même démarche dès que des preuves sont fournies.
- **COMPATIBILITE.md :** ne déclare compatible que ce qui a été réellement importé sans erreur dans le logiciel réel, avec la version et la date. Il liste précisément les essais restant à faire sur les logiciels réels.

## 9. Installation et documentation

- **Installation :**
  - version portable Windows 10 / 11, hors ligne, sans droits administrateur, avec un Python embarqué et un lanceur ;
  - script de construction reproductible.
- **Données :** séparées du programme. Une mise à jour (y compris depuis la V0.30 ou la V0.31) ne touche jamais aux ouvrages.
- **Installation vierge :** sans donnée de démonstration. Un ouvrage d'exemple fictif est fourni à part.
- **Documentation en français, avec captures de l'interface finale :**
  - MANUEL_UTILISATEUR (PDF et Markdown) ;
  - GUIDE_ADMINISTRATEUR ;
  - REGLES_DE_NOMMAGE, générées depuis le référentiel ;
  - CHANGELOG.md, au format Keep a Changelog ;
  - NOTES_DE_VERSION_1.0 ;
  - COMPATIBILITE.md ;
  - LICENCES_TIERCES.md.

## 10. Processus de livraison

- **Intégration continue GitHub Actions**, à chaque push et chaque pull request, sous Windows et Linux :
  - dépendances à versions figées ;
  - tests unitaires et d'intégration, avec couverture ;
  - tests navigateur (Playwright) ;
  - banc de performance bloquant ;
  - analyse statique ;
  - audit des dépendances ;
  - contrôle anti-données réelles (motifs interdits listés dans un fichier de contrôle) ;
  - construction de la version portable en artefact.
- **Qualité du code :**
  - analyse statique sans erreur ;
  - vérification des types sur le moteur ;
  - couverture d'au moins 85 % sur `genvar/`, et de 100 % sur les exports industriels ;
  - aucun code mort, fichier temporaire ou secret.
- **Branches :**
  - branche principale protégée : aucune fusion sans intégration continue verte ;
  - aucune réécriture de son historique.
- **Versions :**
  - `VERSION = "1.0.0"` défini à un seul endroit ;
  - étiquette `v1.0.0-rc1`, puis `v1.0.0` après la recette finale ;
  - release GitHub avec la version portable, sa somme SHA-256 et les notes de version.

### Critères de sortie (tous obligatoires)

1. Intégration continue verte sous Windows et Linux, sans test ignoré non justifié.
2. Tableau de conformité à ce cahier des charges (exigence, état, preuve) entièrement « fait », chaque ligne prouvée par un test.
3. Couverture, analyse statique et audit conformes.
4. Banc de performance dans les objectifs.
5. Installation sur un Windows propre depuis l'artefact : ouvrage neuf jusqu'à la recette, import d'un projet existant fictif, ouverture d'un ouvrage créé en V0.30. Captures d'écran.
6. Aucune donnée réelle ni de l'ancien exploitant dans le dépôt, les artefacts ou les captures.
7. COMPTE_RENDU_V1.0.md complet :
   - bilan ;
   - décisions prises ;
   - résultats exacts des tests et de la couverture ;
   - mesures de performance ;
   - précision et rappel du rapprochement ;
   - essais restant à faire sur les logiciels réels.

## 11. Contraintes permanentes

- Le projet réel est strictement confidentiel. Aucune donnée réelle n'entre dans le dépôt : seulement des données fictives (lieu XTST) ou anonymisées par l'utilisateur.
- Ne supprimer aucune fonction opérationnelle. Ne pas modifier les projets originaux. Préserver les anciens repères et les anciennes adresses.
- Aucune donnée de démonstration dans une installation vierge. Aucune intelligence artificielle embarquée.
- N'inventer aucune caractéristique constructeur, aucun format industriel, aucune adresse pour un projet existant. Ne jamais déclarer un export compatible sans essai qui le prouve.
- Toute bibliothèque ajoutée a une licence compatible avec une vente commerciale (MIT, BSD, Apache, ISC).
