"""Les classeurs incomplets provoquent une erreur explicite, jamais un import partiel."""
import zipfile

import pytest

from genvar import catalogue_excel, tableur


def classeur(tmp_path, *, feuilles=True, cible="worksheets/sheet1.xml", contenu=""):
    fichier = tmp_path / "incomplet.xlsx"
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    relation = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    with zipfile.ZipFile(fichier, "w") as archive:
        sheets = '<sheets><sheet name="Essai" r:id="r1"/></sheets>' if feuilles else ""
        archive.writestr("xl/workbook.xml", f'<workbook xmlns="{main}" xmlns:r="{relation}">{sheets}</workbook>')
        target = f' Target="{cible}"' if cible is not None else ""
        archive.writestr("xl/_rels/workbook.xml.rels",
                         '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                         f'<Relationship Id="r1"{target}/></Relationships>')
        archive.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{main}"><sheetData>{contenu}</sheetData></worksheet>')
        archive.writestr("xl/sharedStrings.xml", f'<sst xmlns="{main}"><si><t>texte</t></si></sst>')
    return fichier


@pytest.mark.parametrize("lecteur", [catalogue_excel.lire_xlsx, tableur.lire_classeur])
def test_cible_absente_refusee(tmp_path, lecteur):
    with pytest.raises(ValueError, match="cible valide"):
        lecteur(classeur(tmp_path, cible=None))


def test_liste_feuilles_absente_refusee(tmp_path):
    with pytest.raises(ValueError, match="liste de feuilles"):
        catalogue_excel.lire_xlsx(classeur(tmp_path, feuilles=False))


@pytest.mark.parametrize("numero", ["", 'r="0"', 'r="abc"'])
def test_numero_ligne_invalide_refuse(tmp_path, numero):
    with pytest.raises(ValueError, match="Numéro de ligne"):
        catalogue_excel.lire_xlsx(classeur(tmp_path, contenu=f'<row {numero}><c r="A1"/></row>'))


@pytest.mark.parametrize("valeur", ["", "-1", "5", "texte"])
def test_texte_partage_invalide_refuse(tmp_path, valeur):
    with pytest.raises(ValueError, match="texte partagé"):
        tableur.lire_classeur(classeur(tmp_path, contenu=f'<row><c r="A1" t="s"><v>{valeur}</v></c></row>'))


def test_reference_cellule_invalide_refusee(tmp_path):
    with pytest.raises(ValueError, match="Référence de cellule"):
        tableur.lire_classeur(classeur(tmp_path, contenu='<row><c r="1"><v>3</v></c></row>'))
