@echo off
cd /d "%~dp0"
echo Test du dossier public HABILIS. Aucune donnee locale transmise.
echo Necessite une connexion internet et le module PyMuPDF.
py recuperer_et_analyser_habilis.py
pause
