# Outils d'ingénierie de l'ouvrage (étape 1)

Décision du 18/11/2026 : plutôt que des « profils », chaque ouvrage déclare les outils réellement utilisés ;
OGIAS applique les règles propres à ces outils, et seulement à eux. Les conventions du maître d'ouvrage (charte de
nommage, plages %MW) sont l'étape suivante : elles ne dépendent d'aucun outil.

| Outil | Où il se choisit | Règle propre appliquée |
| --- | --- | --- |
| Automate / source d'acquisition | Fiche d'identification (inchangé) | M340, M580 : valeur 32 bits sur adresse %MW paire (R-VAR-07, R-EXI-03) |
| Communication | Fiche d'identification (inchangé) | — |
| Supervision | Bloc « Outils d'ingénierie » (nouveau) ; TOPKAPI par défaut | TOPKAPI : libellé de 40 caractères au plus (R-VAR-10) |
| IHM | Bloc « Outils d'ingénierie » (nouveau) ; aucune par défaut | — (format Vijeo non décrit) |

Avant, ces deux règles s'appliquaient à tous les ouvrages, quel que soit l'outil. Un outil non décrit dans OGIAS
n'entraîne aucune règle : rien n'est supposé. Les listes « Supervisions » et « IHM » s'enrichissent par « Gérer
les listes ». Les ouvrages enregistrés gardent TOPKAPI : leur comportement ne change pas.

Défaut corrigé au passage : depuis le 16/11, l'automate s'enregistre « Sch - M340 » ; deux contrôles des projets
existants comparaient encore le nom exact « M340 » et ne se déclenchaient donc plus (adresse paire en 32 bits).

## Étape 2 : conventions du maître d'ouvrage

- **Plan mémoire %MW par famille**, écran Adressage, bloc « Conventions de l'ouvrage » : premier et dernier mot de
  chaque famille, contrôlés avant écriture (entiers, 0 à 65535, aucun recouvrement ; rien n'est écrit en cas de refus).
  Alerte si la plage RTR est plus courte que la plage TR (miroir impossible). Les adresses validées ne bougent jamais ;
  les propositions suivent les nouvelles plages. Le code annonçait déjà ces plages « modifiables », sans écran.
- **Reprendre les réglages d'un autre ouvrage**, bloc « Outils d'ingénierie » : supervision, IHM, plan mémoire et
  décalage Modbus ; automate et communication seulement s'ils ne sont pas encore renseignés (un automate déjà choisi
  n'est pas remplacé : la configuration matérielle en dépend). Tout ou rien ; l'identification, les équipements et
  les adresses ne sont jamais copiés.
- Reste : la charte de nommage (lieu sur 4 caractères, code d'ouvrage sur 2 lettres, format du repère), dupliquée
  dans une dizaine d'endroits. À rendre réglable avec un exemple réel de charte d'un autre maître d'ouvrage, pour ne
  rien supposer.
