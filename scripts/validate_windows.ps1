$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force qa/screenshots | Out-Null
$installer=(Resolve-Path 'release/RAR-PDF-Batch-Unlocker-Setup.exe').Path
python scripts/capture_installer.py --installer $installer
if ($LASTEXITCODE -ne 0) { throw 'Installer screenshot capture failed' }
$installDir=Join-Path $env:LOCALAPPDATA 'RAR-Installed-QA'
$p=Start-Process $installer -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/TASKS=desktopicon',"/DIR=`"$installDir`"",'/LOG=qa/install.log') -Wait -PassThru
if ($p.ExitCode -ne 0) { throw "Installer returned $($p.ExitCode)" }
$exe=Join-Path $installDir 'RAR-PDF-Batch-Unlocker.exe'
if (!(Test-Path $exe)) { throw 'Installed EXE missing' }
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
python scripts/validate_installed.py --exe $exe --qa qa
if ($LASTEXITCODE -ne 0) { throw 'Installed GUI functional QA failed' }
$uninstall=Start-Process (Join-Path $installDir 'unins000.exe') -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -Wait -PassThru
if ($uninstall.ExitCode -ne 0) { throw 'Uninstall failed' }
Start-Sleep -Seconds 2
if (Test-Path $exe) { throw 'Uninstaller left application EXE behind' }
@{ installation='passed'; desktop_shortcut='passed'; start_menu_shortcut='passed'; icon_resources='extracted'; uninstallation='passed' } | ConvertTo-Json | Set-Content qa/installer-validation.json
