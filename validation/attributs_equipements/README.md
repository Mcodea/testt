# Attributs d'équipement définis par l'atelier (lot 4)

C'est l'idée des attributs typés de Typical Manager, à la mesure d'OGIAS : des champs propres à votre façon de
travailler (marque, diamètre, alimentation secourue, repère sur le plan…), déclarés une fois pour l'atelier.

- **Déclaration** : Standards d'ingénierie › Attributs d'équipement › « Nouvel attribut… ».
  - On donne un code, un nom et un type : texte, nombre (avec unité), liste de valeurs, ou oui / non.
  - On choisit les types d'équipement concernés (vide = tous). On peut le rendre obligatoire et lui donner une
    valeur proposée.
- **Saisie** : sur la fiche de l'équipement (bloc « Attributs »), contrôlée selon le type ; ou en masse par
  l'aller-retour Excel, où chaque attribut a sa colonne « Nom [CODE] » (« — » = sans objet pour ce type).
- **Modèles de livrables** : variable `<#ATTR_CODE#>` dans un bloc. Les attributs figurent dans « Variables
  disponibles ».
- **Contrôles** :

| Règle | Niveau | Signification |
| --- | --- | --- |
| R-ATT-01 | Alerte | Attribut obligatoire sans valeur |
| R-ATT-02 | Alerte | Valeur retirée de la liste de l'attribut après sa saisie (conservée, signalée) |

Règles de sécurité :

- **Code et type** : figés après la création, car les modèles et les fichiers les emploient. On ne supprime pas
  un attribut : on l'archive, et les valeurs restent sur les équipements.
- **Valeur proposée** : elle est montrée en exemple, jamais écrite d'office.
- **Équipement** : saisir un attribut ne change ni ses adresses ni sa validation. Un attribut modifié par
  aller-retour ne le fait pas non plus repasser « à valider ».
- **Valeurs vides** : une valeur vidée sur la fiche est retirée ; une cellule vide dans Excel ne change rien.

Les attributs sont ceux de l'atelier (dossier de données, `attributs_equipements.json`) : ils valent pour tous les
clients. S'ils devaient varier d'un client à l'autre, ils pourront devenir une brique des standards.

Vérifications :

- 804 essais du moteur, dont `tests/test_attributs.py` (5 essais) ;
- 113 essais navigateur, dont `test_attributs_d_equipement` ;
- ruff, mypy ;
- banc de performance sans écart ;
- audit des données : 0 détection ;
- accessibilité : 0 écart.

Captures (ouvrage et attributs fictifs) : `bibliotheque_clair.png`, `bibliotheque_sombre.png`, `definition.png`,
`fiche_equipement.png`.
