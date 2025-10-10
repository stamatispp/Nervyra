@echo off
setlocal enableextensions

rem === CONFIG ===
set "SRC=\\10.0.0.13\files\IT\APP\Nervyra\dist\Nervyra.exe"
set "DSTDIR=C:\Temp"
set "DST=%DSTDIR%\Nervyra.exe"
set "SHORTCUT=%Public%\Desktop\Nervyra.lnk"
rem ==============

echo [INFO] Deploying Nervyra...

rem --- check source ---
if not exist "%SRC%" (
  echo [ERROR] Source not found: %SRC%
  exit /b 1
)

rem --- make sure C:\Temp exists ---
if not exist "%DSTDIR%" mkdir "%DSTDIR%" 2>nul

rem --- copy exe ---
copy /y "%SRC%" "%DST%" >nul
if errorlevel 1 (
  echo [ERROR] Copy failed from "%SRC%" to "%DST%"
  exit /b 2
)

rem --- create shortcut on Public Desktop ---
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws=New-Object -ComObject WScript.Shell; " ^
  "$s=$ws.CreateShortcut('%SHORTCUT%'); " ^
  "$s.TargetPath='%DST%'; " ^
  "$s.WorkingDirectory='%DSTDIR%'; " ^
  "$s.IconLocation='%DST%,0'; " ^
  "$s.Save()"

if errorlevel 1 (
  echo [WARN] Shortcut creation may have failed: "%SHORTCUT%"
) else (
  echo [INFO] Shortcut created: "%SHORTCUT%"
)

echo [OK] Deployment completed.
exit /b 0
