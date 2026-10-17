# Screenshot Guide / Screenshots সংগ্রহের নির্দেশনা

> **Status:** Real application screenshots are not yet uploaded. GitHub Actions confirmed the packaged GUI launches, but the installed application still needs hands-on Windows QA. Do not treat placeholders, the GitHub repository page, or concept mockups as actual application screenshots.

## Required captures

| Suggested filename | What to capture | Screenshot preparation |
| --- | --- | --- |
| `docs/screenshots/main-window.png` | RAR PDF Batch Unlocker main window, source/output fields, qpdf path | Use example folder paths only |
| `docs/screenshots/security-analysis.png` | Analyzer results with `Unencrypted`, `PasswordRequired`, etc. | Use sample PDF filenames |
| `docs/screenshots/password-groups.png` | Masked password field and Bank/Office/General groups | Never include real passwords or unmasked input |
| `docs/screenshots/batch-results.png` | Progress bar, result table, success / failed statuses | Test on synthetic PDFs; crop/redact personal paths |
| `docs/screenshots/installer.png` | Published Windows setup wizard | Show authentic installed release |
| `docs/screenshots/release-download.png` | GitHub Releases page with v1.0.0 setup asset | Public repository page only |

## Screenshot workflow (no command line)

1. Install the EXE from the **[verified v1.0.0 release](https://github.com/ruhulaminrevens/RAR-PDF-Batch-Unlocker/releases/tag/v1.0.0)**.
2. Launch the app from Start Menu or Desktop shortcut.
3. Use **only synthetic PDFs or documents without personal data** for screenshot demonstrations.
4. Capture each UI state with Windows **Win + Shift + S**.
5. Inspect images for confidential paths, usernames, bank/account/identity details, tokens and real passwords.
6. Upload images to `docs/screenshots/` and link them from `README.md`.

## README gallery template (add only when files exist)

```md
### Application screenshots
![Main workspace](docs/screenshots/main-window.png)
![Security analysis results](docs/screenshots/security-analysis.png)
![Password groups](docs/screenshots/password-groups.png)
![Batch progress and CSV report](docs/screenshots/batch-results.png)
![Windows installer](docs/screenshots/installer.png)
```

## Manual Windows QA checklist

- [ ] Install unsigned EXE on a clean Windows 10/11 x64 machine
- [ ] Launch GUI without Python/PowerShell/qpdf installed separately
- [ ] Verify bundled qpdf path resolves
- [ ] Analyze security on unencrypted / known-password / unknown-password PDFs
- [ ] Unlock known-password PDF(s) to a separate folder
- [ ] Confirm outputs are unencrypted and originals preserved
- [ ] Test failed-only CSV retry and output-skip behavior
- [ ] Check optional Credential Locker (vault) only if intentionally enabled
- [ ] Capture screenshots using only non-sensitive samples
- [ ] Verify installer uninstall and shortcut cleanup

**Reminder:** Screenshots and test evidence must be real. Do not label untested controls or simulated outputs as validated behavior.
