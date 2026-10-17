# RAR PDF Batch Unlocker

**Goal:** Offline Windows 10/11 PDF unlocker with a polished GUI, multi-password processing, security analysis, progress, failed-file retry and privacy-safe CSV reporting.

## Current status
The baseline source archive, installer recipe, Windows Actions workflow and tests have been prepared. **A Windows EXE has not yet been built or verified, and a GitHub Release asset does not yet exist.** Do not present an installer link as active before a successful build.

## Intended usage (once installer is verified)
1. Download the EXE installer from [GitHub Releases](https://github.com/ruhulaminrevens/RAR-PDF-Batch-Unlocker/releases).
2. Run the installer; bundled qpdf means no PowerShell/Python installation is needed.
3. Select separate Source and Output folders.
4. Analyze security. Add known passwords in masked groups.
5. Test five PDFs first, then run full batch. Review CSV results and retry failed records.

### Scope and safeguards
- Source PDFs preserved, already-existing output skipped; output PDF encryption verified.
- No password values are written to CSV; optional vault is opt-in.
- Unknown strong PDF opening passwords cannot be bypassed by qpdf.
- Avoid publishing bank records, identity documents, personal filenames or passwords.
- Unsigned installers may show SmartScreen warnings; publisher signing requires a code signing certificate.

## Build and publishing
Full source must be committed before activating the Windows build workflow. The workflow compiles a PyInstaller onedir build, bundles official qpdf Windows binaries, runs tests, packages with Inno Setup and uploads an installer artifact. A release should only be published after verifying that the workflow succeeded.

**Direct installer URL after publication (currently not verified):**
https://github.com/ruhulaminrevens/RAR-PDF-Batch-Unlocker/releases/latest/download/RAR-PDF-Batch-Unlocker-Setup.exe

## Project
The prepared source bundle contains: `app.py`, `core.py`, `vault.py`, `tests/test_core.py`, `requirements-build.txt`, `installer/setup.iss`, `.github/workflows/windows-release.yml`, and documentation. Windows binary smoke testing and screenshot capture are outstanding.
