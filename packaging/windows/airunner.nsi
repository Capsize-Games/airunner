!include "MUI2.nsh"

!ifndef APP_NAME
  !define APP_NAME "AIRunner"
!endif

!ifndef APP_VERSION
  !define APP_VERSION "0.0.0"
!endif

!ifndef STAGING_DIR
  !error "STAGING_DIR is required"
!endif

Name "${APP_NAME} ${APP_VERSION}"
OutFile "airunner-${APP_VERSION}-windows-x64-setup.exe"
InstallDir "$PROGRAMFILES64\AIRunner"
InstallDirRegKey HKLM "Software\AIRunner" "Install_Dir"
RequestExecutionLevel admin
Unicode True

!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${STAGING_DIR}\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "Install"
  SetOutPath "$INSTDIR"
  File "${STAGING_DIR}\README.md"
  File "${STAGING_DIR}\LICENSE"

  SetOutPath "$INSTDIR\app"
  File /r "${STAGING_DIR}\app\*"

  SetOutPath "$INSTDIR\bin"
  File /r "${STAGING_DIR}\bin\*"

  SetOutPath "$INSTDIR\python"
  File /r "${STAGING_DIR}\python\*"

  SetOutPath "$INSTDIR\share"
  File /r "${STAGING_DIR}\share\*"

  IfFileExists "${STAGING_DIR}\deployment\*" 0 +3
    SetOutPath "$INSTDIR\deployment"
    File /r "${STAGING_DIR}\deployment\*"

  WriteRegStr HKLM "Software\AIRunner" "Install_Dir" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIRunner" "DisplayName" "AIRunner"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIRunner" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIRunner" "Publisher" "AIRunner"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIRunner" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIRunner" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIRunner" "NoRepair" 1

  CreateDirectory "$SMPROGRAMS\AIRunner"
  CreateShortcut "$SMPROGRAMS\AIRunner\AIRunner.lnk" "$INSTDIR\bin\airunner.exe"
  CreateShortcut "$SMPROGRAMS\AIRunner\Uninstall.lnk" "$INSTDIR\Uninstall.exe"

  WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
  Delete "$SMPROGRAMS\AIRunner\AIRunner.lnk"
  Delete "$SMPROGRAMS\AIRunner\Uninstall.lnk"
  RMDir "$SMPROGRAMS\AIRunner"

  RMDir /r "$INSTDIR\app"
  RMDir /r "$INSTDIR\bin"
  RMDir /r "$INSTDIR\deployment"
  RMDir /r "$INSTDIR\python"
  RMDir /r "$INSTDIR\share"
  Delete "$INSTDIR\README.md"
  Delete "$INSTDIR\LICENSE"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"

  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIRunner"
  DeleteRegKey HKLM "Software\AIRunner"
SectionEnd
