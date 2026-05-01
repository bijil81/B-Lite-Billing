; WhiteLabelInstaller.nsi
; NSIS installer template for the white-label desktop app

Unicode True
SetCompressor /SOLID lzma
!include "branding_build.nsh"

!define APP_NAME        "${WL_APP_NAME}"
!define APP_VERSION     "${WL_APP_VERSION}"
!define APP_PUBLISHER   "${WL_APP_PUBLISHER}"
!define APP_EXE         "${WL_APP_EXE}"
!define INSTALL_DIR     "$PROGRAMFILES\${WL_INSTALL_DIR_NAME}"
!define REG_KEY         "Software\Microsoft\Windows\CurrentVersion\Uninstall\${WL_RUNTIME_DIR_NAME}"

Name              "${APP_NAME} v${APP_VERSION}"
OutFile           "${WL_INSTALLER_OUTFILE}"
InstallDir        "${INSTALL_DIR}"
InstallDirRegKey  HKLM "${REG_KEY}" "InstallLocation"
RequestExecutionLevel admin
ShowInstDetails   show

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"
!include "nsDialogs.nsh"

Var CommonDataRoot
Var ShortcutDesktop
Var ShortcutStartMenu
Var ShortcutPage
Var LegacyInstallRoot
Var DeleteUserData
Var UninstallDataPage

!define MUI_ABORTWARNING
!define MUI_ICON    "${WL_INSTALLER_ICON}"
!define MUI_UNICON  "${WL_INSTALLER_ICON}"

!define MUI_WELCOMEPAGE_TITLE "Welcome to ${APP_NAME} Setup"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
Page custom ShortcutOptionsShow

; --- Shortcut Options Page ---
Function ShortcutOptionsShow
    nsDialogs::Create 1018
    Pop $ShortcutPage

    ${NSD_CreateLabel} 0 0 100% 24u "Choose which shortcuts to create:"
    Pop $0

    ${NSD_CreateCheckbox} 0 30u 100% 12u "Create Desktop Shortcut"
    Pop $0
    ${NSD_Check} $0
    ${NSD_OnClick} $0 OnToggleDesktop

    ${NSD_CreateCheckbox} 0 46u 100% 12u "Create Start Menu Shortcuts"
    Pop $0
    ${NSD_Check} $0
    ${NSD_OnClick} $0 OnToggleStartMenu

    nsDialogs::Show
FunctionEnd

Function OnToggleDesktop
    Pop $0
    ${NSD_GetState} $0 $ShortcutDesktop
FunctionEnd

Function OnToggleStartMenu
    Pop $0
    ${NSD_GetState} $0 $ShortcutStartMenu
FunctionEnd

Function StopRunningApp
    ; Best-effort close of a running older copy before replacing files.
    ; taskkill returns an error when the process is not running; that is OK.
    nsExec::ExecToStack 'taskkill /IM "${APP_EXE}" /T /F'
    Pop $0
    Pop $1
    Sleep 1000
FunctionEnd

Function DetectLegacyInstall
    StrCpy $LegacyInstallRoot ""

    ; Old Bobys-branded builds used different product identities, install
    ; directories, and uninstall registry keys. That allows side-by-side
    ; installs instead of in-place upgrade detection.
    IfFileExists "$PROGRAMFILES\BobySalon\*.*" 0 +2
        StrCpy $LegacyInstallRoot "$PROGRAMFILES\BobySalon"
    ${If} $LegacyInstallRoot == ""
        IfFileExists "$PROGRAMFILES\Bobys Billing\*.*" 0 +2
            StrCpy $LegacyInstallRoot "$PROGRAMFILES\Bobys Billing"
    ${EndIf}
    ${If} $LegacyInstallRoot == ""
        IfFileExists "$PROGRAMFILES\Bobys Billing V5.6\*.*" 0 +2
            StrCpy $LegacyInstallRoot "$PROGRAMFILES\Bobys Billing V5.6"
    ${EndIf}

    ${If} $LegacyInstallRoot != ""
        MessageBox MB_ICONEXCLAMATION|MB_OK \
            "Legacy Bobys-branded installation detected at:$\r$\n$LegacyInstallRoot$\r$\n$\r$\nThis white-label installer uses a separate product identity (${WL_RUNTIME_DIR_NAME}), so the old Bobys install will remain side by side unless it is removed first."
    ${EndIf}
FunctionEnd

; Pre-set defaults before page shows
Function .onInit
    StrCpy $ShortcutDesktop 1
    StrCpy $ShortcutStartMenu 1
    Call DetectLegacyInstall
FunctionEnd

!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN      "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${APP_NAME} now"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
UninstPage custom un.UninstallDataOptionsShow
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Function un.onInit
    StrCpy $DeleteUserData 0
FunctionEnd

Function un.UninstallDataOptionsShow
    nsDialogs::Create 1018
    Pop $UninstallDataPage

    ${NSD_CreateLabel} 0 0 100% 28u "Program files will be removed by default. Choose whether to also remove user/business data."
    Pop $0

    ${NSD_CreateCheckbox} 0 38u 100% 12u "Full data delete: remove AppData and ProgramData for this app"
    Pop $0
    ${NSD_Uncheck} $0
    ${NSD_OnClick} $0 un.OnToggleDeleteUserData

    ${NSD_CreateLabel} 0 60u 100% 42u "Leave this unchecked for normal update/reinstall. Check it only for a clean reset, because it can remove settings, local database, bills, backups, licensing/trial state, and cache for this app."
    Pop $0

    nsDialogs::Show
FunctionEnd

Function un.OnToggleDeleteUserData
    Pop $0
    ${NSD_GetState} $0 $DeleteUserData
FunctionEnd

Function un.StopRunningApp
    ; Best-effort close before uninstalling the EXE from Program Files.
    nsExec::ExecToStack 'taskkill /IM "${APP_EXE}" /T /F'
    Pop $0
    Pop $1
    Sleep 1000
FunctionEnd

VIProductVersion                    "5.6.0.0"
VIAddVersionKey "ProductName"       "${APP_NAME}"
VIAddVersionKey "ProductVersion"    "${APP_VERSION}"
VIAddVersionKey "CompanyName"       "${APP_PUBLISHER}"
VIAddVersionKey "FileDescription"   "${APP_NAME} Installer"
VIAddVersionKey "FileVersion"       "${APP_VERSION}"
VIAddVersionKey "LegalCopyright"    "Copyright 2026 ${APP_PUBLISHER}"

Section "MainSection" SEC01
    ExpandEnvStrings $CommonDataRoot "%ProgramData%\\${WL_RUNTIME_DIR_NAME}"
    Call StopRunningApp

    ; Remove the previous program folder before copying the new onedir build.
    ; User data lives under AppData/ProgramData and is not touched here.
    RMDir /r "$INSTDIR"
    IfFileExists "$INSTDIR\${APP_EXE}" 0 +3
        MessageBox MB_ICONSTOP "Could not replace ${APP_EXE}. Close ${APP_NAME} and run the installer as administrator."
        Abort

    SetOutPath "$INSTDIR"
    SetOverwrite on

    ; Copy the full PyInstaller onedir layout, including the "_internal"
    ; runtime folder that contains the embedded Python standard library.
    File /r "dist\${WL_DIST_DIR}\*"
    File "${WL_INSTALLER_ICON}"

    CreateDirectory "$CommonDataRoot\licensing"
    CreateDirectory "$CommonDataRoot\cache"
    CreateDirectory "$CommonDataRoot\temp"

    ; Desktop shortcut (optional)
    ${If} $ShortcutDesktop = ${BST_CHECKED}
        CreateShortcut \
            "$DESKTOP\${APP_NAME}.lnk" \
            "$INSTDIR\${APP_EXE}" \
            "" \
            "$INSTDIR\${WL_INSTALLER_ICON_NAME}" \
            0 SW_SHOWNORMAL "" "${APP_NAME}"
    ${EndIf}

    ; Start Menu shortcuts (optional)
    ${If} $ShortcutStartMenu = ${BST_CHECKED}
        CreateDirectory "$SMPROGRAMS\${APP_NAME}"
        CreateShortcut \
            "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
            "$INSTDIR\${APP_EXE}" \
            "" \
            "$INSTDIR\${WL_INSTALLER_ICON_NAME}" \
            0 SW_SHOWNORMAL "" "${APP_NAME}"
        CreateShortcut \
            "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" \
            "$INSTDIR\Uninstall.exe"
    ${EndIf}

    WriteRegStr   HKLM "${REG_KEY}" "DisplayName"     "${APP_NAME}"
    WriteRegStr   HKLM "${REG_KEY}" "DisplayVersion"  "${APP_VERSION}"
    WriteRegStr   HKLM "${REG_KEY}" "Publisher"       "${APP_PUBLISHER}"
    WriteRegStr   HKLM "${REG_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr   HKLM "${REG_KEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr   HKLM "${REG_KEY}" "DisplayIcon"     "$INSTDIR\${WL_INSTALLER_ICON_NAME}"
    WriteRegDWORD HKLM "${REG_KEY}" "NoModify"        1
    WriteRegDWORD HKLM "${REG_KEY}" "NoRepair"        1

    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "${REG_KEY}" "EstimatedSize" "$0"

    WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
    Call un.StopRunningApp

    ; Remove version-specific integrity/cache/temp files only.
    ExpandEnvStrings $CommonDataRoot "%ProgramData%\\${WL_RUNTIME_DIR_NAME}"
    Delete "$CommonDataRoot\licensing\integrity_baseline.json"
    Delete "$APPDATA\${WL_APPDATA_DIR_NAME}\licensing\integrity_baseline.json"
    Delete "$CommonDataRoot\temp\*.*"
    Delete "$CommonDataRoot\cache\*.*"
    Delete "$CommonDataRoot\logs\*.log"
    RMDir /r "$CommonDataRoot\temp"
    RMDir /r "$CommonDataRoot\cache"
    RMDir /r "$CommonDataRoot\logs"
    ; Do not remove licensing state, trial history, database, backups, settings, or templates.

    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir /r "$INSTDIR"
    RMDir /r "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"

    ${If} $DeleteUserData = ${BST_CHECKED}
        MessageBox MB_ICONEXCLAMATION|MB_YESNO|MB_DEFBUTTON2 \
            "Full data delete is selected.$\r$\n$\r$\nThis will remove local app data for ${APP_NAME}, including settings, local database, bills, backups, licensing/trial state, and cache.$\r$\n$\r$\nContinue?" \
            IDYES +2
            Goto skip_full_data_delete
        RMDir /r "$APPDATA\${WL_APPDATA_DIR_NAME}"
        RMDir /r "$CommonDataRoot"
    ${EndIf}
    skip_full_data_delete:

    DeleteRegKey HKLM "${REG_KEY}"
SectionEnd

Function .onInstSuccess
    MessageBox MB_ICONINFORMATION \
        "${APP_NAME} v${APP_VERSION} installed!$\r$\nData: %APPDATA%\${WL_APPDATA_DIR_NAME}\" \
        /SD IDOK
FunctionEnd
