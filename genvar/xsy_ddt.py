"""Lecture prudente des exports XSY de Control Expert avec expansion des DDT.

Les champs d'une instance sont enregistrés comme chemins symboliques, PAS comme
adresses Modbus. `ExtractBit` provient du XSY et n'est pas un offset mémoire.
Aucune écriture vers l'automate ou vers TOPKAPI n'est effectuée ici.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import re
import xml.etree.ElementTree as ET

MAX_BYTES = 15 * 1024 * 1024
MAX_DEPTH = 16
MAX_FIELDS = 50000
# Types élémentaires communs Control Expert (extension explicite possible).
BASE_TYPES = {
    'BOOL', 'EBOOL', 'BYTE', 'WORD', 'DWORD', 'LWORD', 'SINT', 'USINT',
    'INT', 'UINT', 'DINT', 'UDINT', 'LINT', 'ULINT', 'REAL', 'LREAL',
    'TIME', 'DATE', 'TOD', 'DT', 'DTL', 'STRING', 'WSTRING', 'CHAR',
}


def _tag(tag):
    return tag.rsplit('}', 1)[-1]


def _enfants(element, tag):
    return [e for e in element if _tag(e.tag) == tag]


def _enfant(element, tag):
    return next(iter(_enfants(element, tag)), None)


def _commentaire(element):
    c = _enfant(element, 'comment')
    return ''.join(c.itertext()).strip() if c is not None else ''


def _extract_bit(element):
    for attr in _enfants(element, 'attribute'):
        if attr.get('name', '').lower() == 'extractbit':
            return attr.get('value', '')
    return ''


def _primitif(typ):
    upper = typ.upper().strip()
    return upper in BASE_TYPES or bool(re.fullmatch(r'(?:W?STRING)\s*\[\s*\d+\s*\]', upper))


@dataclass(frozen=True)
class ChampXSY:
    nom: str
    type_logique: str
    adresse: str
    commentaire: str
    nature: str = 'Principale'  # 'Principale' ou 'Champ DDT'
    parent: str = ''
    type_parent: str = ''
    adresse_parent: str = ''
    extract_bit: str = ''
    # Pas une adresse protocolaire : chemin symbolique issu de l'export.
    chemin_symbolique: str = ''

    def ligne(self):
        return (self.nom, self.type_logique, self.adresse, self.commentaire)


@dataclass
class AnalyseXSY:
    parents: list[ChampXSY] = field(default_factory=list)
    champs: list[ChampXSY] = field(default_factory=list)
    definitions_ddt: int = 0
    avertissements: list[str] = field(default_factory=list)
    sha256: str = ''
    fichier: str = ''

    @property
    def lignes(self):
        return [c.ligne() for c in self.parents + self.champs]

    @property
    def index(self):
        return {c.nom: c for c in self.parents + self.champs}

    @property
    def complet(self):
        return not self.avertissements


def analyser_xsy(path) -> AnalyseXSY:
    """Développe les DDT connus et signale les branches impossibles à interpréter.

    Ne calcule PAS d'offset, d'adresse `%MW`, ni de position bit pour les membres.
    Les définitions récursives, tableaux non détaillés, types manquants et tailles
    excessives sont signalés au lieu d'être silencieusement ignorés.
    """
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError(f'XSY trop volumineux (> {MAX_BYTES // 1048576} Mio).')
    data = path.read_bytes()
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('XSY avec déclaration DTD/ENTITY non accepté pour un import sécurisé.')
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError(f'XML/XSY illisible : {exc}') from exc
    if _tag(root.tag) != 'VariablesExchangeFile':
        raise ValueError("Ce fichier n'est pas un export XSY Control Expert.")
    block = _enfant(root, 'dataBlock')
    if block is None:
        raise ValueError('XSY sans bloc dataBlock : aucune variable importée.')
    result = AnalyseXSY(sha256=hashlib.sha256(data).hexdigest(), fichier=path.name)
    definitions: dict[str, list[ET.Element] | None] = {}
    for source in _enfants(root, 'DDTSource'):
        code = source.get('DDTName', '').strip()
        if not code or code in definitions:
            result.avertissements.append(f'DDT absent ou défini plusieurs fois : {code or "(sans nom)"}.')
            continue
        structure = _enfant(source, 'structure')
        if structure is None:
            result.avertissements.append(f'DDT {code} : aucune structure détaillée dans le fichier.')
            definitions[code] = None
        else:
            definitions[code] = _enfants(structure, 'variables')
    result.definitions_ddt = len(definitions)

    def developper(parent, parent_type, parent_adresse, code_type, prefixe, chaine):
        if len(result.champs) >= MAX_FIELDS:
            raise ValueError(f'Limite de sécurité de {MAX_FIELDS} champs DDT atteinte : import annulé.')
        if code_type in chaine:
            result.avertissements.append(f'DDT récursif : {prefixe} ({code_type}).')
            return
        if len(chaine) >= MAX_DEPTH:
            result.avertissements.append(f'DDT trop profond : {prefixe} (>{MAX_DEPTH} niveaux).')
            return
        membres = definitions.get(code_type)
        if membres is None:
            result.avertissements.append(f'DDT non défini / sans structure : {prefixe} ({code_type}).')
            return
        for element in membres:
            nom = element.get('name', '').strip()
            typ = element.get('typeName', '').strip()
            if not nom or not typ:
                result.avertissements.append(f'Champ DDT incomplet dans {prefixe} : nom ou type absent.')
                continue
            chemin = prefixe + '.' + nom
            if typ in definitions:
                developper(parent, parent_type, parent_adresse, typ, chemin, chaine + (code_type,))
                continue
            if not _primitif(typ):
                result.avertissements.append(f'Champ non développé : {chemin} (type {typ}).')
                # Le champ est conservé comme élément opaque, non masqué.
            bit = _extract_bit(element)
            if bit and not re.fullmatch(r'\d+', bit):
                result.avertissements.append(f'ExtractBit non numérique : {chemin} = {bit}.')
            result.champs.append(ChampXSY(
                nom=chemin, type_logique=typ, adresse='',
                commentaire=_commentaire(element), nature='Champ DDT',
                parent=parent, type_parent=parent_type,
                adresse_parent=parent_adresse, extract_bit=bit,
                chemin_symbolique=chemin,
            ))
            if len(result.champs) > MAX_FIELDS:
                raise ValueError('XSY : trop de champs, import annulé.')

    seen = set()
    for element in _enfants(block, 'variables'):
        nom = element.get('name', '').strip()
        typ = element.get('typeName', '').strip()
        adresse = element.get('topologicalAddress', '').strip()
        if not nom or not typ:
            result.avertissements.append('Déclaration principale sans nom ou type dans dataBlock.')
            continue
        if nom in seen:
            result.avertissements.append(f'Variable principale dupliquée : {nom}.')
        seen.add(nom)
        result.parents.append(ChampXSY(nom, typ, adresse, _commentaire(element), chemin_symbolique=nom))
        if typ in definitions:
            developper(nom, typ, adresse, typ, nom, ())
        elif not _primitif(typ):
            result.avertissements.append(f'Type principal non résolu : {nom} ({typ}).')
    if not result.parents:
        raise ValueError('XSY sans aucune variable principale exploitable.')
    # Ne jamais masquer une collision entre chemins résolus.
    noms = [x.nom for x in result.parents + result.champs]
    if len(noms) != len(set(noms)):
        result.avertissements.append('Noms de variables/chemins DDT dupliqués : import à examiner.')
    return result
