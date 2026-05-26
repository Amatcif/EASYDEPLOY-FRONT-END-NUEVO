@echo off
setlocal

pushd "%~dp0"
call "%~dp0build_easy_deploy_seguro.bat"
set "RESULT=%ERRORLEVEL%"
popd

exit /b %RESULT%
