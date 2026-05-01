@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "PYTHON_EXE="
set "PY_VERSION="
where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3.12 --version >nul 2>&1 && set "PYTHON_EXE=py -3.12"
)
if not defined PYTHON_EXE (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        for /f "tokens=2" %%V in ('python --version 2^>nul') do set "PY_VERSION=%%V"
        if defined PY_VERSION if /I "!PY_VERSION:~0,5!"=="3.12." set "PYTHON_EXE=python"
    )
)
if not defined PYTHON_EXE (
    echo ERROR: Python 3.12 is required for release builds.
    echo Install Python 3.12 or make `py -3.12` available.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   White-Label EXE Builder
echo ========================================
echo.

echo [1/10] Checking Python...
%PYTHON_EXE% --version
if %errorlevel% neq 0 (
    echo ERROR: Python 3.12 launch failed.
    pause
    exit /b 1
)

echo.
echo [2/10] Applying customer branding...
if not exist "scripts\apply_branding.py" (
    echo ERROR: scripts\apply_branding.py not found.
    pause
    exit /b 1
)
%PYTHON_EXE% "scripts\apply_branding.py"
if %errorlevel% neq 0 (
    echo ERROR: Branding apply failed.
    pause
    exit /b 1
)
call "branding_env.cmd"
set "APP_VERSION=%WL_APP_VERSION%"
set "SETUP_NAME=%WL_INSTALLER_NAME%"
set "SPEC_FILE=WhiteLabelApp.spec"
set "INSTALLER_SCRIPT=WhiteLabelInstaller.nsi"
echo ========================================
echo   %WL_APP_NAME% v%APP_VERSION%
echo ========================================
echo Branding: %WL_APP_NAME% v%APP_VERSION%
echo.
echo [3/10] Checking required build files...
if not exist "%SPEC_FILE%" (
    echo ERROR: %SPEC_FILE% not found.
    pause
    exit /b 1
)
if not exist "%INSTALLER_SCRIPT%" (
    echo ERROR: %INSTALLER_SCRIPT% not found.
    pause
    exit /b 1
)
if not exist "requirements-dev.txt" (
    echo ERROR: requirements-dev.txt not found.
    pause
    exit /b 1
)
if not exist "scripts\build_validation.py" (
    echo ERROR: scripts\build_validation.py not found.
    pause
    exit /b 1
)
echo Done.

echo.
echo [4/10] Preparing isolated build environment...
set "BUILD_VENV=%CD%\.venv-build"
set "BUILD_TEMP=%CD%\.build-temp"
set "BUILD_CACHE=%CD%\.build-cache"
if not exist "%BUILD_TEMP%" mkdir "%BUILD_TEMP%"
if not exist "%BUILD_CACHE%" mkdir "%BUILD_CACHE%"
set "TEMP=%BUILD_TEMP%"
set "TMP=%BUILD_TEMP%"
set "PIP_CACHE_DIR=%BUILD_CACHE%"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"

if not exist "%BUILD_VENV%\Scripts\python.exe" (
    echo Creating build virtual environment...
    %PYTHON_EXE% -m venv "%BUILD_VENV%"
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create build virtual environment.
        pause
        exit /b 1
    )
)

set "BUILD_PYTHON=%BUILD_VENV%\Scripts\python.exe"
if not exist "%BUILD_PYTHON%" (
    echo ERROR: Build Python not found at %BUILD_PYTHON%
    pause
    exit /b 1
)

echo Upgrading build tooling...
"%BUILD_PYTHON%" -m pip install --upgrade pip setuptools wheel
if %errorlevel% neq 0 (
    echo ERROR: pip tooling upgrade failed.
    pause
    exit /b 1
)
echo Installing build dependencies...
"%BUILD_PYTHON%" -m pip install --upgrade --prefer-binary -r requirements-dev.txt
if %errorlevel% neq 0 (
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
)
echo Done.

echo.
echo [4.5/10] Cleaning transient test/build folders...
for /d %%D in (".test-runtime" ".smoke_tmp" ".build-pytest-temp*" ".build-pytest-cache*" ".pytest-tmp") do (
    if exist "%%~D" rmdir /s /q "%%~D" >nul 2>nul
)
echo Done.

echo.
echo [5/10] Running build validation...
"%BUILD_PYTHON%" "scripts\build_validation.py"
if %errorlevel% neq 0 (
    echo ERROR: Build validation failed.
    pause
    exit /b 1
)
echo Done.

echo.
echo [6/10] Refreshing integrity baseline...
if exist "licensing_admin\refresh_integrity.py" (
    "%BUILD_PYTHON%" "licensing_admin\refresh_integrity.py"
)
echo Done.

echo.
echo [7/10] Cleaning old build...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
del /f /q "%SETUP_NAME%" >nul 2>nul
echo Done.

echo.
echo [8/10] Building EXE (2-5 minutes)...
"%BUILD_PYTHON%" -m PyInstaller --clean --noconfirm "%SPEC_FILE%"
if %errorlevel% neq 0 (
    echo ERROR: PyInstaller failed.
    pause
    exit /b 1
)
echo EXE built: dist\%WL_DIST_NAME%\%WL_EXE_FILE%

echo.
echo [9/10] Building installer...
set "NSIS_PATH=C:\Program Files (x86)\NSIS\makensis.exe"
if not exist "%NSIS_PATH%" set "NSIS_PATH=C:\Program Files\NSIS\makensis.exe"
if not exist "%NSIS_PATH%" goto nsis_missing

"%NSIS_PATH%" "%INSTALLER_SCRIPT%"
if %errorlevel% neq 0 (
    echo ERROR: NSIS failed.
    pause
    exit /b 1
)
echo.
echo [10/10] Verifying dist output...
if not exist "dist\%WL_DIST_NAME%\%WL_EXE_FILE%" (
    echo ERROR: dist\%WL_DIST_NAME%\%WL_EXE_FILE% missing after build.
    pause
    exit /b 1
)
"%BUILD_PYTHON%" "scripts\dist_runtime_check.py"
if %errorlevel% neq 0 (
    echo ERROR: Dist runtime validation failed.
    pause
    exit /b 1
)
echo.
echo ========================================
echo   SUCCESS
echo   App: %WL_APP_NAME%
echo   Installer: %SETUP_NAME%
echo ========================================
goto end

:nsis_missing
echo ERROR: NSIS not found.
echo Expected at: %NSIS_PATH%
pause
exit /b 1

echo.
:end
pause
