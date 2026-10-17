"""Readable, self-contained HTML run summary. Metadata only: no passwords, no PDF content."""
from __future__ import annotations

import csv
import html
from pathlib import Path

from core import ACTIONS, FAILED, unescape_cell

STATUS_TEXT = {
    'Unlocked': 'Unlocked', 'PasswordNotMatched': 'No password match', 'PasswordRequired': 'Password required',
    'PermissionRestricted': 'Permission restricted', 'Unencrypted': 'Unencrypted',
    'SkippedUnencrypted': 'Already unencrypted', 'CopiedUnencrypted': 'Copied unencrypted',
    'SkippedExisting': 'Output exists', 'InspectionFailed': 'Inspection failed',
    'VerificationFailed': 'Verification failed', 'DecryptFailed': 'Rebuild failed', 'InvalidPDF': 'Invalid PDF',
    'Timeout': 'Timed out', 'Error': 'Error', 'Cancelled': 'Cancelled', 'DryRun': 'Dry run',
    'FileLocked': 'File locked', 'AccessDenied': 'Access denied', 'DiskFull': 'Disk full',
    'PathTooLong': 'Path too long', 'SourceMissing': 'Source missing', 'OutputConflict': 'Output name conflict',
}


def write_html(path: Path, record: dict, report_csv: Path):
    with open(report_csv, newline='', encoding='utf-8-sig') as fh:
        rows = [{k: unescape_cell(v or '') for k, v in r.items() if k} for r in csv.DictReader(fh)]
    e = html.escape
    totals = record.get('totals', {})
    kpis = [('Processed', record.get('processed', 0)), ('Unlocked', totals.get('unlocked', 0)),
            ('Analyzed', totals.get('analyzed', 0)), ('Skipped', totals.get('skipped', 0)),
            ('Need attention', totals.get('failed', 0)), ('Cancelled', totals.get('cancelled', 0)),
            ('Not started', record.get('not_started', 0))]
    problems = [r for r in rows if r.get('status') in FAILED]
    counts = ''.join(f'<tr><td>{e(STATUS_TEXT.get(k, k))}</td><td class="n">{v}</td></tr>'
                     for k, v in record.get('status_counts', {}).items())
    issue_rows = ''.join(
        f'<tr><td>{e(STATUS_TEXT.get(r["status"], r["status"]))}</td><td class="path">{e(r.get("source", ""))}</td>'
        f'<td>{e(r.get("details", ""))}</td><td>{e(ACTIONS.get(r["status"], ""))}</td></tr>' for r in problems[:2000])
    more = f'<p class="muted">{len(problems) - 2000} more rows are in the CSV.</p>' if len(problems) > 2000 else ''
    s = record.get('settings', {})
    sel = record.get('selection', {})
    body = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Unlock summary {e(record.get('started', ''))}</title>
<style>
body{{font:14px/1.5 "Segoe UI",system-ui,sans-serif;margin:0;background:#f5f7fb;color:#0d1626}}
main{{max-width:1100px;margin:auto;padding:28px 20px}} h1{{font-size:24px;margin:0 0 4px}}
.muted{{color:#4a5a72}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin:18px 0}}
.k{{background:#fff;border:1px solid #d8e0ec;border-radius:8px;padding:12px}} .k b{{display:block;font-size:24px}}
table{{border-collapse:collapse;width:100%;background:#fff;margin:8px 0 18px}} th,td{{border:1px solid #d8e0ec;padding:6px 8px;text-align:left;vertical-align:top}}
th{{background:#eaf0f8}} .n{{text-align:right}} .path{{word-break:break-all}}
</style></head><body><main>
<h1>RAR PDF Batch Unlocker — run summary</h1>
<p class="muted">State: <b>{e(record.get('state', ''))}</b>{(' · ' + e(record['halted_reason'])) if record.get('halted_reason') else ''}
 · Mode: {e(record.get('mode', ''))} · Started {e(record.get('started', ''))} · Finished {e(record.get('finished', ''))}
 · Elapsed {e(str(record.get('elapsed_seconds', '')))} s</p>
<p class="muted">App {e(record.get('app_version', ''))} · Engine: {e(record.get('qpdf_version', ''))} · CSV: {e(record.get('report_csv', ''))} (SHA-256 {e(record.get('report_sha256', '')[:16])}…)</p>
<div class="grid">{''.join(f'<div class="k"><b>{v}</b>{e(k)}</div>' for k, v in kpis)}</div>
<h2>Selection and settings</h2>
<table><tr><th>PDFs selected</th><td>{sel.get('pdfs', 0)}</td><th>Total size</th><td>{sel.get('bytes', 0):,} bytes</td></tr>
<tr><th>Duplicates removed</th><td>{sel.get('duplicates_removed', 0)}</td><th>Not selected (links, unsupported, conflicts)</th><td>{sel.get('not_selected', 0)}</td></tr>
<tr><th>Attempts per PDF</th><td>{s.get('max_attempts', '')}</td><th>Timeout</th><td>{s.get('timeout_seconds', '')} s</td></tr>
<tr><th>Parallel workers</th><td>{s.get('workers', '')}</td><th>Passwords supplied</th><td>{s.get('general_passwords', 0) + sum(s.get('password_groups', {}).values())} (values never recorded)</td></tr>
<tr><th>Continued from</th><td>{e(record.get('continued_from') or '—')}</td><th>Copy unencrypted</th><td>{'Yes' if s.get('include_unencrypted') else 'No'}</td></tr></table>
<h2>Status counts</h2><table><tr><th>Status</th><th class="n">Files</th></tr>{counts or '<tr><td colspan="2">No files processed.</td></tr>'}</table>
<h2>Files that need attention ({len(problems)})</h2>
{'<table><tr><th>Status</th><th>File</th><th>Details</th><th>What to do</th></tr>' + issue_rows + '</table>' if problems else '<p>None.</p>'}{more}
<p class="muted">Passwords are never written to reports. Unlocked PDFs remain sensitive; keep the output folder access-controlled.</p>
</main></body></html>'''
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(body, encoding='utf-8')
    tmp.replace(path)
