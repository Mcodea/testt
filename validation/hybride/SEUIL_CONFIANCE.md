# Seuil de confiance du rapprochement hybride — mesures publiées

Fichier généré par `validation/hybride/evaluer.py` (`rapport_seuil`) et vérifié par
`tests/test_seuil_confiance_rapprochement.py` : il ne peut pas diverger du code.

**Seuil de confiance : 80/100** (`genvar.rapprochement.SEUIL_CONFIANCE`). Au-dessus, et si le premier
candidat n'est pas ambigu (écart d'au moins 8 points avec le suivant), la proposition est de confiance
« élevée » et peut être confirmée **en lot** par l'automaticien ; sinon la ligne est « à rapprocher
manuellement ». Aucune correspondance n'est appliquée sans confirmation humaine ; un lot est tracé et
annulable. Le score est un classement, pas une probabilité.

Décision du 11/11/2026 : seuil strict conservé pour la 1.0 (l'utilisateur s'en remet à la recommandation).

Règle de réglage : aucune proposition fausse connue (tous les candidats, y compris sur les signaux
volontairement absents) n'atteint le seuil, sur tous les jeux de validation et pour toutes les méthodes.

| Jeu | Méthode | Liens | Élevées correctes | Élevées fausses | Précision | Rappel | Faux connus | Score max. d'un faux |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Jeu initial | programme | 18 | 5 | 0 | 100.0 % | 27.8 % | 0 | 0 |
| Jeu initial | catalogue | 18 | 0 | 0 | n.d. | 0.0 % | 1 | 74 |
| Jeu initial | hybride | 18 | 5 | 0 | 100.0 % | 27.8 % | 1 | 79 |
| Jeu difficile | programme | 18 | 0 | 0 | n.d. | 0.0 % | 0 | 0 |
| Jeu difficile | catalogue | 18 | 0 | 0 | n.d. | 0.0 % | 11 | 64 |
| Jeu difficile | hybride | 18 | 0 | 0 | n.d. | 0.0 % | 11 | 69 |

| Méthode (deux jeux) | Élevées correctes / liens | Précision | Rappel |
|---|---:|---:|---:|
| programme | 5/36 | 100.0 % | 13.9 % |
| catalogue | 0/36 | n.d. | 0.0 % |
| hybride | 5/36 | 100.0 % | 13.9 % |

Limites : deux jeux fictifs construits pour le développement, non représentatifs d'ouvrages réels ;
le rappel au seuil est volontairement bas (la précision passe avant le rappel). Les autres
correspondances restent proposées sous le seuil, à confirmer une par une. À remesurer sur des exports
industriels anonymisés dont la vérité est établie avant l'exécution.
