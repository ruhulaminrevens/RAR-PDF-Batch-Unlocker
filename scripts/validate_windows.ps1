$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force qa/screenshots | Out-Null
$installer=(Resolve-Path 'release/RAR-PDF-Batch-Unlocker-Setup.exe').Path
python scripts/capture_installer.py --installer $installer
if ($LASTEXITCODE -ne 0) { throw 'Installer screenshot capture failed' }
$installDir=Join-Path $env:LOCALAPPDATA 'RAR-Installed-QA'
$expectedVersion=(python -c "from branding import VERSION; print(VERSION)").Trim()
# Upgrade path: install the published v1.1.0 first, then install this build over it.
$upgrade=@{ from='v1.1.0'; tested=$false }
if ($env:GH_TOKEN) {
    New-Item -ItemType Directory -Force qa/previous | Out-Null
    gh release download v1.1.0 --repo $env:GITHUB_REPOSITORY --pattern 'RAR-PDF-Batch-Unlocker-Setup.exe' --dir qa/previous --clobber
    if ($LASTEXITCODE -ne 0) { throw 'Could not download the v1.1.0 installer for the upgrade test' }
    $old=Start-Process (Resolve-Path 'qa/previous/RAR-PDF-Batch-Unlocker-Setup.exe').Path -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/TASKS=desktopicon',"/DIR=`"$installDir`"",'/LOG=qa/install-previous.log') -Wait -PassThru
    if ($old.ExitCode -ne 0) { throw "v1.1.0 installer returned $($old.ExitCode)" }
    if ((Get-Item (Join-Path $installDir 'RAR-PDF-Batch-Unlocker.exe')).VersionInfo.FileVersion -ne '1.1.0') { throw 'v1.1.0 baseline not installed' }
    $upgrade.tested=$true
}
$p=Start-Process $installer -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/TASKS=desktopicon',"/DIR=`"$installDir`"",'/LOG=qa/install.log') -Wait -PassThru
if ($p.ExitCode -ne 0) { throw "Installer returned $($p.ExitCode)" }
$exe=Join-Path $installDir 'RAR-PDF-Batch-Unlocker.exe'
if (!(Test-Path $exe)) { throw 'Installed EXE missing' }
$version=(Get-Item $exe).VersionInfo
if ($version.ProductName -ne 'RAR PDF Batch Unlocker' -or $version.FileVersion -ne $expectedVersion) { throw 'Installed EXE branding/version metadata mismatch' }
$entries=@(Get-ChildItem 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall','HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall' -ErrorAction SilentlyContinue | Get-ItemProperty | Where-Object { $_.DisplayName -like 'RAR PDF Batch Unlocker*' })
if ($entries.Count -ne 1) { throw "Expected one Programs and Features entry, found $($entries.Count)" }
if ($entries[0].DisplayVersion -ne $expectedVersion) { throw "Uninstall entry shows $($entries[0].DisplayVersion)" }
if ($upgrade.tested) { $upgrade.result="v1.1.0 replaced by $expectedVersion; one uninstall entry" }
foreach ($notice in @('qpdf/qpdf-manifest.json','THIRD-PARTY-NOTICES.txt')) { if (!(Test-Path (Join-Path $installDir $notice))) { throw "Installed notice missing: $notice" } }
$wsh=New-Object -ComObject WScript.Shell
$shortcuts=@((Join-Path ([Environment]::GetFolderPath('Desktop')) 'RAR PDF Batch Unlocker.lnk'),(Join-Path ([Environment]::GetFolderPath('Programs')) 'RAR PDF Batch Unlocker.lnk'))
foreach ($path in $shortcuts) {
    if (!(Test-Path $path)) { throw "Shortcut missing: $path" }
    $shortcut=$wsh.CreateShortcut($path)
    if ($shortcut.TargetPath -ne $exe) { throw 'Shortcut target does not match installed EXE' }
    if (!$shortcut.IconLocation.StartsWith($exe)) { throw 'Shortcut icon does not reference branded EXE' }
}
Add-Type -AssemblyName System.Drawing
foreach ($pair in @(@($exe,'installed-exe-icon.png'),@($installer,'installer-icon.png'),@((Join-Path $installDir 'unins000.exe'),'uninstaller-icon.png'))) {
    $icon=[System.Drawing.Icon]::ExtractAssociatedIcon($pair[0])
    if (!$icon) { throw "No icon resource in $($pair[0])" }
    $bitmap=$icon.ToBitmap();$bitmap.Save((Join-Path (Resolve-Path qa/screenshots) $pair[1]));$bitmap.Dispose();$icon.Dispose()
}
python scripts/verify_icon_resources.py
if ($LASTEXITCODE -ne 0) { throw 'Extracted icon does not match branding' }
python scripts/validate_installed_qt.py --exe $exe --qa qa
if ($LASTEXITCODE -ne 0) { throw 'Installed Qt GUI smoke failed' }
$uninstall=Start-Process (Join-Path $installDir 'unins000.exe') -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -Wait -PassThru
if ($uninstall.ExitCode -ne 0) { throw 'Uninstall failed' }
Start-Sleep -Seconds 2
if (Test-Path $exe) { throw 'Uninstaller left application EXE behind' }
$left=@(Get-ChildItem $installDir -Recurse -File -ErrorAction SilentlyContinue)
if ($left.Count -gt 0) { throw "Uninstaller left files: $($left.FullName -join ', ')" }
foreach ($path in $shortcuts) { if (Test-Path $path) { throw "Shortcut left after uninstall: $path" } }
@{ version=$expectedVersion; upgrade_from_v1_1_0=$upgrade; installation='passed'; programs_and_features='one entry'; notices='installed'; desktop_shortcut='passed'; start_menu_shortcut='passed'; icon_resources='extracted'; uninstallation='passed, no files or shortcuts left' } | ConvertTo-Json -Depth 4 | Set-Content qa/installer-validation.json
Get-Content qa/installer-validation.json | Write-Host
$json=(Get-Content qa/installer-validation.json -Raw) -replace "`r?`n",' '
Write-Host "::notice title=installer validation::$json"
