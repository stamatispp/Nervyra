@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "LOG=%TEMP%\nervyra_build.log"
echo === Nervyra BUILD started %DATE% %TIME% === > "%LOG%"
echo === Nervyra BUILD started %DATE% %TIME% ===

REM ===== Stay in this script's folder =====
pushd "%~dp0" || (
  echo [ERROR] Cannot change dir to "%~dp0"
  >>"%LOG%" echo [ERROR] Cannot change dir to "%~dp0"
  goto :fail
)

REM ===== Find Python launcher =====
where py 1>>"%LOG%" 2>&1
if %errorlevel%==0 ( set "PY=py -3" ) else (
  where python 1>>"%LOG%" 2>&1 || (
    echo [ERROR] Python not found. Install Python 3.x or enable the "py" launcher.
    >>"%LOG%" echo [ERROR] Python not found.
    goto :fail
  )
  set "PY=python"
)
echo [INFO] Using Python launcher: %PY%

REM ===== Clean old outputs =====
if exist build  (rmdir /s /q build)  >> "%LOG%" 2>&1
if exist dist   (rmdir /s /q dist)   >> "%LOG%" 2>&1
if exist Nervyra.spec del /f /q Nervyra.spec >> "%LOG%" 2>&1

REM ===== Ensure dependencies =====
echo [INFO] Ensuring pip/pyinstaller/PySide6 are installed...
%PY% -m pip --version || goto :fail
%PY% -m pip install --upgrade pip         || goto :fail
%PY% -m pip install --upgrade pyinstaller || goto :fail
%PY% -m pip install --upgrade PySide6     || goto :fail

REM ===== Compile Qt resources if present =====
if exist "resources.qrc" (
  echo [INFO] Compiling Qt resources...
  where pyside6-rcc 1>>"%LOG%" 2>&1
  if %errorlevel%==0 (
    pyside6-rcc "resources.qrc" -o "resources_rc.py" || goto :fail
  ) else (
    %PY% -c "import sys,subprocess; sys.exit(subprocess.call(['pyside6-rcc','resources.qrc','-o','resources_rc.py']))" || goto :fail
  )
  if not exist "resources_rc.py" (
    echo [ERROR] resources_rc.py not generated.
    goto :fail
  )
) else (
  echo [WARN] resources.qrc not found. Skipping resource compile.
)

REM ===== Sanity checks =====
if not exist "main.py" (
  echo [ERROR] Missing main.py next to this BAT.
  goto :fail
)
if not exist "icon.ico" (
  echo [WARN] icon.ico not found. EXE will use default icon.
)

REM ===== Build EXE =====
echo [INFO] Building Nervyra (onefile)...
%PY% -m PyInstaller ^
  --name "Nervyra" ^
  --onefile ^
  --windowed ^
  --icon "icon.ico" ^
  "main.py" || goto :fail

set "BUILD_EXE=%cd%\dist\Nervyra.exe"
if not exist "%BUILD_EXE%" (
  echo [ERROR] Build EXE not found: "%BUILD_EXE%"
  goto :fail
)

for %%A in ("%BUILD_EXE%") do set "BUILD_SIZE=%%~zA"
set /a BUILD_KB=(BUILD_SIZE+1023)/1024
echo.
echo ========= BUILD DONE =========
echo Output: "%BUILD_EXE%"
echo Size  : !BUILD_KB! KB
>>"%LOG%" echo [INFO] Build finished: !BUILD_KB! KB

goto :end

:fail
echo.
echo [FAILED] See detailed log at: %LOG%
echo Current folder: %cd%
echo.
echo Press any key to view the log...
pause >nul
notepad "%LOG%" 2>nul

:end
echo.
echo Press any key to exit...
pause >nul
popd
endlocal
