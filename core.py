"""Offline PDF analysis and guarded qpdf operations; Python 3.10+."""
from __future__ import annotations
import csv
from dataclasses import dataclass, field
from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time

FIELDS = ['source', 'destination', 'status', 'details', 'attempts', 'elapsed_seconds', 'security', 'group']
FAILED = {'PasswordNotMatched', 'PasswordRequired', 'InvalidPDF', 'InspectionFailed', 'Timeout', 'Error', 'Cancelled', 'VerificationFailed'}

@dataclass
class Settings:
    source: Path
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


def validate_paths(settings: Settings):
    src = settings.source.expanduser().resolve(strict=True)
    dst = settings.destination.expanduser().resolve(strict=False)
    if not src.is_dir():
        raise ValueError('Source must be a folder.')
    if os.path.normcase(str(src)) == os.path.normcase(str(dst)) or src in dst.parents or dst in src.parents:
        raise ValueError('Source and destination must be separate, non-nested folders.')
    if not Path(settings.qpdf).is_file() and not shutil.which(settings.qpdf):
        raise ValueError('qpdf executable not found. Select qpdf.exe or add it to PATH.')
    if not 0 <= settings.limit <= 1000000 or not 1 <= settings.max_attempts <= 1000:
        raise ValueError('Invalid limit or maximum attempts.')
    if settings.timeout < 1 or settings.timeout > 3600:
        raise ValueError('Invalid timeout.')
    return src, dst


def _retry_paths(csvpath: str, src: Path):
    rows = []
    with open(csvpath, newline='', encoding='utf-8-sig') as fh:
        reader = csv.DictReader(fh)
        if not {'source','status'}.issubset(reader.fieldnames or []):
            raise ValueError('Retry report lacks required CSV columns.')
        for row in reader:
            if row['status'] not in FAILED:
                continue
            rel = Path(row['source'])
            if rel.is_absolute():
                # Legacy reports stored absolute paths. Accept only inside selected source.
                try: rel = rel.resolve().relative_to(src)
                except ValueError: continue
            path = (src / rel).resolve()
            if not path.is_relative_to(src) or not path.is_file() or path.suffix.lower() != '.pdf':
                continue
            rows.append(path)
    return sorted(set(rows), key=lambda x: str(x).casefold())


def scan(settings: Settings):
    src, dst = validate_paths(settings)
    files = _retry_paths(settings.failed_report, src) if settings.failed_report else sorted(
        (p for p in src.rglob('*') if p.is_file() and p.suffix.lower() == '.pdf' and not p.is_symlink()),
        key=lambda p: str(p).casefold())
    return src, dst, (files[:settings.limit] if settings.limit else files)


def run_qpdf(qpdf: str, args: list[str], password: str | None = None, timeout: int = 60):
    """Send supplied password through stdin; never command line or environment."""
    data = None if password is None else (password + '\n').encode('utf-8')
    return subprocess.run([qpdf, *args], input=data, stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE, timeout=timeout, check=False,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def inspect_pdf(qpdf, path, timeout):
    """Return security category without requiring a password. qpdf 0=yes, 2=no."""
    enc = run_qpdf(qpdf, ['--is-encrypted', str(path)], timeout=timeout)
    if enc.returncode == 2: return 'Unencrypted'
    if enc.returncode != 0: return 'InvalidPDF'
    req = run_qpdf(qpdf, ['--requires-password', str(path)], timeout=timeout)
    if req.returncode == 0: return 'PasswordRequired'
    if req.returncode == 3: return 'PermissionRestricted'
    return 'InspectionFailed'


def is_unencrypted(qpdf, path, timeout):
    return run_qpdf(qpdf, ['--is-encrypted', str(path)], timeout=timeout).returncode == 2


def group_for(path: Path, src: Path, mapping: dict[str, str]):
    relative = path.relative_to(src).as_posix().casefold()
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


def _safe_report_value(path, src, relative):
    return path.relative_to(src).as_posix() if relative else str(path)


def process(settings: Settings, emit, stop: threading.Event):
    src, dst, files = scan(settings)
    emit('scan', {'count': len(files)})
    if settings.dry_run:
        for i, p in enumerate(files, 1):
            if stop.is_set(): break
            emit('result', {'source': str(p), 'destination': '', 'status':'DryRun', 'details':'No files changed; no passwords tested', 'attempts':0, 'elapsed_seconds':0, 'index':i, 'total':len(files), 'security':'', 'group':''})
        emit('done', {'report': None, 'cancelled': stop.is_set()})
        return
    dst.mkdir(parents=True, exist_ok=True)
    report = dst / f'unlock-report-{datetime.now():%Y%m%d-%H%M%S-%f}.csv'
    with report.open('x', encoding='utf-8-sig', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=FIELDS)
        writer.writeheader()
        for i, path in enumerate(files, 1):
            if stop.is_set(): break
            started = time.monotonic()
            relative = path.relative_to(src)
            target = dst / relative
            group = group_for(path, src, settings.folder_groups)
            row = dict(source=_safe_report_value(path,src,settings.relative_reports),
                       destination=relative.as_posix() if settings.relative_reports else str(target),
                       status='Error', details='', attempts=0, elapsed_seconds=0, security='', group=group)
            partial = None
            try:
                if target.exists() and not settings.analyze_only:
                    row.update(status='SkippedExisting', details='Existing destination was not overwritten')
                else:
                    security = inspect_pdf(settings.qpdf, path, settings.timeout)
                    row['security'] = security
                    if security in ('InvalidPDF', 'InspectionFailed'):
                        row.update(status=security, details='qpdf could not inspect this PDF')
                    elif settings.analyze_only:
                        row.update(status=security, details='Security scan only; no output written')
                    elif security == 'Unencrypted':
                        row.update(status='SkippedUnencrypted', details='No password protection')
                        if settings.include_unencrypted:
                            target.parent.mkdir(parents=True, exist_ok=True)
                            with open(path, 'rb') as source_handle:
                                with open(target, 'xb') as output_handle:
                                    shutil.copyfileobj(source_handle, output_handle)
                            row.update(status='CopiedUnencrypted', details='Copied unchanged')
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        for pw in candidates(settings, group):
                            if stop.is_set():
                                row['status'] = 'Cancelled'
                                break
                            row['attempts'] += 1
                            partial = target.with_name(target.name + f'.rar-part-{os.getpid()}-{threading.get_ident()}')
                            try:
                                r = run_qpdf(settings.qpdf, ['--password-file=-', '--decrypt', str(path), str(partial)], pw, settings.timeout)
                                if r.returncode in (0, 3) and partial.exists() and partial.stat().st_size:
                                    if not is_unencrypted(settings.qpdf, partial, settings.timeout):
                                        row.update(status='VerificationFailed', details='Output remained encrypted')
                                        break
                                    # Windows-safe no-replace creation via exclusive create.
                                    try:
                                        with open(partial, 'rb') as fi, open(target, 'xb') as fo:
                                            shutil.copyfileobj(fi, fo)
                                    except FileExistsError:
                                        row.update(status='SkippedExisting', details='Output already exists')
                                    else:
                                        row.update(status='Unlocked', details='Encryption removed and verified')
                                    break
                            finally:
                                if partial and partial.exists(): partial.unlink()
                        else:
                            row.update(status='PasswordNotMatched', details='No supplied candidate matched')
            except subprocess.TimeoutExpired:
                row.update(status='Timeout', details='qpdf timeout')
            except (OSError, ValueError) as ex:
                row.update(status='Error', details=type(ex).__name__)
            finally:
                if partial and partial.exists():
                    try: partial.unlink()
                    except OSError: pass
            row['elapsed_seconds'] = round(time.monotonic()-started, 2)
            writer.writerow(row)
            out.flush()
            emit('result', {**row, 'source':str(path), 'index':i, 'total':len(files)})
    emit('done', {'report':str(report), 'cancelled':stop.is_set()})
