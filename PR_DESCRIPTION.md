# OGIAS 0.32 — refonte visuelle industrielle et corrections U9

Le parcours ouvre le bon équipement et la bonne vue E/S. Variables retrouve
des lignes de 44 px, des cases de 24 px utilisables au clavier, des états vides
alignés et une fermeture Échap qui respecte les fenêtres au premier plan.

La nouvelle consigne du 12/11 remplace la palette lavande par une présentation
industrielle : sombre #0B0F19 / #0F1623 / #111827, bordures nettes, navigation
libellée, tableaux fixes et commandes compactes. La préférence de thème reste
conservée. La refonte ne modifie aucune fonction, état, API, donnée ou export.
Les champs matériels, racks complets et nomenclature ajoutés par Claude sont
préservés et leur présentation est adaptée sans toucher leurs événements.

Report sur **Mcodea/testt**, branche **claude/referentiel-v2**, depuis la base
publique de Claude 085b1c7. Aucun historique de l’ancien dépôt privé importé ;
la racine publique 4d084b4 est conservée. Aucun changement moteur, serveur,
données, dépendances, tests unitaires ou workflow dans ce lot.

Validation locale :

- 730 tests Python et 18 sous-cas, 0 ignoré ; couverture 89,283831 %, exports 100 %.
- 60 tests navigateur et 52 sous-cas, 0 ignoré ; sept nouveaux cas de présentation.
- Ruff, mypy (49 fichiers), JS et audit strict des dépendances conformes.
- Performance et audit données consignés dans verification.json/performance.json.
- 28 captures de l’application, sans retouche ni contenu injecté ; sept écrans
  en trois tailles, détail, voies, composition et rack. Comparaison et décisions :
  validation/interface_v1/industriel_12_11/.

CI publique complète déclenchée au push ; statut du commit dans
https://github.com/Mcodea/testt/actions?query=branch%3Aclaude%2Freferentiel-v2.
La base a passé le run 43276436661 (Windows, Linux, navigateur, qualité, portable).
A1 et D5-b restent en attente ; aucun renommage V1 ni intégration des 193 E/S.
Aucun import Control Expert 14.1, TOPKAPI ou S4W-Tools déclaré qualifié sans
preuve réelle. Aucune fusion ni release par les agents.
