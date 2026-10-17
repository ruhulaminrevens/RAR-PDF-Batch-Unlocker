# Dark workspace redesign — validation record

Implementation baseline: `bbf287e6f4af7aab5d8c010190c44e9cd6ba7555` on `main`.
Published baseline: **v1.0.0 remains intact**. The 1.1.0 source is a release candidate until its Windows checks and screenshots are reviewed.

## Changes

- `ui.py`: dark native Tk/ttk workspace, persistent left navigation, dashboard, scrollable pages, live results, search and complete status filters.
- `app.py`: preserved password groups, mappings, vault actions and settings; added asynchronous scanning, immutable run settings, busy controls, safe cancellation, actual elapsed/estimated time and report shortcuts.
- `branding.py`, `assets/`, `scripts/generate_branding.py`: original document/unlocked-padlock identity; separately drawn 16/24/32/48/64/128/256 ICO sizes, matching window PNGs, vector master and installer artwork.
- `installer/setup.iss`, `scripts/build_windows.ps1`, `build-windows.bat`: consistent branded packaging; same installer AppId to retain upgrade identity; bundled qpdf with official archive SHA-256 check.
- `.github/workflows/windows-release.yml`: main pushes and manual runs validate without publishing. Only an intentional new version tag can publish after all Windows checks pass. Existing releases cannot be replaced; v1.0.0 is explicitly excluded.
- `core.py` and `vault.py`: **unchanged** from baseline.

## Automated checks

- Existing core tests plus explicit stdin password privacy.
- Real Tk tests: password groups/counts, masking, snapshots, busy controls, dry run, filtering/search, invalid paths/mappings, safe stop and retry selection.
- Actual qpdf with synthetic AES-256 PDFs: unlock/verify, no-match, empty-user-password restrictions, already unencrypted, analyze, dry run, retry, no overwrite and unchanged originals.
- Windows Credential Locker: temporary synthetic entry save/load/delete (Windows only).
- Source GUI: actual screenshot capture after analyze and unlock, using synthetic fixtures only.
- Installed Windows EXE: actual mouse/keyboard input, batch confirmation, five-PDF run, three decrypted outputs rechecked with bundled qpdf, unchanged originals, password-free report and clean close.
- Installer: silent install, Desktop/Start Menu shortcut targets and icons, EXE/installer/uninstaller icon extraction, uninstall.

Current run evidence belongs in this document after a real Windows run completes. Passing Linux tests alone does not certify Windows packaging.

## Remaining manual coverage

Automated fixture tests do not cover all real-world PDFs, every Windows scaling/display configuration, SmartScreen reputation or third-party antivirus. Optional vault tests cover a synthetic credential, not migration of existing user entries. Installer remains unsigned. Never use user bank statements in repository screenshots.
