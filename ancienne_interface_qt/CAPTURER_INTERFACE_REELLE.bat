@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Captures reelles de SOREP / PySide6 (aucun dessin genere par IA)
echo.
py capturer_interface_reelle.py
if errorlevel 1 echo ERREUR : verifiez que PySide6 est installe (requirements-qt.txt).
echo.
echo Les images sont dans Captures_interface_reelles
pause
