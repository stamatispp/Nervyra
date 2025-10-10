@echo off
setlocal

set "SRC=U:\IT\APP\Nervyra\dist\Nervyra.exe"
set "DSTDIR=C:\Temp"
set "DST=%DSTDIR%\Nervyra.exe"

echo [INFO] Deploying Nervyra...

:: Check source
if not exist "%SRC%" (
  echo [ERROR] Source not found: %SRC%
  pause
  exit /b 1
)

:: Ensure destination folder
if not exist "%DSTDIR%" (
  mkdir "%DSTDIR%" || (
    echo [ERROR] Failed to create %DSTDIR%
    pause
    exit /b 1
  )
)

:: Copy file
echo [INFO] Copying "%SRC%" to "%DST%"...
copy /Y "%SRC%" "%DST%" >nul
if errorlevel 1 (
  echo [ERROR] Copy failed!
  pause
  exit /b 1
)

:: Create Desktop shortcut (detect real Desktop folder from Windows Shell)
echo [INFO] Creating Desktop shortcut...
set "VBS=%TEMP%\mkshortcut.vbs"
> "%VBS%" echo Set oWS = WScript.CreateObject("WScript.Shell")
>>"%VBS%" echo sDesktop = oWS.SpecialFolders("Desktop")
>>"%VBS%" echo Set oLink = oWS.CreateShortcut(sDesktop ^& "\Nervyra.lnk")
>>"%VBS%" echo oLink.TargetPath = "%DST%"
>>"%VBS%" echo oLink.WorkingDirectory = "%DSTDIR%"
>>"%VBS%" echo oLink.IconLocation = "%DST%,0"
>>"%VBS%" echo oLink.Save

cscript //nologo "%VBS%"
del "%VBS%"

echo [OK] Deployed to "%DST%" and shortcut created on Desktop.
pause
endlocal
