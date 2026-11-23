"""Génère REGLES_DE_NOMMAGE.md depuis le code et le référentiel livrés (cahier V1-9-09).

    py outils/documenter_regles_nommage.py            # écrit le fichier
    py outils/documenter_regles_nommage.py --verifier # échoue si le fichier n'est pas à jour
"""
import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
from genvar import charte, chemins, coherence                       # noqa: E402
from genvar.catalogue import DOMAINES, SIGNIFICATION_FAMILLES, Catalogue   # noqa: E402
from genvar.modele import LONGUEUR_MAX_LIBELLE, LONGUEUR_MAX_NOM          # noqa: E402

FICHIER = RACINE / "REGLES_DE_NOMMAGE.md"


def _exemple_variables(catalogue):
    """Noms réels produits par le moteur pour une pompe PM01 d'un ouvrage fictif (aucune donnée réelle)."""
    from sorep_web.serveur import Application
    ancien = os.environ.get("SOREP_DATA_DIR")
    with tempfile.TemporaryDirectory(prefix="ogias-nommage-") as tmp:
        os.environ["SOREP_DATA_DIR"] = tmp
        try:
            app = Application()
            app.appeler("nouveau", {"mode": "Neuf"})
            app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif"})
            app.appeler("fiche_ouvrage", {"action": "creer", "identification": {
                "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "01", "libelle": "Exemple",
                "automate": "Sch - M580", "revision": "A"}})
            ident = app.appeler("ajouter_equipement", {"type": "PM", "numero": "01", "se": "00"})["ident"]
            app.appeler("decider_proposition", {"ident_eq": ident, "decision": "retenir"})
            return [(v.famille, v.nom) for v in app.s.variables()], app.s.ouvrage.repere(app.s.ouvrage.equipement(ident))
        finally:
            if ancien is None:
                os.environ.pop("SOREP_DATA_DIR", None)
            else:
                os.environ["SOREP_DATA_DIR"] = ancien


def generer() -> str:
    cat = Catalogue.charger(chemins.fichier_catalogue_origine())
    c = charte.CHARTE_OGIAS
    ex = charte.exemple(c)
    variables, repere = _exemple_variables(cat)
    exemples = {}
    for famille, nom in variables:
        exemples.setdefault(famille, nom)
    familles = sorted({s["famille"] for s in cat.signaux})
    l = ["# Règles de nommage OGIAS", "",
         f"Document généré par `outils/documenter_regles_nommage.py` depuis le code et le référentiel livrés "
         f"(« {cat.version} ») : ne pas modifier à la main. Les exemples sont fictifs (lieu XTST).", "",
         "## 1. Repères", "",
         "La charte de nommage est un réglage du client (Outils › Standards d'ingénierie). Charte OGIAS par défaut :", ""]
    l += [f"- {x}" for x in charte.decrire(c)]
    l += ["", f"Exemple : ouvrage **{ex['ouvrage']}**, équipement **{ex['equipement']}** "
          f"(longueur maximale d'un repère : {charte.LONGUEUR_MAX_REPERE} caractères).", ""]
    l += ["## 2. Noms de variables", "",
          "Une variable se nomme **FAMILLE_REPÈRE_CODE** : la famille, le repère court de l'équipement dans l'ouvrage "
          "(sans le lieu), puis le code du signal du référentiel.", "",
          f"Exemple, pompe {repere} :", "", "| Famille | Signification | Nom produit |", "|---|---|---|"]
    for f in familles:
        if f in exemples:
            l.append(f"| {f} | {SIGNIFICATION_FAMILLES.get(f, '')} | `{exemples[f]}` |")
    l += ["", f"Un nom de variable fait au plus **{LONGUEUR_MAX_NOM} caractères** (Control Expert), n'emploie que des "
          "lettres, des chiffres et le tiret bas simple `_`, et est unique dans l'ouvrage. Le libellé de supervision "
          f"fait au plus {LONGUEUR_MAX_LIBELLE} caractères (réglable par ouvrage).", "",
          "OGIAS ne renomme jamais une variable de lui-même : un nom en collision est signalé, pas modifié.", "",
          "## 3. Règles de contrôle sur les noms", "", "| Règle | Titre | Gravité | Où corriger |", "|---|---|---|---|"]
    for r in coherence.REGLES.values():
        if r.code.startswith(("R-NOM-", "R-OUV-0")) or r.code in ("R-EQ-06", "R-EQ-07"):
            l.append(f"| {r.code} | {r.titre} | {r.gravite} | {r.corriger} |")
    l += ["", "## 4. Types d'équipement du référentiel", "", f"{len(cat.types)} types.", ""]
    for d in DOMAINES + ["Autres"]:
        types = [t for t in cat.types if (t.get("domaine") or "Autres") == d]
        if types:
            l += [f"**{d}** : " + ", ".join(f"`{t['code'].replace('--', '')}` {t['designation']}" for t in types), ""]
    return "\n".join(l).rstrip() + "\n"


def main(argv):
    texte = generer()
    if "--verifier" in argv:
        if not FICHIER.is_file() or FICHIER.read_text(encoding="utf-8") != texte:
            print("REGLES_DE_NOMMAGE.md n'est pas à jour : py outils/documenter_regles_nommage.py")
            return 1
        return 0
    FICHIER.write_text(texte, encoding="utf-8", newline="\n")
    print(f"Écrit : {FICHIER}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
