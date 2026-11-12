# Référentiel V2 et interface : gestion et adoption contrôlée

Cette branche applique les décisions V2 validées : nomenclature physique limitée,
consolidation CT dans FT pour les nouveaux projets, gouvernance documentaire et
cycle unique de gestion du référentiel. Elle conserve les référentiels figés des
ouvrages existants. **PR #1 à conserver ouverte, sans fusion automatique.**

Le lot UI ajoute les vues Lexique, Dictionnaire et Correspondances, l'archivage
réversible d'un type et sa conservation dans Excel, y compris lorsqu'un ancien
classeur n'a pas cette colonne. Un modèle explicitement sans E/S conserve cette
propriété au réimport. Les commandes métier existantes restent accessibles.

L'adoption montre les noms par équipement et exige chaque confirmation, décochée
par défaut. L'aperçu périmé est refusé. La fiche donne accès à la sauvegarde et à
l'annulation exacte du fichier, avec une autre copie avant annulation. Le retour
arrière est limité au fichier et à la session courants. Les modèles figés restent
conservés ; une migration de leur clé est bloquée dans le parcours web tant qu'un
traitement dédié n'existe pas. Voir docs/ADOPTION_REFERENTIEL.md.

Inter, JetBrains Mono et les géométries Lucide sont embarquées, avec leurs licences
accessibles depuis À propos et leurs sources/empreintes consignées. Les en-têtes
Variables restent alignés avec les cellules lorsque le détail est ouvert. Les
trois captures à 1920×1080 sont comparées aux maquettes dans
validation/interface_v2/maquettes/COMPARAISON.html ; les écarts restants sont listés
dans son README, sans déclarer la conformité globale terminée.

Validation locale : 557 tests Python, 0 ignoré ; couverture moteur 88,58 %, exports
industriels 100 % ; Ruff, mypy et syntaxe JavaScript conformes ; audit données 0.
Navigateur : 35 tests et 34 sous-cas réussis ; captures dans validation/interface_v2/.

Le tableau de bord répartit les E/S depuis les points du moteur et donne accès aux
cinq étapes sans modifier le projet. Les zéros connus sont des états vides, les
sources indisponibles sont signalées et aucun taux de recette n'est fabriqué.

A1 (49 ajouts / renommages V1), R1 (conversion des projets CT avec repère préservé)
et D5-b restent en décision. Aucune donnée du catalogue n'est modifiée par le lot UI.
Les preuves dans Control Expert 14.1, TOPKAPI et S4W-Tools sont encore attendues.
L'API GitHub répond Forbidden dans cet environnement ; la CI distante doit être
vérifiée pour le commit poussé avant toute fusion ou livraison.

Session Claude du 11/11/2026 (moteur) : course de navigation du tableau de bord
corrigée (CI Windows intermittente) ; profil VANNE_MV (options arrêt câblé
`ST_<repère>_AR` et défauts de manœuvre détaillés, à valider) ; homonymes entre
ouvrages d'un même projet Control Expert ; version calculée par profil et état de
synchronisation ; conflits de surcharge locale et retour au standard ; rapport
d'impact multi-ouvrages ; journal des décisions ; acceptation en un geste limitée
aux ouvrages neufs jamais validés ni exportés ; reprise contrôlée d'un modèle figé ;
alerte P3. 590 tests Python et 36 tests navigateur verts en local ; écrans
correspondants à faire. A1, R1 et D5-b toujours non appliqués.
