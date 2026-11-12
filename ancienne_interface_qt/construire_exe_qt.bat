@echo off
rem Construit la nouvelle interface (PySide6) dans dist\GenerateurVariablesQt\
rem A lancer depuis le dossier du projet, une fois installes :
rem     py -m pip install -r requirements-qt.txt pyinstaller
rem L'exe obtenu embarque Qt : rien a installer sur le PC qui l'utilise.

rem Refuser le packaging si les tests Qt sont simplement "ignores".
py verifier_sorep.py --qt-obligatoire
if errorlevel 1 goto echec
py -m PyInstaller --noconfirm --windowed --name GenerateurVariablesQt ^
    --add-data "genvar\data;genvar\data" lancer_qt.pyw
echo.
echo Construit : dist\GenerateurVariablesQt\GenerateurVariablesQt.exe
echo Copier le dossier dist\GenerateurVariablesQt en entier.
pause
exit /b 0
:echec
echo Les tests ont echoue : exe non construit.
pause
exit /b 1
