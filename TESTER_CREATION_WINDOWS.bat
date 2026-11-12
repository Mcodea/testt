@echo off
cd /d "%~dp0"
py -m unittest discover -s tests -p "test_confirmation_fiche_ouvrage.py" -v
if errorlevel 1 (
    echo Echec des tests de creation.
    pause
    exit /b 1
)
py -m unittest discover -s tests -p "test_interface_web.py" -v
pause
