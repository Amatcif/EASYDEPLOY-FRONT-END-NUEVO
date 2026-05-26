@echo off
setlocal

set "APP=%~dp0.."
for %%I in ("%APP%") do set "APP=%%~fI"
pushd "%APP%"

set "ED_BUILD_ADD_DATA_TOKEN=--add-data"
set "ED_BUILD_PY_TOKEN=.py"
findstr /I /C:"%ED_BUILD_ADD_DATA_TOKEN%" "%~f0" | findstr /I "%ED_BUILD_PY_TOKEN%" >nul
if not errorlevel 1 (
  echo Build bloqueado: no se permite incluir fuentes Python como datos del ejecutable.
  popd
  endlocal
  exit /b 1
)

py -3 -m pip install -r "%APP%\requirements.txt"
if errorlevel 1 (
  echo No se pudieron instalar las dependencias.
  popd
  endlocal
  exit /b 1
)

py -3 -m PyInstaller --clean --noconfirm --upx-dir "%APP%" "%APP%\EASY DEPLOY.spec"

popd
endlocal
