"""Fichiers d'import de variables TOPKAPI (« .$$t », en-tête « Version 1 »).

Format relevé sur un projet TOPKAPI réel (application de 2008 modifiée jusqu'en 2018, 70 fichiers .$$t de
neuf stations, relus et réécrits à l'octet près) — il n'a PAS encore été essayé dans TOPKAPI 6.3 :
- encodage Windows-1252 (Latin-1), fins de ligne CRLF ;
- ligne 1 : « Version<TAB>1 » ; ligne 2 : 38 titres de colonnes (VAR_MNEMO … VAR_SYNO) ;
- une ligne par variable, 38 champs séparés par des tabulations ; seuls les 4 premiers sont renseignés dans
  le projet de référence : mnémonique, adresse, code de format, libellé ;
- adresse : numéro de mot décimal (« 2100 ») ou mot$bit avec le bit en hexadécimal 0 à F (« 400$A ») ;
- codes de format observés : 0 (bit, ou mot utilisé en télécommande), 2 (mot 16 bits), 102 et 105
  (valeurs sur deux mots consécutifs : pas d'adresse de 2 en 2). La signification exacte de 102 et 105
  (entier 32 bits, réel…) n'est PAS documentée ici : elle est à confirmer avec AREAL ou par un essai.

Dans le projet de référence, l'adresse TOPKAPI est le numéro de mot JBUS de l'automate, égal à l'indice du
%MW du programme (station JBUS, adresses Modicon désactivées). OGIAS n'applique cette correspondance que
lorsqu'elle est déclarée dans les paramètres de communication de l'ouvrage ; sinon le point reste « non résolu ».
"""
from dataclasses import dataclass, field

ENTETE = ["VAR_MNEMO", "VAR_ADRESS", "VAR_FORMAT", "VAR_TEXT", "VAR_F4", "VAR_F5", "VAR_HISTO", "VAR_ECHANT",
          "VAR_NF", "VAR_TC", "VAR_LIB0", "VAR_LIB1", "VAR_ASTR", "VAR_RANG", "VAR_UNIT", "VAR_MINBRUT",
          "VAR_MAXBRUT", "VAR_MINSCALE", "VAR_MAXSCALE"] + [f"VAR_RES{i}" for i in range(17)] + ["VAR_ZONE", "VAR_SYNO"]
ENCODAGE = "cp1252"
# Codes de format relevés ; la correspondance avec un type OGIAS reste à confirmer pour 102 / 105.
FORMATS_OBSERVES = {"0": "bit (ou mot de télécommande)", "2": "mot 16 bits", "102": "deux mots (à confirmer)",
                    "105": "deux mots (à confirmer)"}


class FormatTopkapiInvalide(ValueError):
    pass


@dataclass
class PointTopkapi:
    mnemo: str
    adresse: str
    format: str
    texte: str
    autres: list = field(default_factory=lambda: [""] * (len(ENTETE) - 4))

    @property
    def mot_bit(self):
        """(mot, bit ou None) ; lève FormatTopkapiInvalide si l'adresse est illisible."""
        a = self.adresse.strip()
        try:
            if "$" in a:
                mot, bit = a.split("$")
                b = int(bit, 16)
                if not 0 <= b <= 15 or len(bit) != 1:
                    raise ValueError
                return int(mot), b
            return int(a), None
        except ValueError as exc:
            raise FormatTopkapiInvalide(f"{self.mnemo} : adresse « {self.adresse} » illisible (mot ou mot$bit).") from exc


def lire_octets(octets, nom="fichier"):
    texte = octets.decode(ENCODAGE)
    if "\r\n" not in texte:
        raise FormatTopkapiInvalide(f"{nom} : fins de ligne CRLF attendues.")
    lignes = texte.split("\r\n")
    if lignes[0] != "Version\t1" or len(lignes) < 2 or lignes[1].split("\t") != ENTETE:
        raise FormatTopkapiInvalide(f"{nom} : en-tête « Version 1 » et 38 colonnes VAR_MNEMO … VAR_SYNO attendus.")
    points = []
    for n, ligne in enumerate(lignes[2:], 3):
        if ligne == "":
            continue
        c = ligne.split("\t")
        if len(c) != len(ENTETE):
            raise FormatTopkapiInvalide(f"{nom}, ligne {n} : {len(c)} champs au lieu de {len(ENTETE)}.")
        p = PointTopkapi(c[0], c[1], c[2], c[3], c[4:])
        p.mot_bit
        points.append(p)
    return points


def lire(chemin):
    with open(chemin, "rb") as f:
        return lire_octets(f.read(), chemin)


def ecrire_octets(points):
    lignes = ["Version\t1", "\t".join(ENTETE)]
    for p in points:
        for champ in (p.mnemo, p.adresse, p.format, p.texte):
            if "\t" in champ or "\r" in champ or "\n" in champ:
                raise FormatTopkapiInvalide(f"{p.mnemo} : tabulation ou retour à la ligne interdit.")
        lignes.append("\t".join([p.mnemo, p.adresse, p.format, p.texte] + list(p.autres)))
    try:
        return ("\r\n".join(lignes) + "\r\n").encode(ENCODAGE)
    except UnicodeEncodeError as exc:
        raise FormatTopkapiInvalide(f"Caractère non représentable en Windows-1252 : {exc.object[exc.start:exc.end]!r}.") from exc


def controler(points):
    """Doublons de mnémonique, chevauchements d'adresses (bit dans un mot déjà pris en entier, mots de 32 bits)."""
    erreurs: list[str] = []
    mnemos: dict[str, PointTopkapi] = {}
    bits: dict[tuple[int, int], str] = {}
    mots: dict[int, str] = {}
    for p in points:
        if p.mnemo in mnemos:
            erreurs.append(f"{p.mnemo} : mnémonique en double.")
        mnemos[p.mnemo] = p
        mot, bit = p.mot_bit
        largeur = 2 if p.format in ("102", "105") else 1
        if bit is not None:
            if (mot, bit) in bits:
                erreurs.append(f"{p.mnemo} : {p.adresse} déjà utilisé par {bits[(mot, bit)]}.")
            bits[(mot, bit)] = p.mnemo
            if mot in mots:
                erreurs.append(f"{p.mnemo} : bit d'un mot déjà utilisé en entier par {mots[mot]}.")
        else:
            for m in range(mot, mot + largeur):
                if m in mots:
                    erreurs.append(f"{p.mnemo} : mot {m} déjà utilisé par {mots[m]}.")
                if any(b[0] == m for b in bits):
                    erreurs.append(f"{p.mnemo} : mot {m} déjà découpé en bits.")
                mots[m] = p.mnemo
    return erreurs
