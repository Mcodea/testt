"""Génère REFERENTIEL.md : liste lisible des types, signaux et règles du référentiel livré.

    py outils/documenter_referentiel.py
"""
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
from genvar import chemins
from genvar.catalogue import Catalogue, DOMAINES


def main():
    cat = Catalogue.charger(chemins.fichier_catalogue_origine())
    l = [f"# Référentiel SOREP livré — {cat.version}", "",
         f"{len(cat.types)} types · {len(cat.signaux)} signaux · {len(cat.regles)} règles. "
         "Document généré par `outils/documenter_referentiel.py` : ne pas modifier à la main.", "",
         "Lecture : **ES** = E/S physique (ET/ST/EA/SA) ; un signal fonctionnel avec « ← ES_x » est acquis ou "
         "commandé par cette E/S. Présence **Règle** : proposé seulement par une règle. ⚙ = logique automate à "
         "programmer (générer la variable ne programme pas la fonction).", ""]
    l += ["## Sommaire", ""]
    for d in DOMAINES + ["Autres"]:
        types = [t for t in cat.types if (t.get("domaine") or "Autres") == d]
        if types:
            l.append(f"- **{d}** : " + ", ".join(f"{t['code']} {t['designation']}" for t in types))
    l.append("")
    for t in cat.types:
        sig = cat.signaux_du_type(t["code"])
        l += [f"## {t['code']} — {t['designation']}", "",
              f"*{t.get('domaine', '')}* · options : {', '.join(t.get('options', [])) or 'aucune'}", ""]
        if t.get("remarque"):
            l += [t["remarque"], ""]
        if sig:
            l += ["| Famille | Code | Information | Type | E/S | Présence | ⚙ |", "|---|---|---|---|---|---|---|"]
            calcules = {c for r in cat.regles if r.get("type") == t["code"] and r.get("mode") == "proposition"
                        for c in r.get("propose", [])}
            for s in sorted(sig, key=lambda s: 0 if s["famille"] == "ES" else 1):
                es = f"← {s['source']}" if s.get("source") else (s.get("es") if s.get("es") != "Interne" else "")
                pres = s["presence"] + (f" ({s['option']})" if s.get("option") else "")
                l.append(f"| {s['famille']} | {s['code']} | {s['information']} | {s.get('type_logique', '')} | {es} | "
                         f"{pres} | {'⚙' if s.get('logique') or (s['famille'] + '_' + s['code']) in calcules else ''} |")
            l.append("")
        regles = [r for r in cat.regles if r.get("type") == t["code"]]
        if regles:
            l += ["**Règles**", ""]
            for r in regles:
                l.append(f"- `{r['id']}` *{r['mode']}* — {r['libelle']} : si {' + '.join(r['si'])} → "
                         f"{', '.join(r['propose'])}" + (f". {r['logique']}" if r.get("logique") else ""))
            l.append("")
    generiques = [r for r in cat.regles if r.get("type") == "*"]
    if generiques:
        l += ["## Règles communes à tous les types", ""]
        l += [f"- `{r['id']}` *{r['mode']}* — {r['libelle']} : {r.get('logique', '')}" for r in generiques]
    (RACINE / "REFERENTIEL.md").write_text("\n".join(l) + "\n", encoding="utf-8")
    print("REFERENTIEL.md généré.")


if __name__ == "__main__":
    main()
