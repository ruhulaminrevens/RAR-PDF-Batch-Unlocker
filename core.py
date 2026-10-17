"""Offline PDF analysis and guarded qpdf operations; Python 3.10+.

Safety contract (kept from 1.0/1.1, hardened in 1.2):
* passwords travel to qpdf only through stdin, never argv, environment, logs or reports;
* originals are opened read-only and never written;
* output is written to a same-folder temporary file, verified with ``qpdf --check``
  and only then published with an atomic, no-replace rename, so an interrupted
  write can never leave a file that a later run would accept as finished output.
"""
from __future__ import annotations

import concurrent.futures as cf
import csv
from dataclasses import dataclass, field
from datetime import datetime
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import threading
import time
import uuid

FIELDS = ['source', 'destination', 'status', 'details', 'attempts', 'elapsed_seconds',
          'security', 'group', 'size_bytes', 'warnings']
SUCCESS = {'Unlocked', 'CopiedUnencrypted'}
SKIPPED = {'SkippedExisting', 'SkippedUnencrypted', 'DryRun'}
ANALYSIS = {'Unencrypted', 'PasswordRequired', 'PermissionRestricted'}
FAILED = {'PasswordNotMatched', 'PasswordRequired', 'InvalidPDF', 'InspectionFailed', 'Timeout',
          'Error', 'Cancelled', 'VerificationFailed', 'DecryptFailed', 'FileLocked', 'AccessDenied',
          'DiskFull', 'PathTooLong', 'SourceMissing', 'OutputConflict'}
# Rows with these states need no more work when a run is resumed.
DONE_FOR_RESUME = SUCCESS | {'SkippedExisting', 'SkippedUnencrypted'}
TEMP_MARK = '.rar-partial-'
LEGACY_TEMP_MARK = '.rar-part-'
FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r')

ACTIONS = {
    'Unlocked': 'Done. The verified copy is in the output folder.',
    'CopiedUnencrypted': 'Done. The file had no protection and was copied unchanged.',
    'SkippedExisting': 'An output with this name already exists. Move or rename it to process the file again.',
    'SkippedUnencrypted': 'No password protection. Turn on “Copy already unencrypted PDFs” to copy it.',
    'PasswordNotMatched': 'None of the supplied passwords opened it. Add the correct password, then retry failed files.',
    'PasswordRequired': 'Needs an opening password. Add it on the Passwords page, then unlock.',
    'PermissionRestricted': 'Opens without a password but has usage restrictions; unlocking removes them.',
    'Unencrypted': 'No password protection.',
    'InvalidPDF': 'qpdf could not read this file as a PDF. It may be damaged, incomplete or not a PDF.',
    'InspectionFailed': 'qpdf could not determine the protection. Open the file in a PDF viewer to check it.',
    'DecryptFailed': 'The password was accepted but qpdf could not rebuild the file (likely damage).',
    'VerificationFailed': 'The rebuilt copy failed the qpdf check and was discarded. The original is unchanged.',
    'Timeout': 'qpdf took longer than the timeout. Raise the timeout in Run settings for very large files.',
    'Cancelled': 'Stopped by you before this file finished. Retry or resume to continue.',
    'FileLocked': 'Another program has the file open. Close it (for example a PDF viewer), then retry.',
    'AccessDenied': 'Windows denied access. Check folder permissions and the read-only attribute.',
    'DiskFull': 'The output drive ran out of space. Free space, then resume or retry.',
    'PathTooLong': 'The path is too long for Windows. Choose a shorter output folder or shorten folder names.',
    'SourceMissing': 'The file was moved or deleted during the run.',
    'OutputConflict': 'Another selected file maps to the same output name; this one was not written.',
    'DryRun': 'Dry run: nothing was opened or written.',
    'Error': 'Unexpected error. See details, then retry.',
}


class Cancelled(Exception):
    """Raised when the user stops a run while qpdf is running."""


class StopBatch(Exception):
    """A condition that makes every later file fail too (for example a full disk)."""


@dataclass
class Settings:
    source: Path | None
    destination: Path
    qpdf: str
    passwords: list[str]
    limit: int = 0
    dry_run: bool = False
    timeout: int = 60
    analyze_only: bool = False
    failed_report: str = ''
    password_groups: dict[str, list[str]] = field(default_factory=dict)
    folder_groups: dict[str, str] = field(default_factory=dict)
    max_attempts: int = 30
    relative_reports: bool = True
    include_unencrypted: bool = False
    issuer_hints: bool = False
    inputs: list[Path] = field(default_factory=list)
    resume_report: str = ''
    workers: int = 1
    html_summary: bool = True
    app_version: str = ''


@dataclass
class Plan:
    base: Path | None
    destination: Path
    files: list[Path]
    relative: dict[Path, str]
    rejected: list[tuple[str, str]] = field(default_factory=list)
    duplicates: int = 0
    ignored_other: int = 0
    total_bytes: int = 0
    existing_outputs: int = 0
    fingerprint: str = ''
    folders: int = 0

    def __iter__(self):  # backwards compatible ``src, dst, files = scan(...)``
        return iter((self.base, self.destination, self.files))


# ---------------------------------------------------------------- paths

def _key(path) -> str:
    return os.path.normcase(str(path))


def fs(path) -> str:
    """Windows extended-length form for long paths; plain string elsewhere."""
    text = str(path)
    if sys.platform == 'win32' and len(text) >= 240 and not text.startswith('\\\\?\\'):
        text = os.path.abspath(text)
        return '\\\\?\\UNC\\' + text[2:] if text.startswith('\\\\') else '\\\\?\\' + text
    return text


def _is_link_dir(entry: os.DirEntry) -> bool:
    try:
        if entry.is_symlink() or getattr(entry, 'is_junction', lambda: False)():
            return True
        if sys.platform == 'win32':
            st = entry.stat(follow_symlinks=False)
            # Mount points and directory symlinks; cloud placeholders are left alone.
            tag = getattr(st, 'st_reparse_tag', 0)
            return bool(getattr(st, 'st_file_attributes', 0) & 0x400) and tag in (0xA0000003, 0xA000000C)
    except OSError:
        return True
    return False


def _walk(folder: Path, plan_rejected: list, counter: dict):
    """Yield PDFs below *folder* without following links or junctions."""
    stack = [folder]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(fs(current)) as it:
                entries = sorted(it, key=lambda e: e.name.casefold())
        except OSError as exc:
            plan_rejected.append((str(current), f'Folder not readable ({type(exc).__name__})'))
            continue
        for entry in entries:
            path = current / entry.name
            try:
                if _is_link_dir(entry):
                    plan_rejected.append((str(path), 'Link or junction not followed'))
                    continue
                if entry.is_dir(follow_symlinks=False):
                    stack.append(path)
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
            except OSError:
                plan_rejected.append((str(path), 'Not readable'))
                continue
            if TEMP_MARK in entry.name or LEGACY_TEMP_MARK in entry.name:
                continue
            if path.suffix.lower() == '.pdf':
                yield path
            else:
                counter['other'] += 1


def _resolve_inputs(settings: Settings) -> list[Path]:
    items = list(settings.inputs or [])
    if settings.source:
        items.insert(0, settings.source)
    if not items:
        raise ValueError('Choose a source folder or add PDF files.')
    resolved = []
    for item in items:
        try:
            path = Path(item).expanduser().resolve(strict=True)
        except (OSError, RuntimeError):
            raise ValueError(f'Input not found: {item}') from None
        if not (path.is_dir() or path.is_file()):
            raise ValueError(f'Input is not a file or folder: {item}')
        resolved.append(path)
    return resolved


def _base_for(items: list[Path]) -> Path | None:
    parents = [p if p.is_dir() else p.parent for p in items]
    try:
        return Path(os.path.commonpath([str(p) for p in parents]))
    except ValueError:  # different drives
        return None


def relative_name(path: Path, base: Path | None) -> str:
    if base is not None:
        return path.relative_to(base).as_posix()
    drive = path.drive.rstrip(':\\/') or 'root'
    return (Path(drive.replace('\\', '_')) / path.relative_to(path.anchor)).as_posix()


def validate_paths(settings: Settings):
    items = _resolve_inputs(settings)
    if not str(settings.destination).strip():
        raise ValueError('Choose an output folder.')
    dst = Path(settings.destination).expanduser().resolve(strict=False)
    if dst.exists() and not dst.is_dir():
        raise ValueError('The output location is a file. Choose a folder.')
    for item in items:
        folder = item if item.is_dir() else item.parent
        if item.is_dir() and (_key(item) == _key(dst) or item in dst.parents or dst in item.parents):
            raise ValueError('Source and output must be separate, non-nested folders.')
        if item.is_file() and (_key(folder) == _key(dst) or dst in item.parents):
            raise ValueError('Choose an output folder that is not the folder of a selected PDF.')
    if not Path(settings.qpdf).is_file() and not shutil.which(settings.qpdf):
        raise ValueError('qpdf executable not found. Select qpdf.exe or add it to PATH.')
    if not 0 <= settings.limit <= 1000000 or not 1 <= settings.max_attempts <= 1000:
        raise ValueError('Invalid limit or maximum attempts.')
    if settings.timeout < 1 or settings.timeout > 3600:
        raise ValueError('Invalid timeout.')
    if not 1 <= settings.workers <= 16:
        raise ValueError('Parallel workers must be between 1 and 16.')
    return items, dst


def fingerprint(items: list[Path]) -> str:
    joined = '\n'.join(sorted(_key(p) for p in items))
    return hashlib.sha256(joined.encode('utf-8')).hexdigest()


def plan(settings: Settings) -> Plan:
    items, dst = validate_paths(settings)
    rejected: list[tuple[str, str]] = []
    counter = {'other': 0}
    seen: dict[str, Path] = {}
    duplicates = 0
    folders = 0
    for item in items:
        if item.is_dir():
            folders += 1
            found = _walk(item, rejected, counter)
        elif item.suffix.lower() != '.pdf':
            rejected.append((str(item), 'Unsupported file type (only .pdf)'))
            continue
        elif Path(item).is_symlink():
            rejected.append((str(item), 'Link not followed'))
            continue
        else:
            found = [item]
        for path in found:
            k = _key(path)
            if k in seen:
                duplicates += 1
            else:
                seen[k] = path
    base = _base_for(items)
    files = sorted(seen.values(), key=lambda p: str(p).casefold())
    relative = {p: relative_name(p, base) for p in files}
    previous = _previous_rows(settings, relative)
    if previous is not None:
        files = [p for p in files if previous(p)]
    # Two inputs that map to one output name (case-insensitive on Windows).
    owners: dict[str, Path] = {}
    unique = []
    for p in files:
        k = relative[p].casefold()
        if k in owners:
            rejected.append((str(p), 'OutputConflict: same output name as ' + relative[owners[k]]))
        else:
            owners[k] = p
            unique.append(p)
    files = unique[:settings.limit] if settings.limit else unique
    total = 0
    existing = 0
    for p in files:
        try:
            total += p.stat().st_size
        except OSError:
            pass
        if (dst / relative[p]).exists():
            existing += 1
    return Plan(base, dst, files, relative, rejected, duplicates, counter['other'], total, existing,
                fingerprint(items), folders)


def scan(settings: Settings):
    return plan(settings)


# ---------------------------------------------------------------- previous reports

def read_report_rows(csvpath: str) -> list[dict]:
    with open(csvpath, newline='', encoding='utf-8-sig') as fh:
        reader = csv.DictReader(fh)
        if not {'source', 'status'}.issubset(reader.fieldnames or []):
            raise ValueError('The report lacks the required CSV columns (source, status).')
        rows = []
        for row in reader:
            if not row.get('source') or not row.get('status'):
                continue  # incomplete last line after a crash
            rows.append({k: unescape_cell(v or '') for k, v in row.items() if k})
        return rows


def run_record_for(csvpath: str) -> dict | None:
    path = Path(csvpath)
    stamp = path.stem.replace('unlock-report-', '')
    candidate = path.with_name(f'unlock-run-{stamp}.json')
    if candidate.is_file():
        try:
            return json.loads(candidate.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return None
    return None


def _previous_rows(settings: Settings, relative: dict[Path, str]):
    """Return a predicate selecting files for retry/resume, or None for a normal run."""
    report = settings.resume_report or settings.failed_report
    if not report:
        return None
    rows = read_report_rows(report)
    record = run_record_for(report)
    items = _resolve_inputs(settings)
    if record and record.get('input_fingerprint') not in (None, fingerprint(items)):
        raise ValueError('This report belongs to a different source selection. Select the same folder or files as that run.')
    by_rel: dict[str, str] = {}
    any_failed: set[str] = set()
    base = _base_for(items)
    for row in rows:
        source = row['source']
        p = Path(source)
        if p.is_absolute():
            try:
                rel = relative_name(p.resolve(), base)
            except ValueError:
                continue
        else:
            rel = Path(source.replace('\\', '/')).as_posix()
            if rel.startswith('../') or '/../' in rel or rel == '..':
                continue
        by_rel[rel.casefold()] = row['status']
        if row['status'] in FAILED:
            any_failed.add(rel.casefold())
    if settings.resume_report:
        if record is None:
            raise ValueError('Resume needs the unlock-run JSON created with the report. Use “Retry failed” for older reports.')

        def wanted(p: Path):
            status = by_rel.get(relative[p].casefold())
            if status in DONE_FOR_RESUME:
                if status in SUCCESS and not (settings.destination / relative[p]).is_file():
                    return True  # output removed since; do it again
                return False
            return True
        return wanted
    return lambda p: relative[p].casefold() in any_failed


# ---------------------------------------------------------------- qpdf

@dataclass
class QpdfResult:
    returncode: int
    stdout: bytes = b''
    stderr: bytes = b''


def run_qpdf(qpdf: str, args: list[str], password: str | None = None, timeout: int = 60,
             stop: threading.Event | None = None):
    """Run qpdf. A supplied password goes through stdin only; Stop kills the process."""
    data = None if password is None else (password + '\n').encode('utf-8')
    proc = subprocess.Popen([qpdf, *args], stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    deadline = time.monotonic() + timeout
    first = True
    while True:
        try:
            out, err = proc.communicate(input=data if first else None, timeout=0.15)
            return QpdfResult(proc.returncode, out or b'', err or b'')
        except subprocess.TimeoutExpired:
            first = False
            if stop is not None and stop.is_set():
                proc.kill(); proc.communicate()
                raise Cancelled()
            if time.monotonic() >= deadline:
                proc.kill(); proc.communicate()
                raise subprocess.TimeoutExpired([qpdf, *args], timeout)


def qpdf_message(stderr: bytes) -> str:
    """Last qpdf error line without the file path (paths stay out of messages)."""
    lines = [l.strip() for l in stderr.decode('utf-8', 'replace').splitlines() if l.strip()]
    for line in reversed(lines):
        if line.startswith('qpdf:') or line.startswith('WARNING:'):
            text = line.split(':', 1)[1].strip()
            # "<path>: message" or "<path> (object 1 0, offset 9): message"
            parts = text.rsplit('): ', 1) if '): ' in text else text.split(': ', 1)
            return (parts[-1] if len(parts) > 1 else text)[:200]
    return (lines[-1][:200] if lines else '')


def qpdf_version(qpdf: str) -> str:
    try:
        r = subprocess.run([qpdf, '--version'], capture_output=True, timeout=20,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return r.stdout.decode('utf-8', 'replace').splitlines()[0].strip()
    except (OSError, subprocess.SubprocessError, IndexError):
        return 'unknown'


def inspect_pdf(qpdf, path, timeout, stop=None):
    """Protection category without any password.

    ``--is-encrypted`` reports damaged files as "not encrypted" (exit 2 is shared with
    errors), so the encryption dictionary is read through qpdf's JSON instead.
    """
    r = run_qpdf(qpdf, ['--json=2', '--json-key=encrypt', fs(path)], timeout=timeout, stop=stop)
    if r.returncode in (0, 3):
        try:
            info = json.loads(r.stdout.decode('utf-8'))['encrypt']
        except (ValueError, KeyError):
            return 'InspectionFailed', 'Unreadable qpdf JSON'
        return ('PermissionRestricted' if info.get('encrypted') else 'Unencrypted'), (
            'qpdf repaired damage while reading' if r.returncode == 3 else '')
    message = qpdf_message(r.stderr)
    if 'invalid password' in message.lower():
        return 'PasswordRequired', ''
    return 'InvalidPDF', message or 'qpdf could not read the file'


def verify_output(qpdf, path, timeout, stop=None):
    """Mandatory check of a written copy: structurally readable and not encrypted."""
    r = run_qpdf(qpdf, ['--check', fs(path)], timeout=timeout, stop=stop)
    text = r.stdout.decode('utf-8', 'replace')
    if r.returncode in (0, 3) and 'File is not encrypted' in text:
        return True, ('qpdf check reported warnings' if r.returncode == 3 else '')
    if 'File is not encrypted' not in text and r.returncode in (0, 3):
        return False, 'Output is still encrypted'
    return False, qpdf_message(r.stderr) or 'qpdf --check failed'


def is_unencrypted(qpdf, path, timeout):
    return verify_output(qpdf, path, timeout)[0]


def group_for(path: Path, src: Path | str, mapping: dict[str, str]):
    relative = (path.relative_to(src).as_posix() if isinstance(src, Path) else src).casefold()
    # Longest matching folder prefix wins; no prefix overlap e.g. bank vs banking.
    found = [(len(prefix), group) for folder, group in mapping.items()
             if (prefix := folder.strip('/\\').replace('\\', '/').casefold())
             and (relative.startswith(prefix + '/') or relative == prefix)]
    return max(found)[1] if found else ''


def candidates(settings: Settings, group: str):
    values = ['']
    # Prefer group-specific credentials. Still allow general credentials.
    values.extend(settings.password_groups.get(group, []))
    values.extend(settings.passwords)
    return list(dict.fromkeys(p for p in values if isinstance(p, str) and '\n' not in p and '\r' not in p))[:settings.max_attempts]


# ---------------------------------------------------------------- output safety

def temp_name(target: Path) -> Path:
    return target.with_name(f'{target.name}{TEMP_MARK}{uuid.uuid4().hex[:12]}')


def publish(temp: Path, target: Path):
    """Atomically move a verified temp file to *target*, never replacing anything."""
    if sys.platform == 'win32':
        os.rename(fs(temp), fs(target))  # raises FileExistsError if target exists
        return
    try:
        os.link(temp, target)  # fails if target exists
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            raise FileExistsError(errno.EEXIST, 'exists', str(target)) from None
        if target.exists():
            raise FileExistsError(errno.EEXIST, 'exists', str(target)) from None
        os.rename(temp, target)
        return
    os.unlink(temp)


def remove_quietly(path: Path | None):
    if path is None:
        return
    try:
        os.chmod(fs(path), stat.S_IWRITE)
        os.unlink(fs(path))
    except FileNotFoundError:
        pass
    except OSError:
        pass


def clean_stale_temps(dst: Path) -> int:
    removed = 0
    if not dst.is_dir():
        return 0
    for entry in list(dst.iterdir()):
        if entry.is_dir() and entry.name.startswith(WORK_MARK):
            shutil.rmtree(fs(entry), ignore_errors=True)
            removed += 1
    for root, dirs, names in os.walk(dst, followlinks=False):
        for name in names:
            if TEMP_MARK in name or (LEGACY_TEMP_MARK in name and name.split(LEGACY_TEMP_MARK)[0].lower().endswith('.pdf')):
                remove_quietly(Path(root) / name)
                removed += 1
    return removed


def check_writable(dst: Path):
    dst.mkdir(parents=True, exist_ok=True)
    probe = dst / f'.rar-write-test-{uuid.uuid4().hex[:8]}'
    try:
        with open(fs(probe), 'xb') as fh:
            fh.write(b'ok')
    finally:
        remove_quietly(probe)


def probe_readable(path: Path):
    """Open the original read-only. On Windows use CreateFileW so a sharing
    violation (file open in another program) is told apart from access denied;
    the C runtime reports both as EACCES."""
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL('kernel32', use_last_error=True)
        k32.CreateFileW.restype = wintypes.HANDLE
        k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                                    wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        handle = k32.CreateFileW(fs(path), 0x80000000, 0x7, None, 3, 0x80, None)
        if handle == wintypes.HANDLE(-1).value:
            code = ctypes.get_last_error()
            err = OSError(errno.EACCES, ctypes.FormatError(code).strip())
            err.winerror = code
            raise err
        k32.CloseHandle(handle)
        return
    with open(path, 'rb') as fh:
        fh.read(1)


def classify_os_error(exc: BaseException, where: str = 'file') -> tuple[str, str]:
    winerror = getattr(exc, 'winerror', None)
    code = getattr(exc, 'errno', None)
    if winerror in (112, 39) or code == errno.ENOSPC:
        return 'DiskFull', 'Not enough free space on the output drive.'
    if winerror in (32, 33):
        return 'FileLocked', f'The {where} is open in another program.'
    if winerror in (206,) or code == errno.ENAMETOOLONG:
        return 'PathTooLong', 'The path exceeds the Windows limit.'
    if isinstance(exc, FileNotFoundError) or winerror in (2, 3):
        return 'SourceMissing', f'The {where} was not found (moved, deleted or path too long).'
    if isinstance(exc, PermissionError) or winerror == 5 or code in (errno.EACCES, errno.EPERM, errno.EROFS):
        return 'AccessDenied', f'Access to the {where} was denied (permissions or read-only).'
    return 'Error', f'{type(exc).__name__}: {getattr(exc, "strerror", None) or "unexpected error"}'


# ---------------------------------------------------------------- reports

def escape_cell(value):
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value


def unescape_cell(value: str) -> str:
    if value.startswith("'") and value[1:2] and value[1:].startswith(FORMULA_PREFIXES):
        return value[1:]
    return value


def bucket(status: str) -> str:
    if status in SUCCESS:
        return 'unlocked'
    if status == 'Cancelled':
        return 'cancelled'
    if status in ANALYSIS:
        return 'analyzed'
    if status in SKIPPED:
        return 'skipped'
    if status in FAILED:
        return 'failed'
    return 'skipped'


# ---------------------------------------------------------------- processing

def _process_one(settings: Settings, path: Path, rel: str, dst: Path, stop: threading.Event):
    started = time.monotonic()
    target = dst / rel
    group = group_for(path, rel, settings.folder_groups)
    row = dict(source=rel if settings.relative_reports else str(path),
               destination=rel if settings.relative_reports else str(target),
               status='Error', details='', attempts=0, elapsed_seconds=0, security='', group=group,
               size_bytes='', warnings='')
    temp = None
    work = None
    stop_batch = None
    try:
        row['size_bytes'] = os.stat(fs(path)).st_size
        if os.path.lexists(fs(target)) and not settings.analyze_only:
            row.update(status='SkippedExisting', details='Existing output was not overwritten')
            return row, None
        try:  # A clear status for locked or unreadable originals before qpdf runs.
            probe_readable(path)
        except OSError as exc:
            status, details = classify_os_error(exc, 'source PDF')
            row.update(status=status, details=details)
            return row, None
        # qpdf cannot open paths beyond the classic Windows limit (even with \\?\),
        # so long-path files go through a short private work folder.
        if needs_staging(path, target):
            work = make_work_dir(dst)
            engine_src = work / 'in.pdf'
            shutil.copyfile(fs(path), fs(engine_src))
        else:
            engine_src = path
        security, note = inspect_pdf(settings.qpdf, engine_src, settings.timeout, stop)
        row['security'] = security
        warnings = [note] if note else []
        if security == 'InvalidPDF' and 'no such file' in note.lower():
            row.update(status='PathTooLong', details='qpdf could not open this path')
        elif security == 'InvalidPDF':
            row.update(status='InvalidPDF', details=note or 'qpdf could not read the file')
        elif security == 'InspectionFailed':
            row.update(status='InspectionFailed', details=note)
        elif settings.analyze_only:
            row.update(status=security, details='Security scan only; no output written')
        elif security == 'Unencrypted':
            row.update(status='SkippedUnencrypted', details='No password protection')
            if settings.include_unencrypted:
                _ensure_space(target, row['size_bytes'])
                os.makedirs(fs(target.parent), exist_ok=True)
                temp = temp_name(target)
                with open(fs(path), 'rb') as fi, open(fs(temp), 'xb') as fo:
                    shutil.copyfileobj(fi, fo, 1024 * 1024)
                    fo.flush(); os.fsync(fo.fileno())
                # A staged work copy has identical bytes and a path qpdf can open.
                ok, why = verify_output(settings.qpdf, engine_src if work else temp, settings.timeout, stop)
                if not ok:
                    row.update(status='VerificationFailed', details=why)
                else:
                    publish(temp, target); temp = None
                    row.update(status='CopiedUnencrypted', details='Copied unchanged and checked')
        else:
            _ensure_space(target, row['size_bytes'])
            os.makedirs(fs(target.parent), exist_ok=True)
            row['status'] = 'PasswordNotMatched'
            row['details'] = 'No supplied password matched'
            for pw in candidates(settings, group):
                if stop.is_set():
                    raise Cancelled()
                row['attempts'] += 1
                temp = (work / f'out-{row["attempts"]}.pdf') if work else temp_name(target)
                r = run_qpdf(settings.qpdf, ['--password-file=-', '--decrypt', fs(engine_src), fs(temp)], pw,
                             settings.timeout, stop)
                message = qpdf_message(r.stderr)
                if r.returncode not in (0, 3) or not os.path.exists(fs(temp)):
                    remove_quietly(temp); temp = None
                    if 'invalid password' in message.lower():
                        continue
                    if 'no space' in message.lower() or 'disk full' in message.lower():
                        raise OSError(errno.ENOSPC, 'No space left on device')
                    row.update(status='DecryptFailed', details=message or 'qpdf could not write the output')
                    break
                if r.returncode == 3:
                    warnings.append('qpdf repaired damage while rebuilding')
                ok, why = verify_output(settings.qpdf, temp, settings.timeout, stop)
                if not ok:
                    row.update(status='VerificationFailed', details=why)
                    break
                if why:
                    warnings.append(why)
                if work:  # bring the verified copy next to its final name, then publish
                    staged = temp_name(target)
                    with open(fs(temp), 'rb') as fi, open(fs(staged), 'xb') as fo:
                        shutil.copyfileobj(fi, fo, 1024 * 1024)
                        fo.flush(); os.fsync(fo.fileno())
                    remove_quietly(temp)
                    temp = staged
                    warnings.append('long path processed through a short work folder')
                try:
                    publish(temp, target); temp = None
                except FileExistsError:
                    row.update(status='SkippedExisting', details='An output with this name appeared during the run')
                else:
                    row.update(status='Unlocked', details='Encryption removed; output passed qpdf --check')
                break
        row['warnings'] = '; '.join(dict.fromkeys(w for w in warnings if w))
    except Cancelled:
        row.update(status='Cancelled', details='Stopped before this file finished')
    except subprocess.TimeoutExpired:
        row.update(status='Timeout', details=f'qpdf did not finish within {settings.timeout} s')
    except InsufficientSpace as exc:
        row.update(status='DiskFull', details=str(exc))
        stop_batch = 'DiskFull'
    except OSError as exc:
        status, details = classify_os_error(exc, 'output' if temp else 'file')
        row.update(status=status, details=details)
        if status == 'DiskFull':
            stop_batch = 'DiskFull'
    except ValueError as exc:
        row.update(status='Error', details=str(exc)[:200])
    finally:
        remove_quietly(temp)
        if work:
            shutil.rmtree(fs(work), ignore_errors=True)
        row['elapsed_seconds'] = round(time.monotonic() - started, 2)
    return row, stop_batch


LONG_PATH = 240
WORK_MARK = '.rar-work-'


def needs_staging(path: Path, target: Path) -> bool:
    return sys.platform == 'win32' and max(len(str(path)), len(str(target)) + 30) >= LONG_PATH


def make_work_dir(dst: Path) -> Path:
    base = dst if len(str(dst)) < 150 else Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'RAR PDF Batch Unlocker'
    work = base / f'{WORK_MARK}{uuid.uuid4().hex[:10]}'
    os.makedirs(fs(work))
    return work


class InsufficientSpace(Exception):
    pass


def _ensure_space(target: Path, size):
    probe = target.parent
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        free = shutil.disk_usage(fs(probe)).free
    except OSError:
        return
    need = int(size or 0) * 2 + 16 * 1024 * 1024
    if free < need:
        raise InsufficientSpace(f'Only {free // (1024 * 1024)} MB free on the output drive; about {need // (1024 * 1024)} MB needed.')


def process(settings: Settings, emit, stop: threading.Event):
    started_wall = datetime.now()
    started = time.monotonic()
    p = plan(settings)
    src, dst, files = p.base, p.destination, p.files
    emit('scan', {'count': len(files), 'plan': p})
    if settings.dry_run:
        for i, path in enumerate(files, 1):
            if stop.is_set():
                break
            emit('result', {'source': str(path), 'relative': p.relative[path], 'destination': '', 'status': 'DryRun',
                            'details': 'No files changed; no passwords tested', 'attempts': 0,
                            'elapsed_seconds': 0, 'index': i, 'total': len(files), 'security': '', 'group': '',
                            'size_bytes': '', 'warnings': ''})
        emit('done', {'report': None, 'cancelled': stop.is_set(), 'summary': None})
        return
    try:
        check_writable(dst)
    except OSError as exc:
        status, details = classify_os_error(exc, 'output folder')
        raise ValueError(f'Cannot write to the output folder: {details}') from None
    stale = clean_stale_temps(dst)
    stamp = f'{datetime.now():%Y%m%d-%H%M%S-%f}'
    report = dst / f'unlock-report-{stamp}.csv'
    run_file = dst / f'unlock-run-{stamp}.json'
    engine = qpdf_version(settings.qpdf)
    record = {
        'schema': 'rar-pdf-unlock-run/1', 'app_version': settings.app_version, 'qpdf_version': engine,
        'state': 'running', 'started': started_wall.isoformat(timespec='seconds'),
        'mode': 'analyze' if settings.analyze_only else 'unlock',
        'continued_from': ('resume' if settings.resume_report else 'retry' if settings.failed_report else ''),
        'input_fingerprint': p.fingerprint, 'report_csv': report.name,
        'settings': {'limit': settings.limit, 'max_attempts': settings.max_attempts, 'timeout_seconds': settings.timeout,
                     'workers': settings.workers, 'include_unencrypted': settings.include_unencrypted,
                     'relative_paths': settings.relative_reports,
                     'password_groups': {g: len(v) for g, v in settings.password_groups.items()},
                     'general_passwords': len(settings.passwords), 'folder_rules': len(settings.folder_groups)},
        'selection': {'pdfs': len(files), 'bytes': p.total_bytes, 'duplicates_removed': p.duplicates,
                      'not_selected': len(p.rejected), 'other_files_ignored': p.ignored_other,
                      'stale_temp_files_removed': stale},
    }
    _write_json(run_file, record)
    counts: dict[str, int] = {}
    processed = 0
    halted = ''
    lock = threading.Lock()
    with open(report, 'x', encoding='utf-8-sig', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=FIELDS)
        writer.writeheader()
        for path_text, reason in p.rejected:
            if reason.startswith('OutputConflict'):
                rel = path_text
                try:
                    rel = relative_name(Path(path_text), src)
                except ValueError:
                    pass
                row = dict(source=rel if settings.relative_reports else path_text, destination='',
                           status='OutputConflict', details=reason.split(': ', 1)[1], attempts=0,
                           elapsed_seconds=0, security='', group='', size_bytes='', warnings='')
                writer.writerow({k: escape_cell(v) for k, v in row.items()})
                counts['OutputConflict'] = counts.get('OutputConflict', 0) + 1
        out.flush()

        def record_row(path, row):
            nonlocal processed
            with lock:
                processed += 1
                counts[row['status']] = counts.get(row['status'], 0) + 1
                writer.writerow({k: escape_cell(v) for k, v in row.items()})
                out.flush()
                index = processed
            emit('result', {**row, 'source': str(path), 'relative': p.relative[path],
                            'output': str(dst / p.relative[path]), 'index': index, 'total': len(files)})

        workers = max(1, min(settings.workers, len(files) or 1))
        with cf.ThreadPoolExecutor(max_workers=workers, thread_name_prefix='rar-unlock') as pool:
            pending: dict[cf.Future, Path] = {}
            queue_iter = iter(files)
            while True:
                while not stop.is_set() and not halted and len(pending) < workers:
                    path = next(queue_iter, None)
                    if path is None:
                        break
                    pending[pool.submit(_process_one, settings, path, p.relative[path], dst, stop)] = path
                if not pending:
                    break
                done, _ = cf.wait(pending, return_when=cf.FIRST_COMPLETED)
                for fut in done:
                    path = pending.pop(fut)
                    row, stop_batch = fut.result()
                    if stop_batch and not halted:
                        halted = stop_batch
                    record_row(path, row)
        out.flush()
        try:
            os.fsync(out.fileno())
        except OSError:
            pass
    elapsed = round(time.monotonic() - started, 2)
    buckets = {'unlocked': 0, 'analyzed': 0, 'skipped': 0, 'failed': 0, 'cancelled': 0}
    for status, n in counts.items():
        buckets[bucket(status)] += n
    record.update(state='cancelled' if stop.is_set() else 'halted' if halted else 'complete',
                  halted_reason=halted, finished=datetime.now().isoformat(timespec='seconds'),
                  elapsed_seconds=elapsed, processed=processed, not_started=len(files) - processed,
                  status_counts=dict(sorted(counts.items())), totals=buckets,
                  report_sha256=hashlib.sha256(report.read_bytes()).hexdigest())
    _write_json(run_file, record)
    html = None
    if settings.html_summary:
        from reports import write_html
        html = dst / f'unlock-summary-{stamp}.html'
        write_html(html, record, report)
    emit('done', {'report': str(report), 'run': str(run_file), 'html': str(html) if html else None,
                  'cancelled': stop.is_set(), 'halted': halted, 'summary': record})


def _write_json(path: Path, data: dict):
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(tmp, path)


def engine_status(qpdf: str) -> tuple[bool | None, str]:
    """Compare a bundled qpdf with the manifest written at build time."""
    exe = Path(qpdf)
    manifest = exe.parent.parent / 'qpdf-manifest.json'
    if not manifest.is_file():
        return None, 'No build manifest (external qpdf).'
    try:
        expected = json.loads(manifest.read_text(encoding='utf-8'))['files']
    except (OSError, ValueError, KeyError):
        return False, 'Manifest unreadable.'
    root = manifest.parent
    for rel, digest in expected.items():
        f = root / rel
        try:
            actual = hashlib.sha256(f.read_bytes()).hexdigest()
        except OSError:
            return False, f'Missing engine file: {rel}'
        if actual != digest:
            return False, f'Engine file changed: {rel}'
    return True, f'{len(expected)} engine files match the build manifest.'
