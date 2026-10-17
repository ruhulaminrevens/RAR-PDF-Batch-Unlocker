# RAR PDF Batch Unlocker

**Offline Windows PDF Security Analyzer & Multi-Password Batch Unlocker**  
**Windows 10/11 (64-bit) · GUI application · qpdf-based · Bangla + English Guide**

[![Windows Installer Build](https://github.com/ruhulaminrevens/RAR-PDF-Batch-Unlocker/actions/workflows/windows-release.yml/badge.svg)](https://github.com/ruhulaminrevens/RAR-PDF-Batch-Unlocker/actions/workflows/windows-release.yml)
[![Latest release](https://img.shields.io/github/v/release/ruhulaminrevens/RAR-PDF-Batch-Unlocker?label=Latest%20Release)](https://github.com/ruhulaminrevens/RAR-PDF-Batch-Unlocker/releases/latest)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11%20x64-0078D4)](#system-requirements)
[![Engine](https://img.shields.io/badge/PDF%20Engine-qpdf-4763B0)](https://github.com/qpdf/qpdf)

> **বাংলায় সংক্ষেপে:** নিজের PC-তে, internet বা online upload ছাড়াই, একাধিক password-protected PDF scan, analyze এবং আপনার জানা passwords দিয়ে batch unlock করুন। Unknown-password PDFs-এর আলাদা report পাওয়া যাবে। Originals overwrite করা হয় না।

## Download & install

**[Download RAR PDF Batch Unlocker v1.1.0 — Windows Setup EXE](https://github.com/ruhulaminrevens/RAR-PDF-Batch-Unlocker/releases/download/v1.1.0/RAR-PDF-Batch-Unlocker-Setup.exe)**

[Release notes](https://github.com/ruhulaminrevens/RAR-PDF-Batch-Unlocker/releases/tag/v1.1.0) · [SHA-256 checksum](https://github.com/ruhulaminrevens/RAR-PDF-Batch-Unlocker/releases/download/v1.1.0/SHA256SUMS.txt) · [Previous v1.0.0](https://github.com/ruhulaminrevens/RAR-PDF-Batch-Unlocker/releases/tag/v1.0.0)

1. Setup EXE download করে install করুন। Python, PowerShell বা qpdf আলাদাভাবে install করতে হবে না।
2. Desktop / Start Menu থেকে app খুলুন → **Batch workspace**-এ Source ও Output folder দিন।
3. **Analyze security** চালিয়ে **Passwords** section-এ জানা password add করুন।
4. **Run settings**-এ প্রথমে 5-file limit দিয়ে test করুন → **Unlock batch**।
5. **Results & reports**-এ result, CSV এবং failed-only retry পাবেন।

**Unsigned installer:** Windows SmartScreen warning আসতে পারে। Download source ও SHA-256 মিলিয়ে নিন। v1.0.0-এর release এবং installer অপরিবর্তিত আছে।

### Modern workspace, existing engine

Navy / cyan / violet interface, persistent sidebar, scrollable pages, real progress and timing, searchable results, masked password controls এবং consistent Windows branding। `core.py` ও `vault.py` আগের working baseline থেকে অপরিবর্তিত।

![Actual installed Windows app after synthetic batch processing](docs/screenshots/installed-window.png)

### Windows validation

[Successful Windows run](https://github.com/ruhulaminrevens/RAR-PDF-Batch-Unlocker/actions/runs/39014860198) · [Full validation record](docs/REDESIGN_VALIDATION.md) · [Screenshot provenance](docs/SCREENSHOTS.md)

| Check | Result |
| --- | --- |
| Automated tests | **23 passed; zero skipped** |
| Actual installed-GUI batch | **5 PDFs: 3 unlocked, 1 no password match, 1 already unencrypted** |
| Original files / CSV privacy | Hashes unchanged; supplied password absent from report |
| Bundled qpdf / decrypted outputs | 12.4.2 archive checked; outputs verified unencrypted |
| Windows vault | Synthetic save/load/delete passed |
| Icons & EXE metadata | EXE/installer/uninstaller icons match; product/version metadata verified |
| Desktop / Start Menu shortcuts | Targets and icon paths verified |
| Install / uninstall | Passed on Windows CI |

The final installer is promoted from the validated build **without rebuilding it**. Your own Windows 10/11 display scaling, antivirus behavior and representative documents remain machine-specific checks; no large-batch benchmark is claimed.

### More real screenshots

<details>
<summary>Password groups, results, settings and installer</summary>

![Masked password groups and folder mappings](docs/screenshots/password-groups.png)
![Actual qpdf batch results](docs/screenshots/batch-results.png)
![Run settings](docs/screenshots/run-settings.png)
![Actual Windows installer wizard](docs/screenshots/installer.png)

</details>

## ✨ Key features

| Feature | কী কাজ করে |
| --- | --- |
| **100% local PDF workflow** | কোনো PDF online service-এ upload করার প্রয়োজন নেই |
| **Recursive folder scan** | Selected folder ও subfolders-এর সব `.pdf` detect করে; full file limit `0` |
| **Security Analyzer** | `Unencrypted`, `PasswordRequired`, `PermissionRestricted`, `InvalidPDF` / inspection issues classify করে |
| **Multi-password matching** | Session-এর known passwords একে একে চেষ্টা করে; default maximum 30 attempts per PDF |
| **Password groups** | General / Bank / Office ইত্যাদি group; folder-based mapping সম্ভব |
| **Masked password entry** | UI-তে password masked থাকে; password values CSV report-এ লেখা হয় না |
| **Optional Windows vault** | Explicitly save/load/delete করলে OS-backed `keyring` ব্যবহার করে; default session-only |
| **Dry Run** | File count/list preview; PDF unlock / password testing করে না |
| **Analyze security** | Password না দিয়েও security state inspect করা যায়; unlocked PDFs তৈরি করে না |
| **Progress + filtering** | File count, status, attempts, elapsed time এবং filterable result table |
| **Failed-only retry** | Previous CSV-এর failed entries আবার process করতে পারে |
| **CSV report** | Output folder-এ timestamped CSV; relative paths default |
| **Protected output** | Existing outputs skip; unlocked output encrypted রয়ে গেছে কি না verify করে |
| **Safe stop** | Stop button current attempt শেষ হওয়ার পরে থামার চেষ্টা করে |
| **Optional copy unencrypted** | Tick করলে unprotected PDFs-এর copy-ও output-এ রাখতে পারে |

**Important:** Strong unknown *opening passwords* qpdf দিয়ে magically bypass করা যায় না; এই tool brute-force password cracking করে না।

## 🚀 Complete GUI usage guide

### Step 1 — Folder preparation

Source আর Output আলাদা, একে অপরের ভেতরে নয়:

```text
D:\PDF Archive\
  Bank Statements\statement1.pdf
  Office Documents\report.pdf
  Personal\document.pdf

D:\PDF UNLOCKED\     (separate output location)
```

Source/Output nested হলে app safety check error দেবে। Original PDF-এর backup রাখুন।

### Step 2 — Scan filenames

1. **Source** browse করে folder select করুন।
2. **Output** browse করে অন্য folder select করুন।
3. **Scan filenames** চাপুন → PDF count দেখাবে; files modify হবে না।
4. **File limit:** `5` দিলে প্রথম 5টি, `0` দিলে সব।

### Step 3 — Analyze security (recommended first)

1. **Analyze security** চাপুন।
2. Sidebar-এর **Results & reports**-এ PDF-by-PDF status দেখুন।
3. `PasswordRequired` হলে opening password প্রয়োজন; `PermissionRestricted` সাধারণত permission/restriction-only protection।
4. Output folder-এ CSV report তৈরি হয়; PDF copy/unlock করা হয় না। **Dry run** enabled থাকলে শুধু file list হয়, CSV-ও তৈরি হয় না।

### Step 4 — Add known passwords

1. Sidebar থেকে **Passwords** খুলুন। **Group: General** রেখে পরিচিত password লিখুন → **Add to group**।
2. আলাদা issuer/department-specific password হলে **New group** বানান (e.g. `Bank`, `Office`)।
3. নিচের **Folder-to-group mapping**-এ প্রতি লাইনে `relative/folder=Group Name` লিখুন:

```text
Bank Statements=Bank
Office Documents=Office
```

4. General passwords সব group-এ চেষ্টা করা হয়; folder-specific group আগে চেষ্টা করা হয়। Duplicate passwords পুনরায় try করা হয় না।
5. **Max password attempts per PDF** যুক্তিযুক্তভাবে সেট করুন (default: 30, blank password trial অন্তর্ভুক্ত)।

**Password privacy:** অন্য কারও password বা real credentials GitHub Issues, screenshot বা CSV-এ দেবেন না। Session password application বন্ধ করলে clear হয়; Windows vault কেবল explicit request-এ ব্যবহার করুন।

### Step 5 — Start a safe 5-file batch

1. Sidebar-এর **Run settings** খুলে **File limit = 5** দিন।
2. **Dry run** tick করে preview করুন; তারপর untick করুন।
3. **Unlock batch** click করে confirmation দিন।
4. Progress/status পর্যবেক্ষণ করুন; output copy create হলে খুলে যাচাই করুন।
5. সব ঠিক থাকলে **File limit = 0** দিয়ে full batch চালান। Original PDFs overwrite হয় না।

### Step 6 — Review results / retry failures

Output folder-এ `unlock-report-YYYYMMDD-HHMMSS-ffffff.csv` ফাইল পাবেন। রিপোর্টে `source`, `destination`, `status`, `details`, `attempts`, `elapsed_seconds`, `security`, `group` থাকে।

- `Unlocked`: decrypted copy created and checked
- `SkippedExisting`: destination exists; app does not overwrite it
- `SkippedUnencrypted`: source PDF already unencrypted
- `CopiedUnencrypted`: unencrypted PDF copied because option enabled
- `PasswordNotMatched`: supplied passwords did not match
- `PasswordRequired`: opening password needed (analyzer)
- `PermissionRestricted`: restrictions-based encryption observed
- `InvalidPDF` / `InspectionFailed`: PDF parse/inspection problem
- `Timeout` / `Error`: processing issue

**Retry only failed:** **Retry failures from last report**, অথবা **Choose CSV** দিয়ে পূর্বের report select করুন; তারপর **Unlock batch**। নতুন known passwords থাকলে যোগ করুন। শুধু failed statuses retry হবে।

## 🔐 Unknown passwords: safe recovery guide

- **Bank / Credit Card:** Statement email-এর documented password instructions, official bank/issuer portal বা bank support থেকে password format খুঁজুন।
- **Office / Accounting:** Document author, approved password manager, finance records administrator বা existing backups।
- **Personal / Government:** Issuing portal, delivery letter/email, official helpdesk, verified owner records।
- **Other PDFs:** Original sender, unencrypted copy, old backup, own password manager।
- Strong unknown opening-password PDF-এর recovery guaranteed নয়। “Unlock without password” দাবি করা random online site-এ sensitive PDFs upload করবেন না।

## ⚙️ Advanced controls

| Setting | Default / meaning |
| --- | --- |
| `File limit` | `0` means all PDFs |
| `Max password attempts per PDF` | `30` including blank |
| `Dry run` | File scan only, no qpdf attempts |
| `Copy unencrypted` | Off by default |
| `Relative file paths in reports` | On by default |
| `Retry CSV` | Optional previous report file |
| `Stop safely` | Attempts stop after current qpdf call, not immediate forced termination |

Optional vault requires a supported Windows Credential Locker backend. For sensitive files, store unlocked output in an access-controlled location (e.g. encrypted drive) and follow organizational policy.

## 🧩 Source code & architecture

| Path | Purpose |
| --- | --- |
| [`app.py`](app.py) | Existing application controller, password groups, worker/event handling and safe stop |
| [`ui.py`](ui.py) | Dark Tk/ttk layout, sidebar, settings, results and accessible scrolling |
| [`branding.py`](branding.py), [`assets/`](assets/) | App identity, resource lookup, DPI setup and multi-size icons |
| [`core.py`](core.py) | qpdf subprocess, security analysis, path validation, batch processing, CSV reports |
| [`vault.py`](vault.py) | Optional Windows Credential Locker integration via `keyring` |
| [`tests/`](tests/) | Engine, GUI, branding, actual qpdf and Windows vault tests |
| [`scripts/`](scripts/) | Reproducible icons, packaging, synthetic fixtures, real screenshots and installed-GUI QA |
| [`requirements-build.txt`](requirements-build.txt) | PyInstaller and keyring build dependencies |
| [`build-windows.bat`](build-windows.bat) | Local developer build helper |
| [`installer/setup.iss`](installer/setup.iss) | Inno Setup installer recipe |
| [`.github/workflows/windows-release.yml`](.github/workflows/windows-release.yml) | Windows CI build, smoke test and release publication |
| [`docs/SCREENSHOTS.md`](docs/SCREENSHOTS.md) | Actual screenshots capture checklist |

**Processing flow:** Choose folders → Scan → Security classify → Select candidate passwords → qpdf decrypt into temporary file → Verify no encryption → Save separate output (no overwrite) → CSV report → Retry if needed.

## 🛠️ Build from source (developers only)

End users can **ignore this section**. On Windows with Python 3.10+, optional dependencies and installed qpdf:

```powershell
python -m pip install -r requirements-build.txt -r requirements-test.txt
python -m unittest discover -s tests -v
python app.py
```

Run [GitHub Actions → Windows validation and installer](https://github.com/ruhulaminrevens/RAR-PDF-Batch-Unlocker/actions/workflows/windows-release.yml) manually on `main`, or push a code change. The pipeline installs pinned top-level dependencies, verifies the official qpdf 12.4.2 archive SHA-256, tests the real GUI/engine/vault, builds the branded installer, installs it, exercises a synthetic batch through its GUI, captures screenshots, verifies shortcuts, and uninstalls it.

**Validation runs do not publish releases.** Download the installer and QA evidence from the successful Actions run. A new release is intentional: the separate publisher runs only on a `release/v1.*` branch, verifies its declared successful Windows run and unchanged application source, then promotes that exact artifact. Existing release assets must never be replaced. See [validation evidence](docs/REDESIGN_VALIDATION.md).

Local packaging uses `build-windows.bat` and the same `scripts/build_windows.ps1` as CI. For icon changes, run `python scripts/generate_branding.py`, commit the generated assets and verify them at small sizes. For source screenshots, run `python scripts/capture_screenshots.py` on a desktop with qpdf available; it uses synthetic PDFs only.

## 🩺 Troubleshooting / FAQ

| Problem | What to check |
| --- | --- |
| Installer download says 404 | Open [Releases](https://github.com/ruhulaminrevens/RAR-PDF-Batch-Unlocker/releases), confirm real asset; use tagged link above |
| Windows SmartScreen prompt | Installer unsigned. Verify GitHub source/hash; do not ignore warning for files from other sources |
| qpdf.exe not detected | Choose bundled `qpdf\bin\qpdf.exe` inside install directory, or reinstall |
| `PasswordNotMatched` | Passwords incorrect/unknown; check official issuer instructions, group mapping and attempt limit |
| Some files `SkippedExisting` | Output path already has those filenames; original output was not overwritten |
| Analyzer returns `InvalidPDF` | Verify PDF opens elsewhere; file may be damaged or unsupported |
| Report contains filenames | By design, CSV includes relative filenames; keep report confidential |
| Unknown password PDF still locked | Expected unless known password matches; qpdf cannot bypass strong encryption |
| Windows vault error | Confirm Windows credential backend and use session-only passwords as fallback |
| Batch takes time | Depends on PDF count, size, number of candidates, storage performance; ETA is an estimate based on completed files |
| Windows still shows an old shortcut icon | Close the app and reopen from the newly installed shortcut. Windows can cache icons; sign out/in if necessary. Do not delete system icon-cache files automatically |

## 🛡️ Security, compatibility & limitations

- Use only on PDFs you own or are authorized to process.
- qpdf passwords go via standard input, not CLI arguments; CSV reports exclude passwords.
- Original files are not intentionally modified. The output is a **separate unencrypted copy**, so secure it properly.
- Unlocking or regenerating a digitally signed PDF may invalidate its signature; retain the signed original.
- Some malformed or unusual PDFs may fail verification; check report before deleting any originals.
- `PasswordNotMatched` is **not** proof the file is unrecoverable—only that the supplied candidates did not match.
- The current build is unsigned and not certified for every enterprise endpoint.
- Automated Windows installation, actual installed-GUI fixture processing, screenshots, vault and uninstall passed. User-machine QA, large real-document benchmarks and an independent security audit are not claimed.

## 📌 Project status and next improvements

**Completed:** modern dark GUI, consistent Windows branding, existing qpdf engine and password features retained, real Windows screenshots, 23 passing tests, installed-GUI synthetic batch, shortcut/icon checks and uninstall validation.

**Next on your PC:** install v1.1.0, select a small representative five-file batch, verify output readability and confirm your preferred Windows scaling. Keep original PDFs. Signing and large-batch benchmarking are future work.

### Support and contribution

Use [Issues](https://github.com/ruhulaminrevens/RAR-PDF-Batch-Unlocker/issues) for bugs and suggestions. Include app version, Windows version, precise reproduction steps and **redacted** output; never attach confidential PDFs or actual passwords.

---

**Maintainer:** [ruhulaminrevens](https://github.com/ruhulaminrevens) · **Project:** RAR PDF Batch Unlocker  
**Documentation:** বাংলা + English · Last updated: 2026-10-17
