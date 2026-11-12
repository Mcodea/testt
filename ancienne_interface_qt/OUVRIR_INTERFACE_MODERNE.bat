@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo SOREP - Interface moderne PySide6
echo.
py lancer_qt.py
if errorlevel 1 (
  echo.
  echo Le demarrage a echoue. Consultez le message ci-dessus.
  echo Si PySide6 manque : py -m pip install -r requirements-qt.txt
  pause
)
