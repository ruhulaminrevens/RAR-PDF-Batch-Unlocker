@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: sign-windows.bat CERTIFICATE_THUMBPRINT
  echo Requires Windows SDK signtool and a valid installed code-signing certificate.
  exit /b 1
)
where signtool >nul 2>&1 || (echo signtool not found & exit /b 1)
if not exist "dist\RAR-PDF-Batch-Unlocker\RAR-PDF-Batch-Unlocker.exe" (echo Build the EXE first & exit /b 1)
signtool sign /fd SHA256 /sha "%~1" /tr http://timestamp.digicert.com /td SHA256 "dist\RAR-PDF-Batch-Unlocker\RAR-PDF-Batch-Unlocker.exe"
if errorlevel 1 exit /b 1
signtool verify /pa /v "dist\RAR-PDF-Batch-Unlocker\RAR-PDF-Batch-Unlocker.exe"
if errorlevel 1 exit /b 1
echo Signed and verified. Record publisher identity and certificate details for deployment.
