@echo off
setlocal
cd /d "%~dp0"
echo [1/3] Running unit tests...
py -3 -m unittest discover -s tests -v
if errorlevel 1 goto fail
echo [2/3] Checking PyInstaller...
py -3 -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
  echo PyInstaller is not installed. Install with: py -3 -m pip install -r requirements-build.txt
  goto fail
)
echo [3/3] Building offline GUI application...
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name "RAR-PDF-Batch-Unlocker" app.py
if errorlevel 1 goto fail
echo EXE READY: %cd%\dist\RAR-PDF-Batch-Unlocker.exe
echo NOTE: qpdf must be installed separately on the target Windows PC.
echo NOTE: Binary is UNSIGNED unless signed with your own code-signing certificate.
pause
exit /b 0
:fail
echo Build failed. No verified release was produced.
pause
exit /b 1
