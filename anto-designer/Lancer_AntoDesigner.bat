@echo off
REM ============================================================
REM   LANCER ANTO DESIGNER  (double-cliquez ce fichier)
REM   La 1re fois : installe les composants (patientez).
REM   Ensuite : ouvre directement l'application.
REM ============================================================
cd /d "%~dp0"
title ANTO DESIGNER

echo.
echo   Demarrage de ANTO DESIGNER...
echo.

python --version >nul 2>&1
if errorlevel 1 (
  echo   [!] Python n'est pas installe.
  echo       Installez Python 3.10+ depuis https://www.python.org/downloads/
  echo       IMPORTANT : cochez "Add Python to PATH" pendant l'installation.
  echo.
  pause
  exit /b 1
)

echo   Verification des composants ^(1re fois : cela peut prendre 1-2 minutes^)...
python -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
  echo   [!] Echec de l'installation des composants.
  pause
  exit /b 1
)

echo   Ouverture de l'application...
python -m anto_designer
if errorlevel 1 (
  echo.
  echo   [!] L'application n'a pas pu demarrer. Voir le message ci-dessus.
  pause
)
