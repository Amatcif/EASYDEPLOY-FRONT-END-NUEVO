@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM Este .bat esta dentro de la carpeta GIT.
REM La raiz del proyecto es la carpeta superior, donde esta EASY DEPLOY.py.
cd /d "%~dp0.."

title EASY DEPLOY - Git ANTES de Codex

echo.
echo ===============================================
echo   GIT - CHECKPOINT ANTES DE CODEX
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
    echo No existe repositorio Git en esta carpeta.
    echo Creando repositorio con: git init
    git init
    if errorlevel 1 (
        echo ERROR: No se pudo inicializar Git.
        pause
        exit /b 1
    )
)

if not exist ".gitignore" (
    echo Creando .gitignore basico...
    > .gitignore echo # Python
    >> .gitignore echo __pycache__/
    >> .gitignore echo *.pyc
    >> .gitignore echo *.pyo
    >> .gitignore echo *.pyd
    >> .gitignore echo .venv/
    >> .gitignore echo venv/
    >> .gitignore echo.
    >> .gitignore echo # Build outputs
    >> .gitignore echo build/
    >> .gitignore echo dist/
    >> .gitignore echo *.log
    >> .gitignore echo *.tmp
    >> .gitignore echo.
    >> .gitignore echo # OS/editor
    >> .gitignore echo Thumbs.db
    >> .gitignore echo .DS_Store
    >> .gitignore echo.
    >> .gitignore echo # Secrets/certificates
    >> .gitignore echo .env
    >> .gitignore echo *.key
    >> .gitignore echo *.pem
    >> .gitignore echo *.pfx
)

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set TS=%%i

echo Estado actual:
git status --short
echo.

set DEFAULT_MSG=Checkpoint BEFORE Codex changes - %TS%
set /p MSG=Mensaje del checkpoint ANTES [Enter = "%DEFAULT_MSG%"]: 
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
    echo Esto no es grave si ya tenias todo guardado.
)

echo.
echo Ultimos checkpoints:
git log --oneline -5
echo.
echo Checkpoint ANTES terminado.
pause
