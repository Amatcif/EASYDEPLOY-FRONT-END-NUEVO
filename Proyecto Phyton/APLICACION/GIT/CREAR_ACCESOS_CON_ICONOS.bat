@echo off
setlocal
chcp 65001 >nul
title Crear accesos Git con iconos

cd /d "%~dp0"

echo.
echo ===============================================
echo   Crear accesos directos Git con iconos
echo ===============================================
echo.
echo Esta carpeta GIT debe estar dentro de la raiz del proyecto.
echo La raiz del proyecto debe ser la carpeta superior, donde esta EASY DEPLOY.py.
echo.
echo Se creara una subcarpeta:
echo Accesos con iconos
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0crear_accesos_git.ps1"

echo.
pause
