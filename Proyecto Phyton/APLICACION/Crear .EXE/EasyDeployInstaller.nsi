Unicode True
RequestExecutionLevel admin
!include "x64.nsh"

!ifndef APP_VERSION
  !define APP_VERSION "0.0.0.0"
!endif

!ifndef SOURCE_EXE
  !error "Falta SOURCE_EXE. Ejecuta build_instalador_easydeploy.bat."
!endif

!ifndef OUT_FILE
  !define OUT_FILE "EasyDeploy_Setup.exe"
!endif

Name "Easy Deploy"
OutFile "${OUT_FILE}"
InstallDir "$PROGRAMFILES64\EasyDeploy"
InstallDirRegKey HKLM "Software\EasyDeploy" "InstallDir"
ShowInstDetails show
ShowUninstDetails show

VIProductVersion "${APP_VERSION}"
VIAddVersionKey "ProductName" "Easy Deploy"
VIAddVersionKey "CompanyName" "Easy Deploy"
VIAddVersionKey "FileDescription" "Instalador de Easy Deploy"
VIAddVersionKey "FileVersion" "${APP_VERSION}"
VIAddVersionKey "ProductVersion" "${APP_VERSION}"
VIAddVersionKey "LegalCopyright" "Copyright 2026 Easy Deploy"

BrandingText "Easy Deploy"

!define APP_EXE "EASY DEPLOY.exe"
!define APP_DIR_NAME "EasyDeploy"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\EasyDeploy"

Page directory
Page instfiles

UninstPage uninstConfirm
UninstPage instfiles

Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "Easy Deploy requiere Windows de 64 bits."
    Abort
  ${EndIf}
FunctionEnd

Section "Instalar Easy Deploy" SEC_INSTALL
  SetShellVarContext all

  SetOutPath "$INSTDIR"

  ; No borrar AppData, logs ni configuracion del usuario.
  ; Solo se sustituye el ejecutable instalado.
  File "${SOURCE_EXE}"

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Accesos directos.
  CreateDirectory "$SMPROGRAMS\Easy Deploy"
  CreateShortcut "$SMPROGRAMS\Easy Deploy\Easy Deploy.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
  CreateShortcut "$SMPROGRAMS\Easy Deploy\Desinstalar Easy Deploy.lnk" "$INSTDIR\Uninstall.exe"

  ; Escritorio publico: C:\Users\Public\Desktop en instalaciones con SetShellVarContext all.
  CreateShortcut "$DESKTOP\Easy Deploy.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0

  ; Registro de instalacion/desinstalacion.
  WriteRegStr HKLM "Software\EasyDeploy" "InstallDir" "$INSTDIR"

  WriteRegStr HKLM "${UNINSTALL_KEY}" "DisplayName" "Easy Deploy"
  WriteRegStr HKLM "${UNINSTALL_KEY}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKLM "${UNINSTALL_KEY}" "Publisher" "Easy Deploy"
  WriteRegStr HKLM "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "${UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
  WriteRegStr HKLM "${UNINSTALL_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoRepair" 1
SectionEnd

Section "Uninstall"
  SetShellVarContext all

  Delete "$DESKTOP\Easy Deploy.lnk"
  Delete "$SMPROGRAMS\Easy Deploy\Easy Deploy.lnk"
  Delete "$SMPROGRAMS\Easy Deploy\Desinstalar Easy Deploy.lnk"
  RMDir "$SMPROGRAMS\Easy Deploy"

  Delete "$INSTDIR\${APP_EXE}"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"

  DeleteRegKey HKLM "${UNINSTALL_KEY}"
  DeleteRegKey HKLM "Software\EasyDeploy"

  ; No borrar %LOCALAPPDATA%\EasyDeploy.
  ; No borrar logs, licencia ni configuracion local.
SectionEnd
