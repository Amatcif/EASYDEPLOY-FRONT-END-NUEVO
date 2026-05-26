@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
title Crear instalador Windows Easy Deploy - Electron + Backend Python

set "PROJECT_DIR=%~dp0"
set "APP_DIR=%PROJECT_DIR%APLICACION"
for %%I in ("%PROJECT_DIR%..\easy-deploy-ForntEND") do set "FRONTEND_DIR=%%~fI"

echo ============================================================
echo   Crear instalador Windows EASY DEPLOY
echo ============================================================
echo.
echo Backend Python:
echo %APP_DIR%
echo.
echo Front-end Electron:
echo %FRONTEND_DIR%
echo.

if not exist "%APP_DIR%\easy_deploy_app\constants.py" (
    echo ERROR: No se encontro easy_deploy_app\constants.py.
    if /i "%EASYDEPLOY_BUILD_PAUSE%"=="1" pause
    exit /b 1
)

if not exist "%FRONTEND_DIR%\package.json" (
    echo ERROR: No se encontro package.json en el front-end.
    if /i "%EASYDEPLOY_BUILD_PAUSE%"=="1" pause
    exit /b 1
)

where py >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python launcher py no esta disponible.
    if /i "%EASYDEPLOY_BUILD_PAUSE%"=="1" pause
    exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
    echo ERROR: Node.js no esta instalado o no esta en el PATH.
    if /i "%EASYDEPLOY_BUILD_PAUSE%"=="1" pause
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo ERROR: npm no esta instalado o no esta en el PATH.
    if /i "%EASYDEPLOY_BUILD_PAUSE%"=="1" pause
    exit /b 1
)

set "APP_VERSION="
for /f "tokens=2 delims== " %%V in ('findstr /B /C:"APP_VERSION" "%APP_DIR%\easy_deploy_app\constants.py"') do set "APP_VERSION=%%~V"
if errorlevel 1 (
    echo ERROR: No se pudo leer APP_VERSION desde constants.py.
    if /i "%EASYDEPLOY_BUILD_PAUSE%"=="1" pause
    exit /b 1
)
if "%APP_VERSION%"=="" (
    echo ERROR: APP_VERSION esta vacio.
    if /i "%EASYDEPLOY_BUILD_PAUSE%"=="1" pause
    exit /b 1
)
set "APP_VERSION=%APP_VERSION:"=%"
echo Version detectada: %APP_VERSION%
echo.

echo [1/7] Regenerando licencia/hash de compilacion del backend...
pushd "%APP_DIR%" || exit /b 1
py -3 tools\stamp_license_build.py
if errorlevel 1 (
    popd
    echo ERROR: No se pudo regenerar license_build.py.
    if /i "%EASYDEPLOY_BUILD_PAUSE%"=="1" pause
    exit /b 1
)

echo [2/7] Generando clave unica SOLO en escritorio del desarrollador...
py -3 tools\stamp_activation_key.py --version "%APP_VERSION%"
if errorlevel 1 (
    popd
    echo ERROR: No se pudo generar la clave de escritorio.
    if /i "%EASYDEPLOY_BUILD_PAUSE%"=="1" pause
    exit /b 1
)

echo [3/7] Compilando backend Python JSONL con PyInstaller...
if exist "%FRONTEND_DIR%\backend_dist" rmdir /s /q "%FRONTEND_DIR%\backend_dist"
if exist "%FRONTEND_DIR%\backend_build" rmdir /s /q "%FRONTEND_DIR%\backend_build"
py -3 -m PyInstaller --clean --noconfirm --onefile --console --name easydeploy_backend --distpath "%FRONTEND_DIR%\backend_dist" --workpath "%FRONTEND_DIR%\backend_build" --specpath "%FRONTEND_DIR%\backend_build" "%APP_DIR%\easy_deploy_backend_launcher.py"
if errorlevel 1 (
    popd
    echo ERROR: Fallo PyInstaller compilando easydeploy_backend.exe.
    if /i "%EASYDEPLOY_BUILD_PAUSE%"=="1" pause
    exit /b 1
)
popd

if not exist "%FRONTEND_DIR%\backend_dist\easydeploy_backend.exe" (
    echo ERROR: No se genero backend_dist\easydeploy_backend.exe.
    if /i "%EASYDEPLOY_BUILD_PAUSE%"=="1" pause
    exit /b 1
)

echo [4/7] Instalando dependencias Electron/React...
pushd "%FRONTEND_DIR%" || exit /b 1
call npm install
if errorlevel 1 (
    popd
    echo ERROR: Fallo npm install.
    if /i "%EASYDEPLOY_BUILD_PAUSE%"=="1" pause
    exit /b 1
)

echo [5/7] Compilando front-end Vite...
if exist "%FRONTEND_DIR%\dist" rmdir /s /q "%FRONTEND_DIR%\dist"
if exist "%FRONTEND_DIR%\dist_desktop" rmdir /s /q "%FRONTEND_DIR%\dist_desktop"
call npm run build
if errorlevel 1 (
    popd
    echo ERROR: Fallo npm run build.
    if /i "%EASYDEPLOY_BUILD_PAUSE%"=="1" pause
    exit /b 1
)

echo [6/7] Creando instalador NSIS con electron-builder...
call npm run package:windows
if errorlevel 1 (
    popd
    echo ERROR: Fallo electron-builder creando el instalador.
    if /i "%EASYDEPLOY_BUILD_PAUSE%"=="1" pause
    exit /b 1
)

echo [7/7] Verificando salida...
if not exist "%FRONTEND_DIR%\dist_desktop" (
    popd
    echo ERROR: No se creo dist_desktop.
    if /i "%EASYDEPLOY_BUILD_PAUSE%"=="1" pause
    exit /b 1
)

dir "%FRONTEND_DIR%\dist_desktop\*.exe" /b >nul 2>nul
if errorlevel 1 (
    popd
    echo ERROR: No se encontro instalador .exe en dist_desktop.
    if /i "%EASYDEPLOY_BUILD_PAUSE%"=="1" pause
    exit /b 1
)

echo.
echo ============================================================
echo   INSTALADOR EASY DEPLOY CREADO
echo ============================================================
echo Salida:
echo %FRONTEND_DIR%\dist_desktop
echo.
echo Instaladores:
dir "%FRONTEND_DIR%\dist_desktop\*.exe" /b
echo.
echo Clave de activacion guardada SOLO en:
echo %USERPROFILE%\Desktop\EASYDEPLOY_CLAVE_ACTIVACION_v%APP_VERSION%.txt
echo.
echo Confirmacion de seguridad:
echo - El instalador incluye backend_dist\easydeploy_backend.exe.
echo - No copia node_modules como carpeta de trabajo del proyecto.
echo - Electron-builder solo empaqueta las dependencias internas necesarias.
echo - No incluye claves de activacion.
echo - No copia fuentes Python como extraResources.
echo.
if /i "%EASYDEPLOY_BUILD_OPEN%"=="1" start "" "%FRONTEND_DIR%\dist_desktop"
if /i "%EASYDEPLOY_BUILD_PAUSE%"=="1" pause
popd
exit /b 0
