# OGIAS — Refonte de l’étape 2 « Liste des E/S »

**Base unique :** archive utilisateur `OGIAS_V028.zip`. Cette livraison est une **étape de la future V0.29**, pas une annonce de finition de tous les écrans V0.29. Aucun projet d'exploitation ni fichier utilisateur n'a été modifié dans le code ou les tests.

## 1. Décisions métier conservées

- Identification principale : **repère équipement à 12 caractères** et **nom réel automate** (`p.pcf`, `p.nom`), sans modifier leurs règles de construction.
- La clé de signal existante (`p.cle`, par exemple `ES_DEB` ou `ES_FDC_FER`) reste une information secondaire ; elle n'est pas recréée dans le JavaScript.
- Étape 2 = **validation du contenu** : désignation, sens du contact, raccordement, échelle analogique, commentaire. Étape 3 = **configuration du matériel, modules, voies et adresses**.
- Aucun bouton d'affectation de voie ni adresse saisissable dans l'étape 2. Les voies existantes apparaissent uniquement en lecture seule.
- Calcul du matériel impossible avec des E/S au contenu non validé (mécanisme métier `Session.proposer_materiel` conservé). Le bouton de navigation « Matériel » est également désactivé sur l'étape 2 tant que le contenu reste à valider.
- La validation par ligne, par sélection et par lignes actuellement affichées reste disponible. La validation affichée respecte les filtres en cours.
- La barre globale à cinq étapes, le pied précédent/suivant et les API `/api/es`, `/api/es/definir`, `/api/es/valider` restent présents.

## 2. Écran développé

- Ruban contextuel de la liste, dans les couleurs OGIAS validées ; boutons de validation, export de liste et accès au matériel selon le statut.
- Compteurs-filtre ET / ST / EA / SA / « à valider » / « validées » ; filtre supplémentaire « erreurs » si une configuration paraît incohérente.
- Recherche par repère, nom automate, clé, désignation, UF ; filtres combinables UF et équipement.
- Tableau : équipement + nom automate + clé de signal, point, désignation, sens ou échelle, raccordement, voie (lecture seule), état.
- Ligne entière cliquable et activable par **Entrée / Espace** ; cases à cocher pour la validation par sélection.
- Panneau contextuel escamotable : désignation, sens des TOR, échelle mA/physique des EA/SA, raccordement, note libre, voie existante en lecture seule, enregistrement ou « Valider le contenu ».
- À 1280 et 1440 px, le panneau s'affiche à droite en superposition pour préserver la largeur du tableau. À largeur supérieure, il peut occuper une colonne séparée.
- Avertissement avant d'abandonner une édition en cours ; confirmation explicite lorsque le changement de raccordement affecterait une adresse déjà placée.

## 3. Backend — extension compatible

- `genvar/modele.py` : champ facultatif `PointES.note`, lu dans `eq.es_meta`, sans supprimer la désignation/commentaire existants.
- `genvar/session.py` : `Session.definir_es(..., note=...)` ; modification de la note dévalide le contenu. L'échelle analogique modifiée depuis l'étape 2 dévalide **le contenu de cette E/S et sa voie**, sans dévalider inutilement l'identification ou le modèle d'équipement déjà validés. La modification de l'échelle depuis la fiche équipement conserve son comportement historique.
- `sorep_web/serveur.py` : `/api/es` retourne également `note`. `/api/es/definir` accepte facultativement `analogique` et `valider_contenu` lors d'une même demande ; pour ces demandes composites, restauration de l'ouvrage en mémoire en cas de rejet des règles métier.
- `genvar/export_liste_es.py` : colonne « Commentaire » ajoutée à la fin de l'Excel, et commentaire disponible dans l'HTML imprimable. L'intitulé historique « Configuration analogique / impulsions » demeure dans l'HTML pour conserver les compatibilités.

## 4. Tests

Commande exécutée : `python -m pytest -q`

**Résultat : 363 tests réussis, 25 ignorés.** Neuf tests spécifiques `tests/test_vue_es_v029.py` couvrent les repères existants, les notes, l'échelle analogique, le refus d'échelle invalide et l'absence de modification partielle, la validation groupée, les routes HTTP conservées, l'export et un jeu synthétique de plus de 50 équipements.

`node --check sorep_web/static/app.js` : conforme.

**Vérification visuelle :** Chromium en 1280 × 900 et 1440 × 900, sans débordement horizontal de page ni exception JavaScript constatés ; navigation au clavier, filtre texte, ouverture du panneau et constitution de la requête d'échelle analogique vérifiées. Le navigateur de test interdisait la navigation directe vers `127.0.0.1` ; le rendu a donc été testé avec les véritables fichiers HTML/CSS/JS et un jeu de réponses API fictives, tandis que les réponses HTTP du serveur ont été testées séparément par pytest. Les captures sous `validation/captures_liste_es/` illustrent **ce contrôle simulé**, non une qualification Windows.

## 5. Limites restantes

- La nouvelle présentation a été testée dans Chromium sous Linux, pas encore sur ton poste Windows avec la fenêtre OGIAS réelle.
- Les champs de l'échelle actuellement pris en charge par le moteur sont exprimés en **mA** ; une extension à d'autres types électriques devra être validée au niveau du référentiel et du moteur, pas inventée côté interface.
- Les protections de cohérence du moteur existant sont conservées. Les tests logiciels ne qualifient ni les exports Control Expert, ni S4W-Tools, ni TOPKAPI 6.3.
- Les autres écrans de la refonte globale restent dans la V0.28 d'origine. Leur modification attend la validation de leurs maquettes.

## 6. Recette manuelle conseillée sous Windows

1. Décompresser l'archive dans un dossier **nouveau** ; conserver l'installation précédente et ses données en sauvegarde.
2. Lancer `OGIAS.bat` et ouvrir un **ouvrage fictif** comportant des équipements complètement paramétrés et validés.
3. Aller à l'étape « Liste des E/S » ; vérifier le repère 12 caractères, le nom automate et la clé réelle d'un signal.
4. Tester le filtre ET puis le filtre « à valider », la recherche, la sélection par UF et par équipement.
5. Ouvrir un signal TOR au clavier et corriger le sens ; enregistrer puis valider le contenu.
6. Pour un signal analogique fictif, modifier l'échelle et vérifier le maintien de l'adresse en lecture seule ; aucun module ne doit être créé automatiquement.
7. Tant qu'une E/S reste à valider, le bouton « Matériel » est inactif. Après validation de tout le contenu, tester le passage à l'étape 3.
