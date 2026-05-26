@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM Este .bat esta dentro de la carpeta GIT.
REM La raiz del proyecto es la carpeta superior, donde esta EASY DEPLOY.py.
cd /d "%~dp0.."

title EASY DEPLOY - Git restaurar backup previo

echo.
echo ===============================================
echo   GIT - RESTAURAR BACKUP PREVIO
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
    pause
    exit /b 1
)

echo Ramas de backup disponibles:
echo.
git branch --list "backup-before-restore-*"
echo.

set /p BRANCH=Escribe el nombre exacto de la rama backup a restaurar: 
if "%BRANCH%"=="" (
    echo Cancelado.
    pause
    exit /b 0
)

git rev-parse --verify "%BRANCH%" >nul 2>nul
if errorlevel 1 (
    echo ERROR: No existe esa rama: %BRANCH%
    pause
    exit /b 1
)

echo.
echo Vas a volver al estado guardado en:
git log -1 --oneline "%BRANCH%"
echo.
set /p CONF=Para confirmar escribe RESTAURAR: 
if /I not "%CONF%"=="RESTAURAR" (
    echo Cancelado.
    pause
    exit /b 0
)

git reset --hard "%BRANCH%"
if errorlevel 1 (
    echo ERROR: No se pudo restaurar la rama backup.
    pause
    exit /b 1
)

echo.
echo Restaurado. Estado actual:
git status --short
echo.
pause
