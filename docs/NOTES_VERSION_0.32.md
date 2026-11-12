# OGIAS 0.32 — version stable de travail (12/11/2026)

Version de stabilisation du travail en binôme Claude / Codex des 10 et 11 novembre 2026. **Ce n'est pas la
1.0** : les exports Control Expert, SOFREL S4W et TOPKAPI restent **non qualifiés** tant que les essais réels
ne sont pas faits (`ESSAIS_A_FAIRE.md`).

## Référentiel V2 (décisions D1 à D7, R1 à R9, P1 à P9)

- **Adoption contrôlée** d'une nouvelle révision, type par type : aperçu des ajouts, retraits et renommages,
  confirmation explicite, report des adresses, voies, commentaires et correspondances TOPKAPI, sauvegarde
  horodatée et retour arrière exact ; acceptation en un geste pour les ouvrages en conception (R6) ;
  conflits de surcharge locale signalés et « revenir au standard » (R4).
- **Noms physiques** : même suffixe pour la même information (`ET_MV01_OUV` / `TS_MV01_OUV`) ; `suffixe_es`
  limité aux collisions de clé ; organe « fin de course » en description.
- **CT consolidé dans FT** (débitmètre / compteur unique) ; correspondances CT → FT ; conversion des projets
  existants par adoption, repère conservé (R1).
- **Règles documentaires** : gouvernance (relation documentaire, suggestion, contrôle) ; aucun algorithme
  imposé ; textes d'origine archivés (`docs/referentiel/REGLES_AVANT.csv`).
- **Objets du référentiel** : 732 lignes de modèles alignées, lexique (354 entrées), dictionnaire des codes
  (81) avec ses contrôles et l'alerte « 3 lettres » pour les nouveaux codes, correspondances anciennes /
  nouvelles clés ; écrans d'édition dans le brouillon ; onglets Excel.
- **Gestion des profils** : version calculée par profil et état de synchronisation de chaque équipement
  (R2 / R3), rapport d'impact multi-ouvrages et journal des décisions (R5 / R7), duplication et archivage,
  suppression bloquée d'un élément utilisé.
- **Profil VANNE_MV** : sortie d'arrêt câblée, défauts d'ouverture et de fermeture détaillés, candidats
  internes BI ; variables internes déclarées BI, EI, MI, RI sur sélection (P1), sans adresse ni logique.
- **Contrôles** : homonymes entre ouvrages d'un même programme automate (P8 / R9).
- **Rapprochement** : seuil de confiance prouvé, mesures publiées, confirmation en lot annulable.
- **Fiabilité** : copies horodatées restaurables avant chaque opération lourde.

## Interface

Gestion du référentiel V2, écran d'adoption détaillé, lexique et dictionnaire, tableau de bord (répartition
des E/S, états vides, accès aux étapes), polices et icônes Lucide embarquées (aucun réseau), colonnes
Variables alignées.

## Qualité

CI GitHub : Windows et Linux, couverture du moteur ≥ 85 %, exports 100 %, ruff, mypy, audit des
dépendances, contrôle anti-données réelles, banc de performance, zip portable construit et essayé.

## Décisions encore ouvertes

D5-b (règles « auto » classées suggestion) ; A1 (renommages V1 et 49 ajouts de la bibliothèque des E/S).
