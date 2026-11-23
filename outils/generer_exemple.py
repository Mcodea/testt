"""Génère l'ouvrage d'exemple FICTIF livré à part (cahier V1-9-05) : exemples/OGIAS_exemple_XTSTRV01.ouvrage.json.

    py outils/generer_exemple.py            # écrit le fichier
    py outils/generer_exemple.py --verifier # échoue si le fichier ne correspond plus au moteur

Lieu fictif XTST, réservoir fictif, sept équipements génériques dont quatre validés : aucune donnée réelle. Pour l'essayer, copier le fichier
dans le dossier des ouvrages (Fichier › Dossier des ouvrages) puis l'ouvrir depuis « Mes ouvrages »."""
import json
import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
CIBLE = RACINE / "exemples" / "OGIAS_exemple_XTSTRV01.ouvrage.json"
EQUIPEMENTS = (("PM", "01", "Pompe de relevage 1"), ("PM", "02", "Pompe de relevage 2"), ("HV", "01", "Vanne d'isolement"),
               ("MV", "01", "Vanne motorisée de sortie"), ("LT", "01", "Niveau du réservoir"), ("FT", "01", "Débit de départ"),
               ("PT", "01", "Pression de refoulement"))


def fabriquer() -> dict:
    """Contenu normalisé (sans les dates) de l'ouvrage d'exemple produit par le moteur."""
    from sorep_web.serveur import Application
    ancien = os.environ.get("SOREP_DATA_DIR")
    with tempfile.TemporaryDirectory(prefix="ogias-exemple-") as tmp:
        os.environ["SOREP_DATA_DIR"] = tmp
        try:
            app = Application()
            app.appeler("nouveau", {"mode": "Neuf"})
            app.listes_ouvrage_action({"action": "ajouter", "groupe": "lieux", "code": "XTST", "libelle": "Lieu fictif d'exemple"})
            app.appeler("fiche_ouvrage", {"action": "creer", "identification": {
                "lieu": "XTST", "code_ouvrage": "RV", "numero_ouvrage": "01", "libelle": "Réservoir fictif d'exemple",
                "automate": "Sch - M580", "revision": "A"}})
            idents = []
            for type_, numero, libelle in EQUIPEMENTS:
                i = app.appeler("ajouter_equipement", {"type": type_, "numero": numero, "se": "00", "libelle": libelle})["ident"]
                app.appeler("decider_proposition", {"ident_eq": i, "decision": "retenir"})
                idents.append(i)
            for i in idents[:4]:                       # les capteurs analogiques gardent leur échelle à paramétrer : l'exemple
                app.appeler("valider_equipements", {"idents": [i], "valide": True})    # laisse donc du travail à faire
            with open(app.s.chemin, encoding="utf-8") as f:
                contenu = json.load(f)
            app.appeler("fermer", {})
            return contenu
        finally:
            if ancien is None:
                os.environ.pop("SOREP_DATA_DIR", None)
            else:
                os.environ["SOREP_DATA_DIR"] = ancien


def normaliser(contenu: dict) -> dict:
    """Résumé stable de l'ouvrage (identification et équipements) : ni horodatage, ni identifiant tiré au hasard."""
    o = contenu["ouvrage"]
    return {"identification": {k: o.get(k) for k in ("lieu", "code_ouvrage", "numero_ouvrage", "libelle", "automate", "revision", "mode")},
            "equipements": [(e["sous_ensemble"], e["type"], e["numero"], e["libelle"], bool(e["valide"])) for e in o.get("equipements", [])]}


def main(argv) -> int:
    contenu = fabriquer()
    if "--verifier" in argv:
        if not CIBLE.is_file() or normaliser(json.loads(CIBLE.read_text(encoding="utf-8"))) != normaliser(contenu):
            print("L'ouvrage d'exemple n'est plus à jour : py outils/generer_exemple.py")
            return 1
        return 0
    CIBLE.parent.mkdir(exist_ok=True)
    CIBLE.write_text(json.dumps(contenu, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Écrit : {CIBLE}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
