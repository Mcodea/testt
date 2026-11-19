# Aller-retour Excel de la liste des équipements (lot 2)

Idée reprise de Typical Manager (import comparé « par repère »), adaptée aux règles d'OGIAS. Feuille de route :
document « OGIAS et Typical Manager : analyse et feuille de route » du 19/11/2026.

1. **Exporter.** Équipements > « Exporter la liste ». Le classeur a deux feuilles :
   - « Équipements » : repère, désignation, type, modèle, UF, local, identifiant OGIAS ;
   - « Lisez-moi » : les règles ci-dessous.
2. **Compléter dans Excel**, ou faire compléter par le client.
3. **Réimporter.** Équipements > « Importer une liste », nature « Liste des équipements (aller-retour) », proposée
   par défaut dès que l'ouvrage a des équipements. OGIAS compare chaque ligne à l'ouvrage et affiche d'abord ce qui
   demande l'attention :

| État | Signification |
| --- | --- |
| Refusé | Ligne en erreur, avec son motif : l'import est bloqué jusqu'à correction du fichier |
| À modifier | Désignation, modèle, UF ou local changés ; chaque changement est affiché « avant → après » |
| À créer | Nouveau repère, lu selon la charte de l'ouvrage |
| Inchangé | Rien à faire |
| Absent du fichier | Équipement de l'ouvrage retiré du fichier : **gardé par défaut**, supprimé seulement sur choix explicite |

Règles de sécurité :

- **Écriture.** Rien n'est écrit avant « Confirmer ». Le bouton dit exactement ce qui sera fait (ajouts,
  modifications, suppressions). Une copie de sécurité de l'ouvrage est faite avant l'application.
- **Adresses validées.** Un équipement qui en a n'est jamais supprimé ni changé de modèle par import.
- **Repère.** Il ne se modifie pas par fichier : l'identifiant OGIAS détecte un repère changé et refuse la ligne,
  car les noms et adresses en dépendent.
- **Cellule vidée.** La valeur d'OGIAS est conservée : aucun effacement implicite.
- **Champs contrôlés.**
  - Le modèle doit appartenir au type dans le référentiel.
  - L'UF doit exister dans l'ouvrage.
  - La désignation fait 32 caractères au plus.
- **Équipement modifié.** Il repasse « à valider », comme pour une modification dans OGIAS.

Non repris de Typical Manager (à décider si besoin) : « Remplacer par » pour un équipement absent du fichier, et
l'import des signaux ou des attributs. Ces derniers viendront avec la grille d'ingénierie (lot 5).

Vérifications :

- 785 essais du moteur, dont `tests/inbound/test_aller_retour.py` (6 essais) ;
- 110 essais navigateur, dont `test_aller_retour_excel_des_equipements` ;
- ruff, mypy ;
- audit des données : 0 détection ;
- accessibilité : 0 écart.

Captures (ouvrage fictif XTST) : `ruban_exporter.png`, `apercu_comparaison_clair.png`, `apercu_comparaison_sombre.png`.
