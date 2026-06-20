@echo off
REM ============================================================
REM  Upscale 4K avec Real-ESRGAN (gratuit, local)
REM  A placer A COTE de realesrgan-ncnn-vulkan.exe
REM  Mettez vos images dans le dossier "entree", puis double-cliquez.
REM  Le resultat 4096x4096 apparait dans "sortie".
REM ============================================================
setlocal
cd /d "%~dp0"

if not exist "realesrgan-ncnn-vulkan.exe" (
  echo [!] Placez ce fichier a cote de realesrgan-ncnn-vulkan.exe
  echo     Telechargez-le sur https://github.com/xinntao/Real-ESRGAN/releases
  pause & exit /b 1
)
if not exist "entree" mkdir entree
if not exist "sortie" mkdir sortie

echo Agrandissement x4 (1024 -> 4096) en cours...
realesrgan-ncnn-vulkan.exe -i entree -o sortie -n realesrgan-x4plus -s 4 -f png

echo.
echo Termine ! Vos images 4K sont dans le dossier "sortie".
pause
