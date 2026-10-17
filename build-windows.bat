@echo off
setlocal
cd /d "%~dp0"
python -m pip install -r requirements-build.txt -r requirements-test.txt
if errorlevel 1 goto fail
python -m unittest discover -s tests -v
if errorlevel 1 goto fail
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1
if errorlevel 1 goto fail
echo GUI READY: %cd%\dist\RAR-PDF-Batch-Unlocker\RAR-PDF-Batch-Unlocker.exe
echo Compile installer\setup.iss using Inno Setup 6 to create the installer.
echo No release is published by this script. The build is unsigned.
pause
exit /b 0
:fail
echo Build failed. No verified release was produced.
pause
exit /b 1
