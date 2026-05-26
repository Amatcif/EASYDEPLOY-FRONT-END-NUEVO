@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM Este .bat esta dentro de la carpeta GIT.
REM La raiz del proyecto es la carpeta superior, donde esta EASY DEPLOY.py.
cd /d "%~dp0.."

title EASY DEPLOY - Git volver a checkpoint

echo.
echo ===============================================
echo   GIT - VOLVER A UN CHECKPOINT
echo ===============================================
echo.

where git >nul 2>nul
if errorlevel 1 (
    echo ERROR: Git no esta instalado o no esta en el PATH.
    pause
    exit /b 1
)

if not exist ".git" (
    echo ERROR: Esta carpeta no tiene repositorio Git.
    echo Ejecuta primero GIT\01_GIT_ANTES_DE_CODEX.bat.
    pause
    exit /b 1
)

echo Estado actual:
git status --short
echo.

echo Checkpoints recientes:
echo.
git log --oneline --decorate -20
echo.

echo IMPORTANTE:
echo Este proceso cambiara los archivos del proyecto al checkpoint elegido.
echo Antes de volver atras se creara una rama de seguridad con el estado actual.
echo Si hay cambios sin guardar, se guardaran en un stash automatico.
echo.
set /p HASH=Escribe el codigo del checkpoint al que quieres volver: 
if "%HASH%"=="" (
    echo Cancelado.
    pause
    exit /b 0
)

git rev-parse --verify "%HASH%" >nul 2>nul
if errorlevel 1 (
    echo ERROR: No existe ese codigo de checkpoint: %HASH%
    pause
    exit /b 1
)

echo.
echo Vas a volver a:
git log -1 --oneline "%HASH%"
echo.
set /p CONF=Para confirmar escribe VOLVER: 
if /I not "%CONF%"=="VOLVER" (
    echo Cancelado. No se ha cambiado nada.
    pause
    exit /b 0
)

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set TS=%%i
set BACKUP_BRANCH=backup-before-restore-%TS%

echo.
echo Creando rama de seguridad del estado actual:
echo %BACKUP_BRANCH%
git branch "%BACKUP_BRANCH%"

for /f %%i in ('git status --porcelain') do set DIRTY=1
if defined DIRTY (
    echo.
    echo Hay cambios sin guardar. Guardando stash automatico...
    git stash push -u -m "auto-stash-before-restore-%TS%"
)

echo.
echo Volviendo al checkpoint elegido...
git reset --hard "%HASH%"
if errorlevel 1 (
    echo ERROR: No se pudo volver al checkpoint.
    pause
    exit /b 1
)

echo.
echo Resultado:
git status --short
echo.
echo Ahora los archivos rastreados por Git estan como en:
git log -1 --oneline
echo.
echo Si te arrepientes, usa:
echo GIT\05_GIT_RESTAURAR_BACKUP_PREVIO.bat
echo y elige esta rama:
echo %BACKUP_BRANCH%
echo.
pause
