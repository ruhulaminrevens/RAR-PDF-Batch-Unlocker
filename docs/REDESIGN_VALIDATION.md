# Dark workspace redesign — validation record

Implementation baseline: `bbf287e6f4af7aab5d8c010190c44e9cd6ba7555` on `main`.
Published baseline: **v1.0.0 remains intact**. The 1.1.0 application passed Windows checks and real screenshot review. The release workflow promotes the exact validated installer without rebuilding it.

## Changes

- `ui.py`: dark native Tk/ttk workspace, persistent left navigation, dashboard, scrollable pages, live results, search and complete status filters.
- `app.py`: preserved password groups, mappings, vault actions and settings; added asynchronous scanning, immutable run settings, busy controls, safe cancellation, actual elapsed/estimated time and report shortcuts.
- `branding.py`, `assets/`, `scripts/generate_branding.py`: original document/unlocked-padlock identity; separately drawn 16/24/32/48/64/128/256 ICO sizes, matching window PNGs, vector master and installer artwork.
- `installer/setup.iss`, `scripts/build_windows.ps1`, `build-windows.bat`: consistent branded packaging; same installer AppId to retain upgrade identity; bundled qpdf with official archive SHA-256 check.
- `.github/workflows/windows-release.yml`: main pushes and manual runs validate without publishing. A separate publisher requires an intentional `release/v1.1.0` branch, a successful declared Windows run and unchanged application source. Existing releases cannot be replaced; v1.0.0 is explicitly excluded.
- `core.py` and `vault.py`: **unchanged** from baseline.

## Automated checks

- Existing core tests plus explicit stdin password privacy.
- Real Tk tests: password groups/counts, masking, snapshots, busy controls, dry run, filtering/search, invalid paths/mappings, safe stop and retry selection.
- Actual qpdf with synthetic AES-256 PDFs: unlock/verify, no-match, empty-user-password restrictions, already unencrypted, analyze, dry run, retry, no overwrite and unchanged originals.
- Windows Credential Locker: temporary synthetic entry save/load/delete (Windows only).
- Source GUI: actual screenshot capture after analyze and unlock, using synthetic fixtures only.
- Installed Windows EXE: actual mouse/keyboard input, batch confirmation, five-PDF run, three decrypted outputs rechecked with bundled qpdf, unchanged originals, password-free report and clean close.
- Installer: silent install, Desktop/Start Menu shortcut targets and icons, EXE/installer/uninstaller icon extraction, uninstall.

## Verified Windows result — 2026-10-17

[Successful run 39014860198](https://github.com/ruhulaminrevens/RAR-PDF-Batch-Unlocker/actions/runs/39014860198) built commit `1af596b40d3bd0b5e439d7e78f5eab379e9e8889`.

| Gate | Actual result |
| --- | --- |
| Automated tests | **23 passed, zero skipped**, Windows Python 3.12 |
| Real qpdf | Official 12.4.2 x64, archive hash checked |
| Source GUI | Analyze, group mapping, unlock and screenshot scenarios passed |
| Installed EXE | Real mouse/keyboard entry and confirmation; five synthetic PDFs processed |
| Installed batch | **3 Unlocked, 1 PasswordNotMatched, 1 SkippedUnencrypted** |
| Output verification | All three outputs rechecked as unencrypted by bundled qpdf |
| Original preservation | Source hashes unchanged |
| Report privacy | Synthetic password absent from CSV |
| Windows vault | Synthetic save/load/delete round trip passed |
| Icons | EXE, installer and uninstaller resource pixels match the committed 32px icon exactly |
| Native titlebar | Branded icon reviewed in the actual installed-window screenshot |
| EXE details | Product name and 1.1.0 file version verified |
| Shortcuts | Desktop and Start Menu targets and icon locations verified |
| Installation/uninstallation | Both passed |
| Screenshots | Actual Windows pixels reviewed; only synthetic data |

Machine-readable results and the test transcript are in [docs/validation](validation/). The first two attempts exposed CI automation issues (desktop dimensions and ordered text input); both were corrected before the successful run. No release was published from either failed run.

Release policy: the publisher downloads the installer from this successful run, verifies its recorded SHA-256 and validated source SHA, permits only documentation/workflow changes since that source, and creates a new release. It never replaces an existing release or asset.

## Remaining manual coverage

Automated fixture tests do not cover all real-world PDFs, every Windows scaling/display configuration, SmartScreen reputation or third-party antivirus. Optional vault tests cover a synthetic credential, not migration of existing user entries. Installer remains unsigned. Never use user bank statements in repository screenshots.
