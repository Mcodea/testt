@echo off
rem Cree un raccourci OGIAS (icone OGIAS) sur le Bureau et dans le menu Demarrer.
rem Ensuite : clic droit sur le raccourci > Epingler a la barre des taches.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=(Get-Location).Path; $w=New-Object -ComObject WScript.Shell; foreach($c in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))){ $s=$w.CreateShortcut((Join-Path $c 'OGIAS.lnk')); $s.TargetPath=$env:ComSpec; $q=[char]34; $s.Arguments='/c '+$q+(Join-Path $d 'OGIAS.bat')+$q; $s.WorkingDirectory=$d; $s.IconLocation=(Join-Path $d 'sorep_web\static\assets\ogias-application.ico')+',0'; $s.WindowStyle=7; $s.Description='OGIAS - Outil de Gestion des Informations d Automatisme et de Supervision'; $s.Save() }"
echo Raccourci OGIAS cree sur le Bureau et dans le menu Demarrer.
pause
