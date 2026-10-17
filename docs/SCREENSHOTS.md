# Real Windows screenshots

Captured from Windows Actions [run 39014860198](https://github.com/ruhulaminrevens/RAR-PDF-Batch-Unlocker/actions/runs/39014860198), validated application commit `1af596b40d3bd0b5e439d7e78f5eab379e9e8889`. All documents, names and passwords used here are public synthetic test fixtures. No design mockup is presented as a real app screenshot.

| Capture | Provenance |
| --- | --- |
| [Installed window](screenshots/installed-window.png) | Actual installed PyInstaller EXE after a five-PDF batch; native titlebar and icon visible |
| [Installed dashboard](screenshots/installed-batch.png) | Actual installed EXE client area after processing |
| [Password groups](screenshots/password-groups.png) | Actual source GUI on Windows; synthetic password masked |
| [Security analysis](screenshots/security-analysis.png) | Actual source GUI after real qpdf inspection |
| [Batch results](screenshots/batch-results.png) | Actual source GUI after real qpdf processing |
| [Run settings](screenshots/run-settings.png) | Actual source GUI, default settings |
| [Installer wizard](screenshots/installer.png) | Actual Inno Setup wizard, before silent install QA |

The desktop was set to 1920×1080 so screenshots are complete. Pages scroll vertically; result tables also scroll horizontally when necessary. Screenshot bytes were copied unchanged from the successful workflow artifact.

## Reproduce

Install `requirements-build.txt` and `requirements-test.txt`. Make qpdf available on PATH. On a visible Windows desktop:

```powershell
python scripts/prepare_desktop.py
python scripts/capture_screenshots.py
```

The source capture script creates its own synthetic PDFs under `qa/demo`, runs analysis and unlocking, verifies hashes and captures actual pixels. Use a fresh QA workspace for a repeat run because outputs are intentionally never overwritten. `scripts/validate_windows.ps1` handles the actual installed EXE, shortcuts, icon resources and uninstall.

## Manual checks remaining

Automated Windows Server runner testing is complete. A first run on the user's own Windows 10/11 machine remains useful for display scaling, antivirus/SmartScreen behavior and representative real PDFs. A 100–1,000 document performance benchmark is not claimed. Never commit private documents or real passwords.
