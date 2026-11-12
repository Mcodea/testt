"""Comparer les stratégies sur les deux jeux fictifs fournis.

Exécution depuis le dossier de l'application : py comparer_les_methodes.py
Rapport détaillé enregistré dans validation/hybride/rapport_comparaison.md.
"""
from __future__ import annotations
import json
from validation.hybride.evaluer import evaluer, BASE

RESULTATS = [("Jeu initial", BASE), ("Jeu difficile", BASE / "jeu_difficile")]
LIBELLES = {"programme": "Programme seul", "catalogue": "Catalogue → programme", "hybride": "Méthode hybride"}


def generer():
    resultats = [(nom, evaluer(rep)) for nom, rep in RESULTATS]
    tab = ["# Comparaison de trois stratégies de rapprochement — ouvrage fictif",
           "", "**Méthode d'évaluation :** vérité de référence enregistrée dans les fichiers `verite_reference.json` ; "
           "pour chaque signal présent, seule la première proposition est comparée au nom source attendu.",
           "", "- **Précision** : bonnes propositions / toutes les premières propositions émises sur des signaux réellement présents.",
           "- **Rappel / taux de réussite** : bonnes propositions / total des correspondances réelles attendues.",
           "- **Couverture** : signaux présents pour lesquels au moins un candidat a été proposé.",
           "- **F1** : moyenne harmonique de la précision et du rappel.",
           "- **Faux positifs sur absents** : suggestions faites pour des signaux volontairement absents de la vérité de référence.",
           "- **Ambiguïté** : premier candidat très proche d'un deuxième (différence de score < 8 points).",
           "", "Le score de classement des candidats **n'est pas une probabilité** de réussite ; chaque correspondance reste à confirmer par un automaticien.",
           "", "## Résultats par jeu", ""]
    agg = {m: {"bons":0,"faux":0,"manques":0,"amb":0,"abs_fp":0,"present":0,"absents":0} for m in LIBELLES}
    for jeu, resultat in resultats:
        d = resultat['jeu']
        tab.extend([f"### {jeu}",
            f"{d['equipements']} équipements, {d['variables_source']} déclarations source, "
            f"{d['es_documentaires']} E/S documentaires, "
            f"{d['liens_attendus']} liens réels et {d['signaux_absents']} signaux absents.", "",
            "| Méthode | Bonnes | Fausses | Non retrouvées | Réussite / rappel | Précision | F1 | Faux sur absents |",
            "|---|---:|---:|---:|---:|---:|---:|---:|"])
        for meth in LIBELLES:
            r = resultat['methodes'][meth]
            precision_texte = f"{r['precision_pct']:.1f}%" if r['precision_pct'] is not None else "n.d."
            tab.append(f"| {LIBELLES[meth]} | {r['corrects']} | {r['faux']} | {r['non_proposes']} | "
                       f"{r['rappel_pct']:.1f}% | {precision_texte} | {r['f1_pct']:.1f}% | "
                       f"{r['faux_positifs_sur_absents']} |")
            a = agg[meth]
            for key, rkey in [('bons','corrects'),('faux','faux'),('manques','non_proposes'),
                              ('amb','premiers_candidats_ambigus'),('abs_fp','faux_positifs_sur_absents')]:
                a[key] += r[rkey]
            a['present']+=d['liens_attendus'];a['absents']+=d['signaux_absents']
        tab.append("")
    tab.extend(["## Bilan agrégé (sur les deux jeux fictifs)", "",
                "| Méthode | Bonnes / liens réels | Taux de réussite | Précision | F1 | Faux sur signaux absents |",
                "|---|---:|---:|---:|---:|---:|"])
    for m,a in agg.items():
        p = 100*a['bons']/max(1,a['bons']+a['faux'])
        r = 100*a['bons']/max(1,a['present'])
        f = 2*p*r/max(p+r,1e-9)
        tab.append(f"| {LIBELLES[m]} | {a['bons']}/{a['present']} | {r:.1f}% | {p:.1f}% | {f:.1f}% | {a['abs_fp']}/{a['absents']} |")
    tab.extend(["", "## Interprétation et limites", "",
        "- Les méthodes sont comparées sur **les mêmes variables sources, le même catalogue et les mêmes signaux attendus**. Seule la méthode hybride utilise en plus la liste documentaire d'E/S.",
        "- Les deux jeux ont été **construits pour le développement** : ce ne sont pas des échantillons aléatoires représentatifs d'ouvrages réels ; une note de performance industrielle ne peut pas en être déduite.",
        "- Les nombreux signaux optionnels du catalogue non présents dans la vérité de référence ne sont pas comptés comme des omissions ; seules les 18 correspondances attendues par jeu sont évaluées.",
        "- L'approche hybride détecte davantage de correspondances, mais les **faux positifs et les absences persistent** sur le jeu difficile ; les commandes et réglages exigent une validation renforcée.",
        "- Le score n'est pas une probabilité calibrée ; 100/100 ne signifie pas validation à 100 %.",
        "- Un export de variables n'établit pas à lui seul la chaîne logique entre une E/S et une variable mémoire, ni l'accessibilité TOPKAPI.",
        "- Une validation indépendante devra utiliser plusieurs véritables exports industriels anonymisés, avec une vérité de référence établie manuellement **avant** l'exécution de la comparaison.", "",
        "## Reproduction", "",
        "Depuis la racine du projet : `py comparer_les_methodes.py`, puis `py -m unittest discover -s tests -v`.", ""])
    output = BASE/'rapport_comparaison.md'
    output.write_text('\n'.join(tab),encoding='utf8')
    for name, r in resultats:
        label='jeu_initial' if name=='Jeu initial' else 'jeu_difficile'
        (BASE/f'resultats_{label}.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
    print('\n'.join(tab[0:4]));print('\n'.join(tab[-23:-11]));print(f'Rapport : {output}')
    return output

if __name__=='__main__':generer()
