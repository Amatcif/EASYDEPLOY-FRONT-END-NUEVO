@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM Este .bat esta dentro de la carpeta GIT.
REM La raiz del proyecto es la carpeta superior, donde esta EASY DEPLOY.py.
cd /d "%~dp0.."

title EASY DEPLOY - Git ver checkpoints

echo.
echo ===============================================
echo   GIT - VER CHECKPOINTS DISPONIBLES
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

echo Checkpoints recientes:
echo.
git log --oneline --decorate -20
echo.
echo Copia el codigo corto de la izquierda, por ejemplo: a1b2c3d
echo Ese codigo sirve para volver a ese checkpoint.
echo.
pause
