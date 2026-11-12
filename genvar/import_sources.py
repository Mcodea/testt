"""Lecture sans effet de bord des tables de variables de projets existants.

Les lectures sont volontairement conservatrices : un SCY non textuel ou une table
sans colonnes identifiables n'est jamais interprété par approximation.
"""
import csv
import io
import re
from pathlib import Path

CHAMPS = ("nom", "adresse", "type", "commentaire")
ALIASES = {
    "nom": {"nom", "variable", "nomvariable", "symbole", "symbol", "symbolname", "name", "mnemonique", "mnémonique", "repere", "repère"},
    "adresse": {"adresse", "address", "adresseautomate", "adresseplc", "objet", "object", "localisation", "topologicaladdress"},
    "type": {"type", "typedonnee", "typededonnee", "datatype", "typename", "typevariable"},
    "commentaire": {"commentaire", "comment", "description", "libelle", "libellé", "designation", "désignation"},
}
ADR = re.compile(r"^%(?:[IQM](?:W|F|D|X|B)?|S(?:W)?|K(?:W)?)[0-9][A-Za-z0-9._]*$", re.I)
SYMBOL = re.compile(r"^[A-Za-z_][\w.]*$")


def _normaliser(s):
    import unicodedata
    s = ''.join(x for x in unicodedata.normalize('NFKD', str(s).lower()) if not unicodedata.combining(x))
    return re.sub(r'[^a-z0-9]', '', s)


def _decodage(data):
    for enc in ('utf-8-sig', 'utf-16', 'cp1252'):
        try:
            s = data.decode(enc)
        except UnicodeError:
            continue
        if '\x00' not in s and sum(c.isprintable() or c in '\r\n\t' for c in s) / max(len(s), 1) >= 0.93:
            return s
    raise ValueError("Fichier non reconnu comme texte. Un export SCY binaire ou propriétaire ne peut pas être lu sans un exemple de son format ; exporter la table en CSV/Excel depuis le logiciel.")


def _colonnes(headers):
    correspondances = {}
    for i, val in enumerate(headers):
        cle = _normaliser(val)
        for champ, noms in ALIASES.items():
            if cle in {_normaliser(n) for n in noms} and champ not in correspondances:
                correspondances[champ] = i
    return correspondances


def charger_table(chemin, feuille=None, separateur=None):
    """Renvoie (entetes, lignes) sans transformer ni importer les variables.

    Pour un CSV ou SCY textuel, première ligne interprétée comme en-tête quand
    elle contient des noms de colonnes; sinon seules les lignes SCY ayant une
    adresse PL7 explicite sont acceptées, avec nom/adresse et commentaire.
    """
    p = Path(chemin)
    ext = p.suffix.lower()
    if ext == '.xlsx':
        try:
            from openpyxl import load_workbook
        except ImportError as ex:
            raise ValueError('La lecture Excel nécessite openpyxl : py -m pip install openpyxl') from ex
        wb = load_workbook(p, read_only=True, data_only=True)
        try:
            ws = wb[feuille] if feuille else wb.active
            raw = [[str(v).strip() if v is not None else '' for v in row] for row in ws.iter_rows(values_only=True)]
        finally:
            wb.close()
    elif ext in ('.csv', '.txt', '.scy'):
        s = _decodage(p.read_bytes()).lstrip('\ufeff')
        if not s.strip():
            raise ValueError('Le fichier est vide.')
        if separateur is None:
            try:
                separateur = csv.Sniffer().sniff(s[:8192], delimiters=';\t,|').delimiter
            except csv.Error:
                separateur = '\t' if '\t' in s else ';'
        raw = list(csv.reader(io.StringIO(s), delimiter=separateur))
        if ext == '.scy':
            # Plusieurs exports PL7 présentent une table avec adresse/symbole ;
            # on ne retient que les lignes où une adresse explicite est reconnue.
            if not _colonnes(raw[0]).get('nom') and 'nom' not in _colonnes(raw[0]):
                raw = _scy_lignes(raw)
    else:
        raise ValueError(f'Format non pris en charge : {ext}')
    raw = [r for r in raw if any(str(x).strip() for x in r)]
    if not raw:
        raise ValueError('Aucune ligne exploitable dans le fichier.')
    headers = raw[0]
    mapping = _colonnes(headers)
    if 'nom' in mapping and 'adresse' in mapping:
        if ext == '.scy':
            indice = mapping['adresse']
            erreurs = [i for i, row in enumerate(raw[1:], start=2)
                       if indice >= len(row) or not ADR.fullmatch(str(row[indice]).strip())]
            if erreurs:
                raise ValueError(f"SCY non exploitable sans risque de perte : adresse absente ou inconnue "
                                 f"sur {len(erreurs)} ligne(s), notamment ligne(s) "
                                 f"{', '.join(map(str, erreurs[:5]))}. Aucun import partiel effectué.")
        return headers, raw[1:]
    # Sans en-têtes: présenter les colonnes, avec choix manuel dans l'interface.
    largeur = max(len(r) for r in raw)
    return [f'Colonne {i + 1}' for i in range(largeur)], raw


def _scy_lignes(rows):
    """Support conservateur de SCY texte : lignes (adresse, symbole, commentaire)
    ou (symbole, adresse, commentaire). Les variantes inconnues sont refusées.
    """
    resultat = [['Adresse', 'Nom', 'Commentaire']]
    lignes_ambigues = []
    for numero, row in enumerate(rows, start=1):
        cells = [v.strip().strip('"') for v in row]
        if not any(cells) or (cells[0].startswith(('#', '//'))):
            continue
        indices = [i for i, v in enumerate(cells) if ADR.fullmatch(v)]
        if len(indices) != 1:
            lignes_ambigues.append(numero)
            continue
        a = indices[0]
        possibles = [i for i, v in enumerate(cells) if i != a and SYMBOL.fullmatch(v) and not ADR.fullmatch(v)]
        if not possibles:
            lignes_ambigues.append(numero)
            continue
        n = min(possibles, key=lambda i: abs(i-a))
        commentaire = ' '.join(v for i, v in enumerate(cells) if i not in (a,n) and v).strip()
        resultat.append([cells[a], cells[n], commentaire])
    if lignes_ambigues:
        raise ValueError('SCY non interprétable intégralement : ' + str(len(lignes_ambigues))
                         + ' ligne(s) ambiguë(s), notamment ' + ', '.join(map(str, lignes_ambigues[:8]))
                         + '. Aucun import partiel effectué ; utiliser un export PL7 explicite.')
    if len(resultat) == 1:
        raise ValueError("Format SCY non reconnu. Aucun couple adresse/symbole PL7 explicite. Fournir un export texte ou Excel ; aucune donnée n'a été modifiée.")
    return resultat


def verifier_lignes_import(lignes):
    """Vérifie une liste de tuples (nom, type, adresse, commentaire) sans l'appliquer.

    Les doublons contradictoires sont bloquants. Les doublons strictement
    identiques sont explicitement signalés et dédoublonnés. Les noms invalides
    bloquent l'import plutôt que d'être perdus silencieusement.
    Renvoie (lignes_uniques, avertissements).
    """
    uniques = []
    vus: dict[str, tuple[int, tuple[str, str, str, str]]] = {}
    avertissements, erreurs = [], []
    for numero, ligne in enumerate(lignes, start=1):
        if len(ligne) != 4:
            erreurs.append(f'Enregistrement {numero} : quatre champs attendus.')
            continue
        nom, typ, adr, com = tuple('' if v is None else str(v).strip() for v in ligne)
        if not nom or not SYMBOL.fullmatch(nom):
            erreurs.append(f'Enregistrement {numero} : nom manquant ou invalide ({nom!r}).')
            continue
        if nom in vus:
            premier, valeur = vus[nom]
            if valeur != (nom, typ, adr, com):
                erreurs.append(f'Enregistrement {numero} : conflit sur {nom} avec l’enregistrement {premier} '
                               '(type, adresse ou commentaire différent).')
            else:
                avertissements.append(f'Enregistrement {numero} : doublon strictement identique {nom}, '
                                      f'déjà présent en {premier}.')
            continue
        valeur = (nom, typ, adr, com)
        vus[nom] = (numero, valeur)
        uniques.append(valeur)
        if not adr:
            avertissements.append(f'Enregistrement {numero} : adresse manquante pour {nom} ; à vérifier.')
        if not typ:
            avertissements.append(f'Enregistrement {numero} : type inconnu pour {nom} ; à confirmer.')
    if erreurs:
        raise ValueError('Import interrompu, aucune donnée appliquée.\n' + '\n'.join(erreurs[:25])
                         + (f'\n... et {len(erreurs)-25} autre(s) conflit(s).' if len(erreurs)>25 else ''))
    if not uniques:
        raise ValueError('Aucune variable exploitable ; import annulé.')
    return uniques, avertissements


def rapport_import(nombre_lignes, lignes_uniques, avertissements):
    """Résumé de prévalidation ; toutes les pertes doivent être explicites."""
    doublons = sum('doublon strictement identique' in a for a in avertissements)
    return (f'Lignes de données lues : {nombre_lignes}\n'
            f'Variables distinctes : {len(lignes_uniques)}\n'
            f'Doublons strictement identiques : {doublons}\n'
            f'Lignes non comptabilisées : {nombre_lignes-len(lignes_uniques)-doublons}\n'
            f'Avertissements : {len(avertissements)}')


def preparer_lignes(headers, rows, correspondances):
    """Contrôle complet avant insertion. Renvoie (variables, avertissements)."""
    if 'nom' not in correspondances or 'adresse' not in correspondances:
        raise ValueError('Associer au minimum les colonnes Nom et Adresse.')
    indices = list(correspondances.values())
    if len(indices) != len(set(indices)):
        raise ValueError('Une même colonne ne peut pas alimenter plusieurs champs (Nom, Adresse, Type, Commentaire).')
    lignes = []
    for ligne in rows:
        def get(k):
            ix = correspondances.get(k)
            return str(ligne[ix]).strip() if ix is not None and ix < len(ligne) and ligne[ix] is not None else ''
        valeurs = tuple(get(k) for k in ('nom', 'type', 'adresse', 'commentaire'))
        if any(str(v).strip() for v in ligne if v is not None):
            # Ne jamais masquer une ligne où seules les colonnes non mappées
            # contiennent des données : elle doit apparaître comme erreur.
            lignes.append(valeurs)
    return verifier_lignes_import(lignes)
