@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM Este .bat esta dentro de la carpeta GIT.
REM La raiz del proyecto es la carpeta superior, donde esta EASY DEPLOY.py.
cd /d "%~dp0.."

title EASY DEPLOY - Git DESPUES de probar

echo.
echo ===============================================
echo   GIT - CHECKPOINT DESPUES DE PROBAR
echo ===============================================
echo Carpeta del proyecto:
echo %CD%
echo.

where git >nul 2>nul
if errorlevel 1 (
    echo ERROR: Git no esta instalado o no esta en el PATH.
    echo Instalalo con:
    echo winget install --id Git.Git -e --source winget
    echo.
    pause
    exit /b 1
)

if not exist ".git" (
    echo ERROR: Esta carpeta todavia no tiene repositorio Git.
    echo Ejecuta primero GIT\01_GIT_ANTES_DE_CODEX.bat.
    echo.
    pause
    exit /b 1
)

echo IMPORTANTE:
echo Ejecuta este checkpoint DESPUES de probar que EASY DEPLOY abre y funciona.
echo.
set /p OK=Has probado la app y funciona bien? Escribe S para continuar: 
if /I not "%OK%"=="S" (
    echo Cancelado. No se ha creado checkpoint DESPUES.
    pause
    exit /b 0
)

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set TS=%%i

echo.
echo Estado actual:
git status --short
echo.

set DEFAULT_MSG=Checkpoint AFTER verified working - %TS%
set /p MSG=Mensaje del checkpoint DESPUES [Enter = "%DEFAULT_MSG%"]: 
if "%MSG%"=="" set MSG=%DEFAULT_MSG%

echo.
echo Anadiendo cambios...
git add .
if errorlevel 1 (
    echo ERROR: Fallo git add.
    pause
    exit /b 1
)

echo.
echo Creando checkpoint...
git commit -m "%MSG%"
if errorlevel 1 (
    echo.
    echo No se ha creado commit. Puede que no hubiera cambios nuevos que guardar.
    echo Esto no es grave si ya estaba todo guardado.
)

echo.
echo Ultimos checkpoints:
git log --oneline -8
echo.
echo Checkpoint DESPUES terminado.
pause
