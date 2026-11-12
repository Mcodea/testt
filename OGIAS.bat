@echo off
rem OGIAS - Ingenierie, Automatisme et Supervision
cd /d "%~dp0"
py -m sorep_web
if errorlevel 1 python -m sorep_web
pause
