# Comparaison visuelle — ressources embarquées

Ouvrir [COMPARAISON.html](COMPARAISON.html) pour consulter chaque maquette et la
capture correspondante côte à côte, avec accès aux fichiers à leur taille réelle.
Les sources fournies ne sont pas modifiées. Les captures viennent de
`TestVariablesV031.test_captures_aux_dimensions_des_maquettes`, à 1920×1080,
avec un ouvrage fictif temporaire. Les nombres et états du scénario diffèrent
donc de ceux des maquettes ; aucune donnée de démonstration n'est injectée dans
les écrans pour les faire ressembler aux images.

## Comparaison effectuée

| Écran | Points observés | Écarts encore ouverts |
| --- | --- | --- |
| Tableau de bord | Lavande, navigation indigo de 80 px, quatre indicateurs et trois grandes cartes, typographie Inter, icônes Lucide locales. | Étapes désormais accessibles, E/S réparties depuis les points du moteur, état vide distinct de l’indisponibilité. Écarts : contenu à y=129 contre environ y=160 ; recette sans dénominateur donc taux non affiché ; activité récente absente. |
| Variables | Carte blanche, trois vues, recherche, propositions, colonnes à chasse fixe JetBrains Mono et commandes existantes. | Carte à y=129 contre environ y=160 sur la maquette ; densité, tailles de texte et marges à rapprocher ; état enregistré / historique insuffisants. |
| Variables avec détail | Panneau droit, nom, source, adresses, validation ; en-têtes et cellules maintenant alignés pour les neuf combinaisons testées. | Panneau de 350 px contre environ 440 px sur la maquette ; y=129 contre environ y=96 ; historique absent, actions et texte à rapprocher. |

`maquettes-mesures.json` contient les rectangles réellement relevés dans le DOM.
Ces mesures ne constituent pas un test d'identité pixel par pixel. La conformité
globale à §4 reste **partielle** ; les captures ne permettent pas de déclarer les
trois écrans terminés.

## Preuves automatiques du lot

- `TestRessourcesEmbarquees` : fichiers WOFF2 réellement chargés, chasse fixe,
  icônes SVG effectivement rendues, empreintes et licences accessibles, aucun
  accès extérieur accepté pendant les essais.
- `TestVariablesV031.test_detail_garde_les_entetes_alignes_aux_cellules` : Source
  reste visible ; Règle est masquée avec son en-tête ; Télétransmission reste
  visible au-delà de 1400 px, sauf dans la vue Table d'échange. Coordonnées des
  en-têtes et cellules comparées à 1366, 1920 et 2560 px, trois vues par taille.
- Les six scénarios Variables précédents restent inchangés.

Les anciennes sources physiques FDC visibles dans ce scénario proviennent de la
fixture et du moteur existants. Ce lot ne change ni catalogue, ni modèle, ni nom,
ni adresse ; les règles de nomenclature V2 priment sur les textes des maquettes.

Le lot Tableau de bord corrige la clé `point`, les étapes et les états vides.
Les quatre natures sont testées sur le contrat visuel ; la comparaison aux
points réels du moteur utilise une fixture ET. Les réponses synthétiques des
essais ne constituent aucune qualification matérielle ou industrielle.

Reprise UI recommandée : liens des points à traiter vers leur correction,
dimensions/densité et historique du panneau Variables ; activité récente
uniquement à partir d’événements enregistrés. Aucun taux ou événement fabriqué.

Le cahier §4 demande « aucun compteur à zéro » : un zéro connu est un état vide
explicite (Aucun équipement / Aucune E/S / Aucun point à traiter), sans nombre nul.
Une réponse manquante reste Non disponible. Les autres écrans restent à auditer.
