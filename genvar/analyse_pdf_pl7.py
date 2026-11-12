"""Analyse *documentaire* de dossiers programmes PDF (PL7 / Control Expert).

Pas d'OCR ni de raisonnement automatique sur les schémas Ladder/FBD.
Les références R/W prouvent des occurrences documentées, pas des liens causaux.
Les adresses repérées ne sont JAMAIS déclarées accessibles à la supervision.
Ce module est indépendant de PySide6 et des fichiers d'ouvrage SOREP.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import csv
import hashlib
import json
import re
import unicodedata

# Ne pas confondre les variables nommées du programme avec les adresses physiques.
ADDR = r'%(?:TM|MN|DR|[IQMSKX](?:W|F|D|X)?)\d+(?:\.\d+)*(?::X\d+)?(?:\.[TQRV])?'
RE_ADDR = re.compile(r'(?<![\w])' + ADDR + r'(?![\w])', re.I)
RE_SECTION = re.compile(r'\b(?:MAST|FAST|SR\d*|PRL|POST|CHART|AUX|SR)\b[\w.\-/]*', re.I)
RE_USAGE = re.compile(r'(?:^|[\s|;,])(?P<mode>R/W|RW|R|W)(?=$|[\s|;,])', re.I)
RE_LABEL = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{1,80}$')
RE_COMMENTS = re.compile(r'\b(?:REF[ÉE]RENCES? CROIS[ÉE]ES?|CROSS REFERENCES?)\b', re.I)
RE_MW = re.compile(r'^%MW(\d+)$', re.I)
RE_SIMPLE_IL = re.compile(r'^\s*(LD|ST)\s+(' + ADDR + r')\s*$', re.I)
# Les expressions OPERATE sont des indices de dépendance documentaire, jamais un graphe causal complet.
RE_AFFECTATION = re.compile(r'(?P<gauche>' + ADDR + r')\s*:=\s*(?P<droite>[^|\n]{1,180})', re.I)
RE_FOLIO = re.compile(r'\bFOLIO\s*:\s*(?P<code>[0-9]+(?:\.[0-9]+)*)\s*[-–]\s*\d+', re.I)
RE_TITRE_REF = re.compile(r'^(?:5\s+)?REFERENCES\s+CROISEES\b', re.I)
RE_TITRE_VAR = re.compile(r'^(?:6\s+)?(?:VARIABLES|TABLE DES VARIABLES)\b', re.I)
MAX_PAGES = 900
MAX_BYTES = 200 * 1024 * 1024


def normaliser(t: str) -> str:
    d = unicodedata.normalize('NFD', t or '')
    return ''.join(c for c in d if unicodedata.category(c) != 'Mn').upper()


@dataclass
class Occurrence:
    adresse: str
    page: int
    contexte: str
    rubrique: str
    usage: str = ''
    section: str = ''
    symbole: str = ''


@dataclass
class LienDocumentaire:
    origine: str
    destination: str
    page: int
    justification: str = 'Deux instructions IL consécutives LD puis ST, sans opération intermédiaire'
    statut: str = 'Indice à vérifier : ne prouve pas une exposition à la supervision'


@dataclass
class IndiceSymbole:
    adresse: str
    symbole: str
    commentaire: str
    page: int
    source: str = 'Tableau de variables imprimé : association à vérifier'


@dataclass
class AffectationDocumentaire:
    destination: str
    dependances: list[str]
    expression: str
    page: int
    section: str = ''
    nature: str = 'OPERATE : expression d’affectation imprimée, dépendance syntaxique uniquement'
    statut: str = 'À examiner : aucune qualification supervision'


@dataclass
class InventairePDF:
    fichier: str
    empreinte_sha256: str
    pages: int
    pages_texte: int
    occurrences: list[Occurrence] = field(default_factory=list)
    adresses_uniques: list[str] = field(default_factory=list)
    pages_references_croisees: list[int] = field(default_factory=list)
    zones_memoires_candidates: list[dict] = field(default_factory=list)
    liens_il_simples: list[LienDocumentaire] = field(default_factory=list)
    affectations_documentaires: list[AffectationDocumentaire] = field(default_factory=list)
    indices_symboles: list[IndiceSymbole] = field(default_factory=list)
    avertissements: list[str] = field(default_factory=list)

    def resume(self) -> str:
        o = [
            'ANALYSE DOCUMENTAIRE PDF — SOREP (non qualifiante)',
            f'Fichier : {self.fichier}',
            f'SHA256 : {self.empreinte_sha256}',
            f'Pages : {self.pages} | Pages avec texte : {self.pages_texte}',
            f'Occurrences d’adresses : {len(self.occurrences)} | Adresses uniques : {len(self.adresses_uniques)}',
            f'Pages « références croisées » repérées : {", ".join(map(str,self.pages_references_croisees)) or "aucune"}',
            f'Groupes %MW consécutifs (simples indices) : {len(self.zones_memoires_candidates)}',
            f'Indices de dépendance IL stricts LD/ST : {len(self.liens_il_simples)}',
            f'Affectations textuelles OPERATE : {len(self.affectations_documentaires)}',
            f'Associations adresse / symbole (indices documentaires) : {len(self.indices_symboles)}',
            'AUCUNE correspondance fonctionnelle, adresse TOPKAPI ni relation R/W n’est validée automatiquement.',
        ]
        from .revue_documentaire import preparer_revue
        revue = preparer_revue(self)
        pupitres = sum('pupitre/IHM' in x.categorie for x in revue)
        sources_es = sum(bool(x.origine_potentielle) for x in revue)
        o.append(f'Revue proposée : {len(revue)} adresses ; {sources_es} ayant un lien syntaxique vers une entrée ; {pupitres} indice(s) pupitre/IHM.')
        o.append('Le fichier revue_variables_pdf.csv est à examiner ; aucune ligne n’est prévalidée.')
        if self.avertissements:
            o += ['', 'AVERTISSEMENTS :', *(' - ' + x for x in self.avertissements)]
        o += ['', 'LIENS IL POSSIBLES (textes seulement, à vérifier) :']
        for x in self.liens_il_simples[:20]:
            o.append(f'  p.{x.page} : {x.origine} -> {x.destination} (LD / ST consécutifs)')
        o += ['', 'AFFECTATIONS DOCUMENTÉES (pas de preuve d’accès TOPKAPI) :']
        for a in self.affectations_documentaires[:25]:
            deps = ', '.join(a.dependances) if a.dependances else '(constante / aucune variable détectée)'
            o.append(f'  p.{a.page} | {a.destination} <- {deps} | {a.expression}')
        o += ['', 'SYMBOLISATION RETROUVÉE DANS LES TABLEAUX (à vérifier visuellement) :']
        for symbole in self.indices_symboles[:30]:
            o.append(f'  p.{symbole.page} | {symbole.adresse} -> {symbole.symbole} | {symbole.commentaire}')
        o += ['', 'EXEMPLES D’OCCURRENCES DOCUMENTÉES :']
        for occurrence in self.occurrences[:35]:
            o.append(f'  p.{occurrence.page} | {occurrence.adresse} | {occurrence.usage or "?"} | {occurrence.section or "section non établie"} | {occurrence.contexte}')
        return '\n'.join(o)

    def enregistrer(self, dossier: str | Path):
        p = Path(dossier)
        p.mkdir(parents=True, exist_ok=True)
        (p / 'analyse_pdf.json').write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding='utf-8')
        with (p / 'occurrences_pdf.csv').open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(asdict(Occurrence('',0,'','')).keys()), delimiter=';')
            w.writeheader()
            w.writerows(asdict(x) for x in self.occurrences)
        with (p / 'affectations_pdf.csv').open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(['destination','dependances','expression','page','section','statut'])
            for a in self.affectations_documentaires:
                writer.writerow([a.destination,' | '.join(a.dependances),a.expression,a.page,a.section,a.statut])
        with (p / 'symboles_pdf.csv').open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['adresse','symbole','commentaire','page','source'], delimiter=';')
            w.writeheader()
            w.writerows(asdict(x) for x in self.indices_symboles)
        (p / 'bilan_pdf.txt').write_text(self.resume(), encoding='utf-8')
        # Rapport d'aide au tri, indépendant des règles de génération TOPKAPI.
        from .revue_documentaire import enregistrer_revue
        enregistrer_revue(self, p)


def _rubrique(texte: str) -> str:
    """Détecte la rubrique PL7 sur ses titres ET sur le folio imprimé.

    La table des matières est traitée avant tout autre indice pour ne pas prendre
    « 5 Références croisées... 7p » pour une page de références croisées.
    """
    lignes = [normaliser(l).strip() for l in texte.splitlines() if l.strip()]
    debut = lignes[:30]
    if any(l == 'SOMMAIRE' or re.match(r'^(2\s+)?SOMMAIRE\b', l) for l in debut[:12]):
        return 'Sommaire'
    if any(RE_TITRE_REF.match(l) and '..' not in l for l in debut[:12]):
        return 'Références croisées (indice de rubrique)'
    if any(RE_TITRE_VAR.match(l) and '..' not in l for l in debut[:12]):
        return 'Variables (indice de rubrique)'
    # Dans les impressions PL7, le titre de rubrique est parfois uniquement
    # présent dans le pied de page « Auteur ... 5 Références croisées ».
    codes = [m.group('code') for l in lignes for m in RE_FOLIO.finditer(l)]
    if any(c == '5' or c.startswith('5.') for c in codes):
        return 'Références croisées (indice de rubrique)'
    if any(c == '6' or c.startswith('6.') for c in codes):
        return 'Variables (indice de rubrique)'
    if any(c == '4' or c.startswith('4.') for c in codes):
        return 'Programme (indice de rubrique)'
    if any('REFERENCES CROISEES' in l and '..' not in l and 'AUTEUR' in l for l in lignes[-15:]):
        return 'Références croisées (indice de rubrique)'
    if any('6 VARIABLES' in l and 'AUTEUR' in l for l in lignes[-15:]):
        return 'Variables (indice de rubrique)'
    if any(l.startswith(('PROGRAMME','MAST-','MAST ','CHART - PAGE')) for l in debut[:12]):
        return 'Programme (indice de rubrique)'
    return 'Non déterminée'


def affectations_depuis_texte(texte: str, page: int, rubrique: str, section: str = '') -> list[AffectationDocumentaire]:
    """Cherche les expressions `destination:=expression` visibles dans la section Programme.

    Une expression PL7 ne prouve pas le sens hydraulique ni l'exposition réseau.
    La même expression peut être imprimée deux fois (rung et tableau) ; dédoublonner
    uniquement à l'échelle de la page.
    """
    if rubrique != 'Programme (indice de rubrique)':
        return []
    resultat = []
    vus = set()
    for ligne in texte.splitlines():
        if len(ligne) > 900 or 'LISTE DE VARIABLES' in normaliser(ligne):
            continue
        for m in RE_AFFECTATION.finditer(ligne):
            dest = m.group('gauche').upper()
            rhs = m.group('droite').strip()
            # Couper un tableau/une note accolée à l'expression, ne jamais deviner.
            rhs = re.split(r'\s{2,}(?=[A-Za-zÀ-ÿ])', rhs, maxsplit=1)[0].strip()
            if not rhs or rhs.startswith(('LISTE','REPERE','SYMBOLE')):
                continue
            expression = f'{dest}:={rhs}'
            # Une même page peut imprimer un rung plusieurs fois.
            cle = re.sub(r'\s+', '', expression.upper())
            if cle in vus:
                continue
            vus.add(cle)
            deps = list(dict.fromkeys(x.group().upper() for x in RE_ADDR.finditer(rhs)))
            resultat.append(AffectationDocumentaire(dest, deps, expression, page, section))
    return resultat


def _symbole_sur_ligne(ligne: str, adresse: str) -> str:
    """Conservateur : prend un symbole uniquement immédiatement accolé à l'adresse."""
    reste = ligne.split(adresse, 1)[-1]
    fragments = re.split(r'\s{2,}|\t|\||;', reste.strip(), maxsplit=1)
    premier = (fragments[0].split() or [''])[0]
    return premier if RE_LABEL.fullmatch(premier) and premier.upper() not in {'R','W','RW','R/W'} else ''


def _grouper_mw(adresses):
    nums = sorted(set(int(m.group(1)) for a in adresses if (m:=RE_MW.fullmatch(a))))
    groups = []
    courant: list[int] = []
    for x in nums:
        if not courant or x == courant[-1] + 1:
            courant.append(x)
        else:
            if len(courant) >= 3: groups.append({'debut':f'%MW{courant[0]}','fin':f'%MW{courant[-1]}','taille':len(courant),'preuve':'seulement contiguïté des adresses'})
            courant = [x]
    if len(courant) >= 3: groups.append({'debut':f'%MW{courant[0]}','fin':f'%MW{courant[-1]}','taille':len(courant),'preuve':'seulement contiguïté des adresses'})
    return groups




def symboles_depuis_texte(texte: str, page: int, rubrique: str) -> list[IndiceSymbole]:
    """Indices provenant de `REPERE / SYMBOLE / COMMENTAIRE` imprimé.

    Dans certains PDF PL7, chaque colonne est extraite sur sa propre ligne.
    Par prudence, une adresse sans symbole immédiatement identifiable est omise.
    """
    if rubrique not in {'Programme (indice de rubrique)', 'Variables (indice de rubrique)'}:
        return []
    lines = [l.strip() for l in texte.splitlines() if l.strip()]
    found = []
    vu = set()
    table_active = False
    ignorer = {'REPERE', 'SYMBOLE', 'COMMENTAIRE', 'R', 'W', 'RW', 'R/W',
               'OPERATE','COMPARE','LISTE','MAST','MAST-POST','MAST-PRL'}
    for i, line in enumerate(lines):
        n = normaliser(line)
        if rubrique == 'Variables (indice de rubrique)':
            # Ligne de table : « %MW10 TEMP_C valeur calculée ».
            mligne = re.match(r'^(' + ADDR + r')\s+([A-Za-z_][A-Za-z0-9_]{1,80})(?:\s+(.*))?$', line, re.I)
            if mligne and normaliser(mligne.group(2)) not in ignorer:
                cle = (mligne.group(1).upper(),mligne.group(2),page)
                if cle not in vu:
                    found.append(IndiceSymbole(mligne.group(1).upper(), mligne.group(2),
                                               (mligne.group(3) or '')[:200], page))
                    vu.add(cle)
                continue
        if 'LISTE DE VARIABLES UTILISEES DANS LE RUNG' in n or n in {'REPERE SYMBOLE COMMENTAIRE', 'SYMBOLE REPERE COMMENTAIRE'}:
            table_active = True
            continue
        if n.startswith(('AUTEUR :','FOLIO :','CHART - PAGE')):
            table_active = False
        # Désignations en colonne sans liste de variables imprimées non maîtrisées :
        # ne pas les interpréter par intuition.
        if not table_active:
            continue
        if RE_ADDR.fullmatch(line.upper()) and i+1 < len(lines):
            suivant = lines[i+1]
            token = suivant.split()[0] if suivant else ''
            if (RE_LABEL.fullmatch(token) and normaliser(token) not in ignorer and
                    not RE_ADDR.fullmatch(token.upper()) and not suivant.startswith('%')):
                commentaire = ''
                if i+2 < len(lines):
                    commentaire_candidat = lines[i+2]
                    norm = normaliser(commentaire_candidat)
                    if (commentaire_candidat and not commentaire_candidat.startswith('%') and
                        norm not in ignorer and not norm.startswith(('LISTE DE VARIABLES','AUTEUR :', 'FOLIO :'))):
                        commentaire = commentaire_candidat[:200]
                cle = (line.upper(), token, page)
                if cle not in vu:
                    found.append(IndiceSymbole(line.upper(), token, commentaire, page))
                    vu.add(cle)
    return found

def tracer_origines(resultat: InventairePDF, destination: str, profondeur_max: int = 6, chemins_max: int = 100) -> list[dict]:
    """Remonte uniquement les affectations textuelles `A:=B...`, avec pages de preuve.

    Les dépendances ne signifient PAS que le signal est sûr, de même sens,
    ni destiné à une supervision. Si plusieurs écritures existent, on conserve
    toutes les branches, sans les fusionner dans une vérité unique.
    """
    cible = (destination or '').upper().strip()
    if not RE_ADDR.fullmatch(cible):
        raise ValueError('Adresse cible invalide (exemple : %MW5, %MW100:X3).')
    if not (1 <= profondeur_max <= 20 and 1 <= chemins_max <= 1000):
        raise ValueError('Limites de parcours invalides.')
    index: dict[str, list[AffectationDocumentaire]] = {}
    for a in resultat.affectations_documentaires:
        index.setdefault(a.destination, []).append(a)
    chemins: list[dict[str, object]] = []
    en_attente: list[tuple[str, list[str], list[dict[str, object]], frozenset[str]]] = [(cible, [cible], [], frozenset([cible]))]
    while en_attente and len(chemins) < chemins_max:
        actuel, nodes, pieces, visites = en_attente.pop(0)
        options = index.get(actuel, [])
        if not options or len(nodes) > profondeur_max:
            chemins.append({'chaine': nodes, 'preuves': pieces,
                            'fin': 'aucune affectation directe retrouvée' if not options else 'limite de profondeur'})
            continue
        for a in options:
            preuve: dict[str, object] = {'page': a.page, 'expression': a.expression, 'destination': a.destination}
            if not a.dependances:
                chemins.append({'chaine': nodes, 'preuves': pieces + [preuve], 'fin': 'affectation constante / sans variable détectée'})
            for dep in a.dependances:
                if dep in visites:
                    chemins.append({'chaine': nodes + [dep], 'preuves': pieces + [preuve], 'fin': 'boucle détectée'})
                else:
                    en_attente.append((dep, nodes + [dep], pieces + [preuve], visites | {dep}))
    return chemins[:chemins_max]


def analyser_pdf(fichier: str | Path) -> InventairePDF:
    try:
        import fitz
    except ImportError as e:
        raise RuntimeError("Analyse PDF indisponible : installer PyMuPDF (py -m pip install PyMuPDF).") from e
    chemin = Path(fichier).expanduser().resolve()
    if not chemin.exists():
        raise FileNotFoundError(str(chemin))
    if chemin.stat().st_size > MAX_BYTES:
        raise ValueError('PDF dépassant la limite de sécurité 200 Mo.')
    digest = hashlib.sha256(chemin.read_bytes()).hexdigest()
    doc = fitz.open(str(chemin))
    try:
        if doc.is_encrypted:
            raise ValueError('PDF chiffré : fournir une version lisible autorisée.')
        if len(doc) > MAX_PAGES:
            raise ValueError(f'PDF trop long : {len(doc)} pages (maximum {MAX_PAGES}).')
        result = InventairePDF(chemin.name, digest, len(doc), 0)
        for i in range(len(doc)):
            page_document = doc.load_page(i)
            texte = page_document.get_text('text', sort=True)
            if len(texte.strip()) >= 30:
                result.pages_texte += 1
            rubrique = _rubrique(texte)
            lignes = texte.splitlines()
            if rubrique == 'Références croisées (indice de rubrique)':
                result.pages_references_croisees.append(i+1)
            section_page = next((x for l in lignes[:25] for x in RE_SECTION.findall(l)), '')
            result.affectations_documentaires.extend(affectations_depuis_texte(texte, i+1, rubrique, section_page))
            result.indices_symboles.extend(symboles_depuis_texte(texte, i+1, rubrique))
            precedente_ld = None
            for ligne in lignes:
                if not ligne.strip():
                    continue
                # Prudence : uniquement deux instructions IL isolées ET consécutives.
                # Un commentaire, un AND/OR, une temporisation ou une autre instruction
                # rompt la paire ; pas de reconstruction de Ladder ou FBD ici.
                match_il = RE_SIMPLE_IL.fullmatch(ligne)
                if rubrique == 'Programme (indice de rubrique)' and match_il:
                    operation, adresse_il = match_il.group(1).upper(), match_il.group(2).upper()
                    if operation == 'ST' and precedente_ld and precedente_ld != adresse_il:
                        result.liens_il_simples.append(LienDocumentaire(precedente_ld, adresse_il, i+1))
                    precedente_ld = adresse_il if operation == 'LD' else None
                else:
                    precedente_ld = None
                if len(ligne) > 800:
                    ligne = ligne[:800]
                for m in RE_ADDR.finditer(ligne):
                    adr = m.group().upper()
                    usages = list(RE_USAGE.finditer(ligne))
                    # R/W est un usage possible, mais il peut apparaître dans un commentaire.
                    # Il est affiché comme indice documentaire, jamais comme preuve de sens causal.
                    usage = usages[-1].group('mode').upper() if usages else ''
                    sections = RE_SECTION.findall(ligne)
                    result.occurrences.append(Occurrence(adr, i+1, ligne.strip()[:300], rubrique, usage,
                                                         sections[-1] if sections else (section_page if rubrique == 'Programme (indice de rubrique)' else ''),
                                                         _symbole_sur_ligne(ligne, adr)))
        result.adresses_uniques = sorted(set(o.adresse for o in result.occurrences))
        result.zones_memoires_candidates = _grouper_mw(result.adresses_uniques)
        if result.pages_texte == 0:
            result.avertissements.append('PDF sans couche texte exploitable : document probablement scanné. Extraction automatique refusée, pas d’OCR implicite.')
        elif result.pages_texte < result.pages // 2:
            result.avertissements.append('Moins de la moitié des pages possèdent du texte : inventaire probablement incomplet.')
        if not result.pages_references_croisees:
            result.avertissements.append('Aucune rubrique de références croisées clairement détectée.')
        result.avertissements.append('Les indices R/W, les symboles, les commentaires et les sections sont extraits au mieux de la mise en page ; vérification visuelle nécessaire.')
        result.avertissements.append('Les liens LD/ST et les affectations OPERATE sont des dépendances syntaxiques documentaires, pas une interprétation Ladder/FBD ni une preuve d’acquisition TOPKAPI.')
        result.avertissements.append('Une proximité de mots %MW ne démontre ni une table d’échanges ni une liaison TOPKAPI.')
        return result
    finally:
        doc.close()
