# Règles de cohérence d'OGIAS

Catalogue généré depuis `genvar/coherence.py` (orientation du 18/11/2026 : la cohérence d'abord). Chaque constat de la
recette porte l'une de ces règles ; l'API `/api/regles` donne le même catalogue. Les contrôles R-CHA et R-TEL-01 à 03
sont nouveaux : ils suivent la chaîne de l'information au travers des étapes.

Essai à vide : sur un ouvrage fictif réunissant les 50 types du catalogue avec toutes leurs options (312 variables,
15 paires TR / RTR), les contrôles transversaux ne signalent rien : pas de faux positif sur des données saines.

| Code | Règle | Gravité | Se corrige dans | Pourquoi | Corriger |
| --- | --- | --- | --- | --- | --- |
| R-OUV-01 | Identification de l'ouvrage incomplète | Erreur | Ouvrage | Sans lieu, code et libellé, les noms de variables et les fichiers livrés ne sont pas identifiables. | Compléter la fiche de l'ouvrage. |
| R-OUV-02 | Lieu mal formé | Erreur | Ouvrage | Le lieu entre dans chaque repère et chaque nom de variable : un format différent casse la charte. | Saisir 4 caractères (lettres majuscules ou chiffres) dans la fiche de l'ouvrage. |
| R-OUV-03 | Code d'ouvrage mal formé | Erreur | Ouvrage | Le code d'ouvrage entre dans les repères : un format différent casse la charte. | Saisir 2 lettres majuscules dans la fiche de l'ouvrage. |
| R-OUV-04 | Numéro d'ouvrage invalide | Erreur | Ouvrage | Le numéro distingue deux ouvrages du même lieu : invalide, il crée des repères ambigus. | Saisir un numéro de 01 à 99, ou le laisser vide pour un ouvrage historique. |
| R-OUV-05 | Sous-ensemble mal formé | Erreur | Ouvrage | Le code du sous-ensemble entre dans le repère des équipements. | Saisir 2 caractères (lettres majuscules ou chiffres). |
| R-OUV-06 | Sous-ensemble déclaré deux fois | Erreur | Ouvrage | Deux sous-ensembles de même code produisent des repères en double. | Supprimer ou renommer le doublon dans la fiche de l'ouvrage. |
| R-EQ-01 | Équipement non validé | Erreur | Équipements | Un paramétrage non validé peut encore changer : les E/S et variables qui en découlent ne sont pas sûres. | Ouvrir la fiche de l'équipement, vérifier puis valider. |
| R-EQ-02 | Inventaire vide | Alerte | Équipements | Un ouvrage sans équipement ne produit aucune E/S ni variable. | Ajouter les équipements dans l'inventaire. |
| R-EQ-03 | Modèle d'équipement incohérent | Erreur | Équipements | Le modèle utilisé contient des signaux contradictoires : les variables générées seraient fausses. | Corriger le modèle dans le référentiel métier, ou changer de modèle. |
| R-EQ-04 | Type absent du catalogue | Erreur | Équipements | Sans type connu, OGIAS ne sait pas quels signaux produire. | Choisir un type existant ou l'ajouter au référentiel métier. |
| R-EQ-05 | Sous-ensemble non déclaré | Erreur | Équipements | L'équipement référence un sous-ensemble absent de l'ouvrage : son repère est invalide. | Déclarer le sous-ensemble dans la fiche de l'ouvrage ou corriger l'équipement. |
| R-EQ-06 | Numéro d'équipement mal formé | Erreur | Équipements | Le numéro entre dans le repère : un format différent casse la charte. | Saisir 2 chiffres (01 à 99). |
| R-EQ-07 | Repère en double | Erreur | Équipements | Deux équipements de même repère produisent des noms de variables identiques. | Renuméroter l'un des deux équipements. |
| R-EQ-08 | Option inconnue | Alerte | Équipements | Une option inconnue du type n'a aucun effet : l'information attendue ne sera pas produite. | Retirer l'option ou compléter le type dans le référentiel métier. |
| R-EQ-09 | Signal obligatoire retiré | Alerte | Équipements | Une information obligatoire du type manquera en supervision. | Rétablir le signal, ou le remplacer par un signal propre équivalent. |
| R-EQ-10 | Information attendue non décidée | Erreur | Équipements | Une règle du référentiel propose une information : sans décision, la liste des variables n'est pas figée. | Dans la fiche de l'équipement, retenir l'information ou l'écarter avec un motif. |
| R-EQ-11 | Information écartée sans motif | Alerte | Équipements | Un écart non motivé ne se justifie pas à la recette. | Écrire le motif dans la fiche de l'équipement. |
| R-EQ-12 | Signal accepté dont la règle n'est plus satisfaite | Alerte | Équipements | Le signal n'est plus généré alors qu'il avait été accepté : une information disparaît sans décision. | Vérifier les E/S de l'équipement, puis confirmer ou retirer le signal. |
| R-EQ-13 | Adresse conservée pour un signal non retenu | Alerte | Équipements | Une adresse reste réservée sans variable : elle sera réutilisée si le signal revient. | Libérer l'adresse si le signal ne doit pas revenir. |
| R-EQ-14 | Signal propre incohérent | Erreur | Équipements | Le sens ou la nature du signal propre contredit sa famille : l'E/S ou la variable serait fausse. | Corriger le signal propre dans la fiche de l'équipement. |
| R-EQ-15 | Information calculée sans source | Alerte | Équipements | Une information calculée (position, marche…) n'a ni E/S de retour ni ordre pour la calculer. | Ajouter les E/S nécessaires ou retirer l'information. |
| R-EQ-16 | Informations transmises sans E/S physique | Alerte | Équipements | L'équipement transmet des informations sans aucune E/S câblée ni liaison déclarée. | Ajouter les E/S câblées ou confirmer une liaison par communication. |
| R-NOM-01 | Nom trop long | Erreur | Variables | Control Expert et TOPKAPI refusent ou tronquent les noms trop longs. | Raccourcir le code du signal ou du repère. |
| R-NOM-02 | Caractères non autorisés dans un nom | Erreur | Variables | Les logiciels cibles refusent ces caractères à l'import. | N'utiliser que lettres, chiffres et _ simple. |
| R-NOM-03 | Nom en double | Erreur | Variables | Deux variables de même nom : l'import automate ou supervision échoue ou en écrase une. | Renommer l'un des signaux ou renuméroter l'équipement. |
| R-NOM-04 | Ouvrages du même programme en collision de noms | Erreur | Variables | Deux ouvrages du même programme automate emploient les mêmes noms. | Mettre le lieu dans les noms ou renuméroter l'un des ouvrages (aucun renommage automatique). |
| R-ES-01 | E/S non validées | Alerte | Liste des E/S et matériel | Des E/S restent à valider : leur contenu peut encore changer avant le câblage. | Valider les E/S dans la Liste des E/S. |
| R-ES-02 | Adresse physique manquante | Alerte | Liste des E/S et matériel | Une E/S câblée sans adresse %I / %Q n'est reliée à aucune voie. | Implanter l'E/S sur une voie dans l'écran Matériel. |
| R-ES-03 | Adresse physique en double | Erreur | Liste des E/S et matériel | Deux E/S sur la même adresse : un signal de terrain en écrase un autre. | Déplacer l'une des E/S sur une voie libre. |
| R-ES-04 | Préfixe d'adresse incohérent | Alerte | Liste des E/S et matériel | Le préfixe ne correspond pas à la nature (ET %I, ST %Q, EA %IW, SA %QW). | Corriger l'adresse ou la nature de l'E/S. |
| R-ES-05 | Voie déjà affectée | Erreur | Liste des E/S et matériel | Deux E/S sur la même voie d'un module. | Déplacer l'une des E/S dans l'écran Matériel. |
| R-ES-06 | Module non déclaré | Erreur | Liste des E/S et matériel | L'E/S est placée sur un module absent de la configuration. | Déclarer le module ou déplacer l'E/S. |
| R-ES-07 | E/S sur un module de mauvaise nature | Erreur | Liste des E/S et matériel | Une entrée sur un module de sorties (ou l'inverse) ne fonctionnera pas. | Déplacer l'E/S sur un module de sa nature. |
| R-ES-08 | Voie hors du module | Erreur | Liste des E/S et matériel | Le numéro de voie dépasse la capacité du module. | Choisir une voie existante du module. |
| R-ES-09 | Réserve d'un module sous le seuil | Alerte | Liste des E/S et matériel | Trop peu de voies libres pour les évolutions futures. | Ajouter une carte ou répartir les E/S. |
| R-ES-10 | Voie d'E/S non renseignée | Erreur | Liste des E/S et matériel | Une E/S de l'inventaire validé n'a pas de voie : elle ne sera pas câblée. | Implanter l'E/S dans l'écran Matériel. |
| R-VAR-01 | Type logique inconnu | Erreur | Variables | Sans type connu, l'occupation mémoire ne peut pas être calculée. | Corriger le type dans le référentiel métier. |
| R-VAR-02 | Variable sans adresse | Erreur | Variables | La variable n'a pas d'adresse dans la table d'échange : elle n'arrive pas en supervision. | Calculer puis valider les adresses dans l'écran Variables. |
| R-VAR-03 | Adresse non reconnue | Erreur | Variables | L'adresse n'est pas au format %MW (bit de 0 à 15). | Corriger l'adresse dans l'écran Variables. |
| R-VAR-04 | Format d'adresse incohérent avec le type | Erreur | Variables | Un BOOL doit être un bit (%MWn.b), une valeur numérique un mot (%MWn). | Corriger l'adresse ou le type. |
| R-VAR-05 | Chevauchement d'adresses | Erreur | Variables | Deux variables partagent la même mémoire : l'une écrase l'autre dans l'automate. | Déplacer l'une des variables (recalcul de l'adressage). |
| R-VAR-06 | Adresse hors de la plage de la famille | Erreur | Variables | La variable sort de la plage réservée à sa famille : la supervision ne la lira pas où elle l'attend. | Recalculer l'adressage ou corriger la plage de l'ouvrage. |
| R-VAR-07 | Variable 32 bits sur adresse impaire | Erreur | Variables | M340 et M580 refusent une variable 32 bits sur une adresse impaire. | Placer la variable sur une adresse paire. |
| R-VAR-08 | RTR pas en miroir de son TR | Erreur | Variables | Le retour de téléréglage n'est pas à l'adresse attendue en face de sa consigne. | Recalculer l'adressage TR / RTR. |
| R-VAR-09 | Types TR / RTR différents | Erreur | Variables | La consigne et son retour n'ont pas le même type : la supervision comparera des valeurs incompatibles. | Aligner les types dans le référentiel ou déclarer la conversion. |
| R-VAR-10 | Libellé TOPKAPI trop long | Alerte | Variables | TOPKAPI tronque les libellés au-delà de 40 caractères. | Raccourcir le libellé. |
| R-VAR-11 | Adresses proposées non validées | Alerte | Variables | Des adresses sont proposées mais pas validées par l'automaticien : elles peuvent encore bouger. | Valider les adresses dans l'écran Variables. |
| R-CHA-01 | Variable liée à une E/S introuvable | Erreur | Variables | L'E/S indiquée comme source de la variable n'existe pas dans la liste des E/S : le fil est rompu, la variable ne reflète aucun signal de terrain. | Rétablir l'E/S dans la fiche de l'équipement ou corriger la source de la variable. |
| R-CHA-02 | E/S liée à une variable introuvable | Erreur | Liste des E/S et matériel | L'E/S désigne une variable d'échange qui n'existe pas : son information n'arrive pas en supervision. | Vérifier les signaux retenus de l'équipement, puis régénérer les variables. |
| R-TEL-01 | Téléréglage sans retour | Alerte | Télétransmission | Une consigne (TR) sans retour (RTR) : la supervision ne peut pas vérifier que la consigne est appliquée. | Ajouter le retour de téléréglage dans le référentiel ou justifier son absence. |
| R-TEL-02 | Adresse de télétransmission négative | Erreur | Télétransmission | Le décalage Modbus réglé fait passer des adresses sous zéro : elles sont impossibles à lire. | Corriger le décalage dans les paramètres d'adressage. |
| R-TEL-03 | Libellés TOPKAPI identiques sur un équipement | Alerte | Télétransmission | Deux informations du même équipement portent le même libellé : l'opérateur ne peut pas les distinguer. | Différencier les libellés dans la fiche de l'équipement ou le référentiel. |
| R-TEL-04 | Ligne de télétransmission incohérente | Erreur | Télétransmission | La ligne de la table de télétransmission existante contredit sa source. | Corriger la ligne dans la table de télétransmission. |
| R-TEL-05 | Informations sans source | Alerte | Télétransmission | Des informations de la table n'ont pas de variable source. | Associer une variable ou déclarer l'information non accessible. |
| R-TEL-06 | Lignes à compléter | Alerte | Télétransmission | Fonction ou accès TOPKAPI restent à valider. | Compléter les lignes dans la table de télétransmission. |
| R-EXI-01 | Doublon d'identification | Erreur | Variables | Deux variables existantes sont rattachées au même signal du même équipement. | Corriger l'identification de l'une des deux. |
| R-EXI-02 | BOOL sur un mot entier | Alerte | Variables | Un booléen placé sur un mot entier : un bit manque probablement dans l'adresse. | Vérifier l'adresse dans le programme existant. |
| R-EXI-03 | Variable 32 bits sur adresse impaire (existant) | Erreur | Variables | L'automate refuse une variable 32 bits sur une adresse impaire. | Vérifier le programme existant (aucune correction automatique). |
| R-EXI-04 | Chevauchement mémoire (existant) | Erreur | Variables | Deux variables existantes partagent la même mémoire. | Vérifier le programme existant (aucune correction automatique). |
| R-EXI-05 | Identification à confirmer | Alerte | Variables | Le rattachement de la variable existante est probable mais pas certain. | Confirmer ou corriger l'identification. |
| R-EXI-06 | Identification incohérente | Erreur | Variables | Le rattachement de la variable existante contredit ses caractéristiques. | Corriger l'identification. |
