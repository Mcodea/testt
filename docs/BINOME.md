# Règle du binôme Claude / Codex

À lire au début de **chaque** session, avant tout commit. Valable jusqu'à la version 1.0.

## 1. Une seule branche

Dépôt de travail : **Mcodea/testt**, public. `testt` est le nom du dépôt.
L’ancien dépôt Mcodea/OGIAS reste privé ; ne jamais transférer son historique.
La CI complète fonctionne sur le dépôt public.

- Branche commune : **`claude/referentiel-v2`** (PR #1 vers `release/1.0`).
- Ne **jamais** pousser sur `release/1.0`, `main` ni une autre branche. Aucun agent ne fusionne la PR :
  l'utilisateur la relit et la fusionne.
- Avant de commencer : `git fetch origin && git checkout claude/referentiel-v2 && git pull --rebase`.
- Avant chaque push : `git pull --rebase`, suite complète verte en local, puis push. Ne jamais réécrire
  l'historique déjà poussé (`--force` interdit).

## 2. Domaines

| Domaine | Responsable principal | Fichiers |
| --- | --- | --- |
| Interface, ergonomie, tests navigateur, captures | **Codex** | `sorep_web/static/**`, `tests_web/**`, `validation/interface_v1/**` |
| Moteur, référentiel, données, exports, adoption, tests unitaires | **Claude** | `genvar/**`, `genvar/data/**`, `tests/**`, `outils/**` |
| Serveur web (routes) | les deux, petits commits | `sorep_web/serveur.py` |
| Suivi | les deux | `ETAT_TRAVAIL.md`, `docs/INSTRUCTIONS_EN_COURS.md` |

Un agent peut toucher le domaine de l'autre s'il le faut pour terminer son lot, en le signalant dans le
message de commit. Chacun **relit** les commits de l'autre depuis sa dernière session (`git log`) et corrige
ou signale ce qui contredit les décisions.

## 3. Tour de parole

- Ligne « Agent actif » en tête de `docs/INSTRUCTIONS_EN_COURS.md` : `Claude` ou `Codex`, avec l'heure.
  La mettre à jour dans le premier commit de la session.
- Si l'autre agent a poussé il y a moins d'une heure : rester dans son propre domaine.
- Avant de s'arrêter (limite proche ou plus rien d'utile) : tout est commité et poussé, CI verte ou échec
  expliqué, entrée « Passation » mise à jour (dernier commit, lot en cours, **étape exacte** de reprise,
  décisions à valider), « Agent actif » remis à `libre`.

## 4. Qualité

Chaque lot : comprendre, tests d'abord, code minimal, suite complète + ruff + mypy + `node --check` +
`python outils/ci.py data`, relecture critique du diff, push, vérification du run GitHub. Un lot qui casse
la CI est corrigé avant tout autre travail. Les règles du prompt
`docs/referentiel/PROMPT_CLAUDE_AUTONOME_OGIAS_V2.md` s'appliquent sans exception.

## 5. Décisions de l'utilisateur en attente

D5-b (règles auto classées suggestion), A1 (renommages V1 et 49 ajouts). Ne pas les appliquer ; travailler sur
le reste. R1 validé le 11/11 (CT contenu dans FT ; projets existants convertis par adoption, repère conservé).
