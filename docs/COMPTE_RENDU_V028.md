# OGIAS V0.28 — Compte rendu (9 novembre 2026)

## 1. Fusion des deux branches

Une seule base réunit désormais :
- ma V0.27 : moteur d'adressage, TOPKAPI `.$$t`, référentiel Excel ;
- votre Module 1 : import contrôlé `genvar/inbound`, repris tel quel ;
- votre Module 2 : son cycle brouillon → validation → publication et ses garde-fous, intégrés au dépôt unifié.

La seule collision, sur la table des routes du serveur, a été résolue en gardant les deux côtés. Les anciennes routes
d'import d'inventaire restent désactivées, comme dans votre version.

## 2. Un seul référentiel versionné (`genvar/referentiel_depot.py`)

- **Révision publiée** : ce sont les fichiers en service. L'écran est en lecture seule.
- **Brouillon** : il est unique et enregistré sur disque. On le modifie à l'écran (signaux, règles, types, modèles,
  lignes) ou par un classeur Excel, après aperçu et contrôle.
- **Validation** : elle fige l'empreinte du brouillon ; toute modification l'annule.
- **Publication** : le motif est obligatoire. L'écriture se fait sous verrou, avec retour arrière en cas d'échec.
  Chaque révision `Rnnnn` est archivée et ne change plus.
- **Restauration** : elle crée un nouveau brouillon ; l'historique n'est jamais réécrit.
- **Protection** : un fichier en service modifié hors du cycle est détecté et bloque toute publication.
- **Ouvrages** : ils ne sont jamais modifiés et gardent leur référentiel figé. Leur fiche signale une révision plus
  récente (V0.26).
- **Code retiré** : `referentiel_v2` et l'ancienne application directe d'un classeur. Il n'y a plus deux mécanismes
  concurrents.

## 3. Écran Référentiel (maquette validée)

1. **Consultation** de la révision publiée, avec six vues par type : E/S physiques, informations fonctionnelles,
   règles, modèles et lignes, utilisation dans les ouvrages, contrôle de conception.
2. **Brouillon** : bandeau orange, éléments modifiés surlignés, modification et ajout de signaux, de règles et de
   lignes, export et import Excel.
3. **Import d'un classeur** : erreurs bloquantes localisées, différences ; rien n'est intégré avant confirmation.
4. **Contrôle et publication** : contrôles, différences, conséquences, validation, motif et historique.

## 4. Tests

- 349 tests réussis ; 30 ignorés, faute de PyMuPDF ou de PySide6 dans cet environnement.
- Les 33 tests du module 2 visaient l'ancien module : ses garde-fous sont repris dans 3 tests du cycle unifié.
- Parcours navigateur sans erreur JavaScript :
  - consultation ;
  - création d'un brouillon ;
  - modification d'un signal ;
  - contrôle et publication ;
  - équipements ;
  - adressage.

## 5. Limites

1. Un brouillon n'est pas partagé entre plusieurs postes : le verrou est local.
2. L'option d'un signal se choisit parmi les options du type ; une option nouvelle s'ajoute d'abord au type.
3. Les modèles créés « depuis le catalogue » reçoivent une copie des signaux du type : c'est l'existant, conservé.
4. Qualifications industrielles : inchangées. Voir `COMPTE_RENDU_V027.md` §4 et le rapport LINA du 9 novembre (§20).
