@echo off
cd /d "%~dp0"
py verifier_xsy_github.py
if errorlevel 1 (
  echo.
  echo ERREUR : consulter le message ci-dessus.
) else (
  echo.
  echo Diagnostic ecrit dans validation\ddt\resultats.
)
pause
