@echo off
setlocal
cd /d "%~dp0"
echo SOREP - Analyse documentaire PDF PL7 (lecture seule)
if not "%~1"=="" (
 set "SOURCE_PDF=%~1"
) else (
 echo Indiquer le chemin du dossier PDF texte :
 set /p "SOURCE_PDF=Fichier PDF : "
)
if "%SOURCE_PDF%"=="" goto :fin
py analyser_dossier_pl7.py "%SOURCE_PDF%" --sortie "Rapport_PDF_PL7"
echo.
echo Le dossier Rapport_PDF_PL7 contient maintenant les occurrences, symboles,
echo affectations, pages justificatives et revue_variables_pdf.csv.
echo Toutes les correspondances restent a verifier manuellement.
:fin
pause
