@echo off
cd /d "%~dp0"
py lancer_qt.py
if errorlevel 1 (
  echo.
  echo Echec du demarrage. Verifier Python et PySide6.
  echo Installer : py -m pip install -r requirements-qt.txt
  pause
)
