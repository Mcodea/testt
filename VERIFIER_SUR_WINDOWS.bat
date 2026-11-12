@echo off
cd /d "%~dp0"
echo ===============================================
echo  OGIAS - Verification avant utilisation
echo ===============================================
py verifier_sorep.py
set RESULTAT=%ERRORLEVEL%
echo.
if not "%RESULTAT%"=="0" (
  echo [ATTENTION] La recette n'est PAS terminee. Code %RESULTAT%.
  echo Lire les erreurs ci-dessus et installer les dependances si necessaire.
) else (
  echo [OK] Tests automatiques termines.
  echo RESTE A FAIRE : recette manuelle et validations constructeur.
)
pause
exit /b %RESULTAT%
