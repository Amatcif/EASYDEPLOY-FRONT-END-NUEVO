@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Build instalador Easy Deploy

REM ============================================================
REM  Build instalador NSIS de Easy Deploy
REM  Requiere: NSIS 3.x con makensis.exe
REM  Entrada:  dist\EASY DEPLOY.exe
REM  Salida:   releases\EasyDeploy_Setup_vX.Y.Z.exe
REM
REM  Uso recomendado desde la raiz del proyecto:
REM      cmd /k "Crear .EXE\build_instalador_easydeploy.bat"
REM
REM  Tambien funciona con doble clic, pero dejara la ventana abierta.
REM ============================================================

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Detectar raiz del proyecto de forma tolerante:
REM 1) Si el .bat esta en Crear .EXE, la raiz es la carpeta padre.
REM 2) Si el .bat esta en la raiz, la raiz es su propia carpeta.
REM 3) Si se ejecuta desde la raiz, usar %CD%.
set "APP_ROOT="

if exist "%SCRIPT_DIR%\easy_deploy_app\constants.py" (
    set "APP_ROOT=%SCRIPT_DIR%"
)

if not defined APP_ROOT if exist "%SCRIPT_DIR%\..\easy_deploy_app\constants.py" (
    for %%I in ("%SCRIPT_DIR%\..") do set "APP_ROOT=%%~fI"
)

if not defined APP_ROOT if exist "%CD%\easy_deploy_app\constants.py" (
    set "APP_ROOT=%CD%"
)

if not defined APP_ROOT (
    echo.
    echo [ERROR] No se ha podido detectar la raiz del proyecto.
    echo.
    echo Ejecuta este archivo desde la raiz del proyecto con:
    echo   cmd /k "Crear .EXE\build_instalador_easydeploy.bat"
    echo.
    echo O coloca este archivo dentro de:
    echo   Crear .EXE\
    echo.
    pause
    exit /b 1
)

set "CONSTANTS_FILE=%APP_ROOT%\easy_deploy_app\constants.py"
set "DIST_EXE=%APP_ROOT%\dist\EASY DEPLOY.exe"
set "RELEASES_DIR=%APP_ROOT%\releases"

REM Localizar EasyDeployInstaller.nsi en ubicaciones habituales.
set "NSI_FILE="
if exist "%SCRIPT_DIR%\EasyDeployInstaller.nsi" set "NSI_FILE=%SCRIPT_DIR%\EasyDeployInstaller.nsi"
if not defined NSI_FILE if exist "%SCRIPT_DIR%\Crear .EXE\EasyDeployInstaller.nsi" set "NSI_FILE=%SCRIPT_DIR%\Crear .EXE\EasyDeployInstaller.nsi"
if not defined NSI_FILE if exist "%APP_ROOT%\Crear .EXE\EasyDeployInstaller.nsi" set "NSI_FILE=%APP_ROOT%\Crear .EXE\EasyDeployInstaller.nsi"

echo.
echo ============================================================
echo  Easy Deploy - Generador de instalador
echo ============================================================
echo.
echo [INFO] Raiz proyecto: "%APP_ROOT%"
echo [INFO] constants.py:  "%CONSTANTS_FILE%"
echo [INFO] EXE origen:   "%DIST_EXE%"
echo [INFO] NSI:          "%NSI_FILE%"
echo.

if not exist "%CONSTANTS_FILE%" (
    echo [ERROR] No se encuentra constants.py:
    echo         "%CONSTANTS_FILE%"
    echo.
    pause
    exit /b 1
)

if not exist "%DIST_EXE%" (
    echo [ERROR] No existe el EXE compilado:
    echo         "%DIST_EXE%"
    echo.
    echo Primero genera Easy Deploy con PyInstaller para crear:
    echo   dist\EASY DEPLOY.exe
    echo.
    pause
    exit /b 1
)

if not defined NSI_FILE (
    echo [ERROR] No se encuentra EasyDeployInstaller.nsi.
    echo.
    echo Debe estar en:
    echo   Crear .EXE\EasyDeployInstaller.nsi
    echo.
    pause
    exit /b 1
)

set "APP_VERSION="
for /f "tokens=2 delims==" %%A in ('findstr /R /C:"^APP_VERSION *= *" "%CONSTANTS_FILE%"') do (
    set "APP_VERSION=%%~A"
)
set "APP_VERSION=%APP_VERSION:"=%"
set "APP_VERSION=%APP_VERSION: =%"

if not defined APP_VERSION (
    echo [ERROR] No se pudo leer APP_VERSION desde constants.py.
    echo.
    pause
    exit /b 1
)

set "MAKENSIS="
if exist "%ProgramFiles(x86)%\NSIS\makensis.exe" set "MAKENSIS=%ProgramFiles(x86)%\NSIS\makensis.exe"
if not defined MAKENSIS if exist "%ProgramFiles%\NSIS\makensis.exe" set "MAKENSIS=%ProgramFiles%\NSIS\makensis.exe"
if not defined MAKENSIS (
    for /f "delims=" %%P in ('where makensis.exe 2^>nul') do (
        if not defined MAKENSIS set "MAKENSIS=%%P"
    )
)

if not defined MAKENSIS (
    echo [ERROR] No se encuentra makensis.exe.
    echo.
    echo Falta instalar NSIS 3.x.
    echo Descarga/instala NSIS y vuelve a ejecutar este .bat.
    echo.
    echo Rutas habituales:
    echo   C:\Program Files ^(x86^)\NSIS\makensis.exe
    echo   C:\Program Files\NSIS\makensis.exe
    echo.
    echo No se ha generado el instalador.
    echo.
    pause
    exit /b 2
)

if not exist "%RELEASES_DIR%" mkdir "%RELEASES_DIR%"

set "OUT_EXE=%RELEASES_DIR%\EasyDeploy_Setup_v%APP_VERSION%.exe"
if exist "%OUT_EXE%" del /f /q "%OUT_EXE%" >nul 2>&1

echo [INFO] Version:      %APP_VERSION%
echo [INFO] NSIS:         "%MAKENSIS%"
echo [INFO] Salida:       "%OUT_EXE%"
echo.

"%MAKENSIS%" /V2 ^
    "/DAPP_VERSION=%APP_VERSION%" ^
    "/DSOURCE_EXE=%DIST_EXE%" ^
    "/DOUT_FILE=%OUT_EXE%" ^
    "%NSI_FILE%"

set "BUILD_ERROR=%ERRORLEVEL%"
if not "%BUILD_ERROR%"=="0" (
    echo.
    echo [ERROR] NSIS devolvio codigo %BUILD_ERROR%.
    echo.
    pause
    exit /b %BUILD_ERROR%
)

if not exist "%OUT_EXE%" (
    echo.
    echo [ERROR] NSIS termino sin error, pero no aparece el instalador esperado:
    echo         "%OUT_EXE%"
    echo.
    pause
    exit /b 3
)

echo.
echo [OK] Instalador generado correctamente:
echo      "%OUT_EXE%"
echo.
echo Sube ESTE archivo a Dropbox, no dist\EASY DEPLOY.exe.
echo.
pause
exit /b 0
