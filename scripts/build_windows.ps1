$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$archive = 'qpdf-12.4.2-mingw64.zip'
$expected = '773d2fa0c7d161e2271430734338e560a07b25d0edf11ceee8e53de435012766'
if (!(Test-Path $archive)) {
    Invoke-WebRequest "https://github.com/qpdf/qpdf/releases/download/v12.4.2/$archive" -OutFile $archive
}
if ((Get-FileHash $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw 'qpdf archive SHA-256 mismatch' }
Expand-Archive $archive -DestinationPath qpdf-extract -Force
$engine = Get-ChildItem qpdf-extract -Filter qpdf.exe -Recurse | Select-Object -First 1
if (!$engine) { throw 'Official qpdf archive has no executable' }
New-Item -ItemType Directory -Force bundled-qpdf/bin | Out-Null
Copy-Item "$($engine.Directory.FullName)/*" bundled-qpdf/bin -Recurse -Force
# Include the upstream license files alongside the bundled runtime.
Get-ChildItem qpdf-extract -Recurse -File | Where-Object { $_.Name -match '^(NOTICE|LICENSE|COPYING)' } | ForEach-Object { Copy-Item $_.FullName bundled-qpdf -Force }
& bundled-qpdf/bin/qpdf.exe --version
if ($LASTEXITCODE -ne 0) { throw 'Bundled qpdf failed to start' }
python -m PyInstaller --noconfirm --clean --onedir --windowed --name RAR-PDF-Batch-Unlocker --icon assets/app.ico --version-file assets/version-info.txt --add-data 'assets;assets' --hidden-import keyring.backends.Windows --hidden-import reports --hidden-import toolkit --hidden-import diagnostics --collect-all pypdfium2 --collect-all pdfminer --collect-all pdfplumber --collect-all docx --collect-all openpyxl --collect-all tkinterdnd2 app.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
Copy-Item bundled-qpdf dist/RAR-PDF-Batch-Unlocker/qpdf -Recurse -Force
python scripts/write_manifest.py dist/RAR-PDF-Batch-Unlocker/qpdf
if ($LASTEXITCODE -ne 0) { throw 'Engine manifest failed' }
Copy-Item THIRD-PARTY-NOTICES.txt dist/RAR-PDF-Batch-Unlocker/ -Force
