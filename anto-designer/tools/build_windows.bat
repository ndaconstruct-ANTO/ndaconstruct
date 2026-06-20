@echo off
REM ============================================================
REM  ANTO DESIGNER - Construction de AntoDesigner.exe (Windows)
REM  Double-cliquez ce fichier, ou lancez-le depuis le dossier
REM  "anto-designer".
REM ============================================================
setlocal
cd /d "%~dp0\.."

echo [1/4] Verification de Python...
python --version || (echo Python introuvable. Installez Python 3.10+ ^(Add to PATH^). & pause & exit /b 1)

echo [2/4] Installation des dependances...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller || (echo Echec installation. & pause & exit /b 1)

echo [3/4] (Re)generation de l'icone...
python tools\make_icon.py

echo [4/4] Construction de l'executable...
pyinstaller --noconfirm AntoDesigner.spec || (echo Echec PyInstaller. & pause & exit /b 1)

echo.
echo ============================================================
echo  TERMINE !  L'application est dans :  dist\AntoDesigner\
echo  Lancez :   dist\AntoDesigner\AntoDesigner.exe
echo  (Pour creer l'installateur, voir docs\INSTALL_WINDOWS.md)
echo ============================================================
pause
