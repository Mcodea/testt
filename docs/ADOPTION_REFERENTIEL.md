# Adopter une révision du référentiel

Un ouvrage conserve son référentiel figé. Ouvrir un ancien projet ne lui applique
aucune nouvelle nomenclature. L'adoption reste une action volontaire sur la fiche
de l'ouvrage, après son enregistrement.

1. Cliquer sur **Examiner et appliquer…** dans le bandeau du référentiel.
2. Examiner chaque type et chaque équipement : ajouts, retraits, définitions et
   règles modifiées, noms physiques et fonctionnels avant/après. Les adresses
   affichées sont celles de l'ouvrage ; elles ne sont pas réaffectées.
3. Cocher les types souhaités, puis chaque ligne de renommage correspondante.
   Aucune case n'est cochée par défaut. Un type bloqué ne peut pas être choisi.
4. Confirmer **Adopter les types cochés**. Les équipements concernés repassent à
   valider. Le projet est enregistré ; une copie horodatée distincte est conservée
   avant toute application. Si l'ouvrage ou le référentiel a changé depuis
   l'aperçu, fermer et rouvrir la fenêtre avant de confirmer.

La fiche affiche ensuite **Télécharger la sauvegarde du projet** et
**Annuler l'adoption**, même si tous les écarts ont disparu. L'annulation demande
confirmation : elle revient à l'état précédant la dernière adoption, y compris
les modifications réalisées ensuite. Elle sauvegarde l'état courant dans un
autre fichier, puis restaure les octets d'origine par remplacement atomique.
L'état précédant l'annulation peut également être téléchargé.

Le retour arrière en un clic est disponible dans la session courante. Un nouvel
ouvrage, une ouverture de fichier ou un « Enregistrer sous » ne transporte pas
l'annulation vers un autre projet. Les copies sur disque restent disponibles.
Pour reprendre une copie après réouverture de l'application, conserver le fichier
courant puis ouvrir la sauvegarde téléchargée au format JSON comme un ouvrage.

## Limites volontaires

- Les signaux d'un **modèle figé** restent ceux de ce modèle : adopter le catalogue
  du type ne les remplace pas. Leur reprise est un acte séparé (moteur, 11/11/2026) :
  `Session.apercu_modele` / `adopter_modele`, routes `GET /api/referentiel/apercu-modele`
  et `POST /api/referentiel/adopter-modele`. Mêmes garanties : aperçu sans effet,
  blocage si une clé qui disparaît porte des données, correspondance du type →
  données reportées, renommages confirmés, sauvegarde, journal, « Annuler l'adoption ».
  L'ancienne action « actualiser le modèle » est refusée dès qu'elle renommerait ou
  ferait disparaître une donnée. L'écran web de cette reprise reste à faire (Codex) ;
  d'ici là, le parcours web continue de bloquer un changement de clé de modèle figé.
- La conversion d'un ancien équipement CT vers FT reste bloquée, en attente de la
  décision R1 sur la conservation de son repère.
- A1 (renommages V1 et 49 ajouts) et D5-b ne sont pas appliqués par ce parcours.
- L'adoption ne constitue pas une qualification des exports dans Control Expert,
  TOPKAPI ou S4W-Tools.

Preuves : `tests/test_adoption_controlee.py`, `tests/test_adoption_modele_fige.py`, `tests_web/test_adoption.py` ; captures
dans `validation/interface_v2/adoption/`.
