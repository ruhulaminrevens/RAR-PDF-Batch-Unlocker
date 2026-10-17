"""Core engine tests. Real-qpdf tests use synthetic PDFs only and skip when qpdf is absent."""
import csv
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core
from scripts.fixtures import create_fixtures, make_pdf, KNOWN

QPDF = os.environ.get('RAR_TEST_QPDF') or shutil.which('qpdf')
WINDOWS = sys.platform == 'win32'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def run_batch(self, settings, stop=None, on_result=None):
        events = []
        stop = stop or threading.Event()

        def emit(kind, payload):
            events.append((kind, payload))
            if kind == 'result' and on_result:
                on_result(payload, stop)
        core.process(settings, emit, stop)
        return [p for k, p in events if k == 'result'], events[-1][1]


class SelectionTests(Base):
    """Path planning; no qpdf needed (sys.executable stands in for the engine path)."""

    def setUp(self):
        super().setUp()
        self.src = self.root / 'source'
        for name in ('a.pdf', 'sub/b.PDF', 'sub/c.pdf', 'd.txt'):
            f = self.src / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b'%PDF-1.4 fixture')
        self.settings = core.Settings(self.src, self.root / 'output', sys.executable, [])

    def test_folder_scan_and_nested_rejection(self):
        p = core.plan(self.settings)
        self.assertEqual([p.relative[f] for f in p.files], ['a.pdf', 'sub/b.PDF', 'sub/c.pdf'])
        self.assertEqual(p.ignored_other, 1)
        src, dst, files = core.scan(self.settings)  # legacy tuple form still works
        self.assertEqual(len(files), 3)
        for bad in (self.src / 'child', self.src, self.root):
            self.settings.destination = bad
            with self.assertRaises(ValueError):
                core.scan(self.settings)

    def test_single_and_multiple_files_with_duplicates_and_unsupported(self):
        s = core.Settings(None, self.root / 'out', sys.executable, [],
                          inputs=[self.src / 'sub' / 'c.pdf', self.src / 'a.pdf', self.src / 'a.pdf', self.src / 'd.txt'])
        p = core.plan(s)
        self.assertEqual(sorted(p.relative.values()), ['a.pdf', 'sub/c.pdf'])  # common parent keeps names unique
        self.assertEqual(p.duplicates, 1)
        self.assertIn(('%s' % (self.src / 'd.txt'), 'Unsupported file type (only .pdf)'), p.rejected)
        single = core.plan(core.Settings(None, self.root / 'out', sys.executable, [], inputs=[self.src / 'sub' / 'b.PDF']))
        self.assertEqual(list(single.relative.values()), ['b.PDF'])
        # A file inside a selected folder counts once.
        mixed = core.plan(core.Settings(self.src, self.root / 'out', sys.executable, [], inputs=[self.src / 'a.pdf']))
        self.assertEqual(len(mixed.files), 3)
        self.assertEqual(mixed.duplicates, 1)

    def test_output_next_to_selected_file_is_rejected(self):
        s = core.Settings(None, self.src / 'sub', sys.executable, [], inputs=[self.src / 'sub' / 'c.pdf'])
        with self.assertRaises(ValueError):
            core.plan(s)

    @unittest.skipIf(WINDOWS, 'case-sensitive file system needed to create both names')
    def test_case_conflicting_output_names(self):
        (self.src / 'A.pdf').write_bytes(b'%PDF-1.4')
        p = core.plan(self.settings)
        self.assertEqual(len([r for r in p.rejected if r[1].startswith('OutputConflict')]), 1)
        self.assertEqual(len(p.files), 3)

    def test_links_and_junctions_not_followed(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'secret.pdf').write_bytes(b'%PDF-1.4')
        link = self.src / 'linked'
        if WINDOWS:
            r = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(outside)], capture_output=True)
            self.assertEqual(r.returncode, 0, r.stderr)
        else:
            os.symlink(outside, link)
        p = core.plan(self.settings)
        self.assertFalse(any('secret.pdf' in str(f) for f in p.files))
        self.assertTrue(any(reason.startswith('Link') for _, reason in p.rejected))

    def test_retry_report_filters_failures_and_traversal(self):
        rp = self.root / 'previous.csv'
        with rp.open('w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=['source', 'status'])
            w.writeheader()
            w.writerow({'source': 'sub/c.pdf', 'status': 'PasswordNotMatched'})
            w.writerow({'source': '../outside.pdf', 'status': 'PasswordNotMatched'})
            w.writerow({'source': 'a.pdf', 'status': 'Unlocked'})
        self.settings.failed_report = str(rp)
        self.assertEqual([f.name for f in core.plan(self.settings).files], ['c.pdf'])

    def test_groups_candidates_and_limits(self):
        s = core.Settings(self.src, self.root / 'o', sys.executable, ['general', 'general'],
                          password_groups={'Bank': ['bankpass']}, folder_groups={'sub': 'Bank', 'su': 'X'}, max_attempts=2)
        self.assertEqual(core.group_for(self.src / 'sub' / 'c.pdf', self.src, s.folder_groups), 'Bank')
        self.assertEqual(core.candidates(s, 'Bank'), ['', 'bankpass'])
        s.limit = 2
        self.assertEqual(len(core.plan(s).files), 2)
        for field, value in (('workers', 0), ('timeout', 0), ('max_attempts', 0)):
            bad = core.Settings(self.src, self.root / 'o', sys.executable, [], **{field: value})
            with self.assertRaises(ValueError):
                core.plan(bad)


class UnitTests(unittest.TestCase):
    def test_password_uses_stdin_not_arguments_or_environment(self):
        with patch.object(core.subprocess, 'Popen') as popen:
            popen.return_value.communicate.return_value = (b'', b'')
            popen.return_value.returncode = 0
            core.run_qpdf('qpdf', ['--password-file=-', '--decrypt', 'in.pdf', 'out.pdf'], 'synthetic-secret')
        args, kwargs = popen.call_args
        self.assertNotIn('synthetic-secret', ' '.join(args[0]))
        self.assertNotIn('env', kwargs)
        self.assertEqual(popen.return_value.communicate.call_args.kwargs['input'], b'synthetic-secret\n')

    def test_stop_kills_running_engine_quickly(self):
        stop = threading.Event()
        threading.Timer(0.3, stop.set).start()
        started = time.monotonic()
        with self.assertRaises(core.Cancelled):
            core.run_qpdf(sys.executable, ['-c', 'import time; time.sleep(30)'], timeout=60, stop=stop)
        self.assertLess(time.monotonic() - started, 5)

    def test_timeout_kills_engine(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            core.run_qpdf(sys.executable, ['-c', 'import time; time.sleep(30)'], timeout=1)

    def test_error_classification(self):
        def err(cls=OSError, code=None, win=None):
            e = cls(code, 'x') if code else cls('x')
            if win is not None:
                e.winerror = win
            return e
        self.assertEqual(core.classify_os_error(err(OSError, errno.ENOSPC))[0], 'DiskFull')
        self.assertEqual(core.classify_os_error(err(OSError, 13, 112))[0], 'DiskFull')
        self.assertEqual(core.classify_os_error(err(PermissionError, 13, 32))[0], 'FileLocked')
        self.assertEqual(core.classify_os_error(err(PermissionError, 13, 5))[0], 'AccessDenied')
        self.assertEqual(core.classify_os_error(err(OSError, 2, 206))[0], 'PathTooLong')
        self.assertEqual(core.classify_os_error(err(FileNotFoundError, 2))[0], 'SourceMissing')
        self.assertEqual(core.classify_os_error(ValueError('x'))[0], 'Error')

    def test_formula_cells_escaped_and_restored(self):
        for value in ('=HYPERLINK("x").pdf', '+1.pdf', '-a.pdf', '@x.pdf'):
            self.assertTrue(core.escape_cell(value).startswith("'"))
            self.assertEqual(core.unescape_cell(core.escape_cell(value)), value)
        self.assertEqual(core.escape_cell("O'Brien.pdf"), "O'Brien.pdf")
        self.assertEqual(core.unescape_cell("'quoted.pdf"), "'quoted.pdf")

    def test_qpdf_message_removes_path(self):
        err = b'WARNING: C:\\Users\\me\\x.pdf: file is damaged\nqpdf: C:\\Users\\me\\x.pdf: unable to find trailer dictionary\n'
        self.assertEqual(core.qpdf_message(err), 'unable to find trailer dictionary')
        self.assertEqual(core.qpdf_message(b'qpdf: /tmp/a.pdf (object 2 0, offset 9): unexpected EOF\n'), 'unexpected EOF')

    def test_engine_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'bin').mkdir()
            exe = root / 'bin' / 'qpdf.exe'
            exe.write_bytes(b'engine')
            self.assertIsNone(core.engine_status(str(exe))[0])
            (root / 'qpdf-manifest.json').write_text(json.dumps({'files': {'bin/qpdf.exe': sha(exe)}}))
            self.assertTrue(core.engine_status(str(exe))[0])
            exe.write_bytes(b'tampered')
            self.assertFalse(core.engine_status(str(exe))[0])


@unittest.skipUnless(QPDF, 'Real qpdf executable not available')
class QpdfTests(Base):
    def setUp(self):
        super().setUp()
        self.src = create_fixtures(self.root).resolve()
        self.dst = self.root / 'Output'
        self.settings = core.Settings(self.src, self.dst, QPDF, [KNOWN], app_version='test')
        self.before = {p: sha(p) for p in self.src.rglob('*.pdf')}

    def originals_unchanged(self):
        self.assertEqual(self.before, {p: sha(p) for p in self.before})

    def test_unlock_verify_reports_and_no_overwrite(self):
        rows, done = self.run_batch(self.settings)
        counts = {}
        for r in rows:
            counts[r['status']] = counts.get(r['status'], 0) + 1
        self.assertEqual(counts, {'Unlocked': 3, 'PasswordNotMatched': 1, 'SkippedUnencrypted': 1})
        for out in self.dst.rglob('*.pdf'):
            self.assertTrue(core.verify_output(QPDF, out, 60)[0])
        self.originals_unchanged()
        record = json.loads(Path(done['run']).read_text(encoding='utf-8'))
        self.assertEqual(record['state'], 'complete')
        self.assertEqual(record['totals']['unlocked'], 3)
        self.assertEqual(record['totals']['failed'], 1)
        self.assertEqual(record['processed'], 5)
        self.assertIn('qpdf', record['qpdf_version'].lower())
        self.assertEqual(record['report_sha256'], sha(done['report']))
        for artifact in (done['report'], done['run'], done['html']):
            text = Path(artifact).read_text(encoding='utf-8-sig')
            self.assertNotIn(KNOWN, text)
            self.assertNotIn(str(self.root), text)
        self.assertFalse(list(self.dst.rglob(f'*{core.TEMP_MARK}*')))
        outputs = {p: sha(p) for p in self.dst.rglob('*.pdf')}
        rows, _ = self.run_batch(self.settings)
        self.assertEqual(sum(r['status'] == 'SkippedExisting' for r in rows), 3)
        self.assertEqual(outputs, {p: sha(p) for p in outputs})
        self.settings.failed_report = done['report']
        rows, _ = self.run_batch(self.settings)
        self.assertEqual([r['status'] for r in rows], ['PasswordNotMatched'])

    def test_damaged_empty_and_non_pdf_are_invalid_not_unencrypted(self):
        good = (self.src / 'Finance' / 'Monthly-statement.pdf').read_bytes()
        (self.src / 'damaged.pdf').write_bytes(good[:400])
        (self.src / 'empty.pdf').write_bytes(b'')
        (self.src / 'photo.pdf').write_bytes(os.urandom(500))
        self.settings.include_unencrypted = True
        rows, _ = self.run_batch(self.settings)
        by = {Path(r['source']).name: r for r in rows}
        for name in ('damaged.pdf', 'empty.pdf', 'photo.pdf'):
            self.assertEqual(by[name]['status'], 'InvalidPDF', by[name])
            self.assertFalse((self.dst / name).exists())
        self.assertEqual(by['Welcome.pdf']['status'], 'CopiedUnencrypted')

    def test_interrupted_publish_leaves_nothing_and_halts(self):
        calls = {'n': 0}
        real = core.publish

        def failing(temp, target):
            calls['n'] += 1
            if calls['n'] == 1:
                raise OSError(errno.ENOSPC, 'No space left on device')
            return real(temp, target)
        with patch.object(core, 'publish', side_effect=failing):
            rows, done = self.run_batch(self.settings)
        full = [r for r in rows if r['status'] == 'DiskFull']
        self.assertEqual(len(full), 1)
        self.assertEqual(done['halted'], 'DiskFull')
        self.assertLess(len(rows), 5)
        self.assertFalse(list(self.dst.rglob(f'*{core.TEMP_MARK}*')))
        self.assertFalse((self.dst / full[0]['relative']).exists())
        rows, _ = self.run_batch(self.settings)  # nothing half-written is mistaken for output
        self.assertEqual(sum(r['status'] == 'Unlocked' for r in rows), 3)

    def test_low_disk_space_halts_before_writing(self):
        with patch.object(core.shutil, 'disk_usage', return_value=shutil._ntuple_diskusage(10**9, 10**9 - 1000, 1000)):
            rows, done = self.run_batch(self.settings)
        self.assertEqual(done['halted'], 'DiskFull')
        self.assertFalse(list(self.dst.rglob('*.pdf')))

    def test_verification_failure_discards_output(self):
        with patch.object(core, 'verify_output', return_value=(False, 'Output is still encrypted')):
            rows, _ = self.run_batch(self.settings)
        self.assertEqual(sum(r['status'] == 'VerificationFailed' for r in rows), 3)
        self.assertFalse(list(self.dst.rglob('*.pdf')))
        self.assertFalse(list(self.dst.rglob(f'*{core.TEMP_MARK}*')))

    def test_stop_then_resume_finishes_remaining_only(self):
        self.settings.workers = 1
        rows, done = self.run_batch(self.settings, on_result=lambda p, stop: stop.set())
        self.assertEqual(len(rows), 1)
        record = json.loads(Path(done['run']).read_text(encoding='utf-8'))
        self.assertEqual(record['state'], 'cancelled')
        self.assertEqual(record['not_started'], 4)
        self.settings.resume_report = done['report']
        rows2, _ = self.run_batch(self.settings)
        first = rows[0]['relative']
        self.assertNotIn(first, [r['relative'] for r in rows2] if rows[0]['status'] in core.DONE_FOR_RESUME else [])
        self.assertEqual(len(rows2), 4 if rows[0]['status'] in core.DONE_FOR_RESUME else 5)
        self.assertEqual(len(list(self.dst.rglob('*.pdf'))), 3)
        other = self.root / 'Other'
        other.mkdir()
        self.settings.source = other
        with self.assertRaises(ValueError):
            core.plan(self.settings)

    def test_parallel_matches_sequential(self):
        self.settings.workers = 4
        rows, done = self.run_batch(self.settings)
        self.assertEqual(sorted(r['status'] for r in rows),
                         sorted(['Unlocked'] * 3 + ['PasswordNotMatched', 'SkippedUnencrypted']))
        self.assertEqual(sorted(r['index'] for r in rows), [1, 2, 3, 4, 5])
        self.originals_unchanged()

    def test_unicode_formula_and_long_paths(self):
        deep = self.src / 'বাংলা ফোল্ডার' / ('দীর্ঘ-নাম-' * 6) / ('x' * 60) / ('y' * 60)
        names = ['ব্যাংক স্টেটমেন্ট ২০২৬.pdf', '=HYPERLINK("x").pdf']
        make_pdf(deep / names[0], KNOWN)
        make_pdf(self.src / names[1], KNOWN)
        rows, done = self.run_batch(self.settings)
        mine = [r for r in rows if Path(r['source']).name in names]
        self.assertEqual([r['status'] for r in mine], ['Unlocked', 'Unlocked'], mine)
        if WINDOWS:
            longest = max(len(str(self.dst / r['relative'])) for r in mine)
            self.assertGreater(longest, 260)
        with open(done['report'], encoding='utf-8-sig', newline='') as fh:
            cells = [row['source'] for row in csv.DictReader(fh)]
        self.assertTrue(any(c.startswith("'=") for c in cells))
        self.assertFalse(any(c.startswith('=') for c in cells))
        self.assertTrue(any('ব্যাংক স্টেটমেন্ট' in c for c in cells))
        for row in mine:
            self.assertTrue(os.path.exists(core.fs(self.dst / row['relative'])))

    def test_analyze_and_dry_run_write_no_pdf(self):
        self.settings.dry_run = True
        rows, _ = self.run_batch(self.settings)
        self.assertTrue(all(r['status'] == 'DryRun' for r in rows))
        self.assertFalse(self.dst.exists())
        self.settings.dry_run = False
        self.settings.analyze_only = True
        rows, done = self.run_batch(self.settings)
        self.assertEqual(sorted(r['status'] for r in rows), ['PasswordRequired'] * 3 + ['PermissionRestricted', 'Unencrypted'])
        self.assertFalse(list(self.dst.rglob('*.pdf')))
        self.assertEqual(json.loads(Path(done['run']).read_text())['totals']['analyzed'], 5)

    def test_stale_partials_removed_and_never_scanned(self):
        self.dst.mkdir()
        stale = self.dst / f'old.pdf{core.TEMP_MARK}abc'
        stale.write_bytes(b'partial')
        legacy = self.dst / 'old2.pdf.rar-part-1-2'
        legacy.write_bytes(b'partial')
        self.run_batch(self.settings)
        self.assertFalse(stale.exists())
        self.assertFalse(legacy.exists())

    @unittest.skipIf(not WINDOWS and hasattr(os, 'geteuid') and os.geteuid() == 0, 'root ignores folder permissions')
    def test_read_only_output_folder_is_reported(self):
        self.dst.mkdir()
        if WINDOWS:
            user = os.environ['USERNAME']
            subprocess.run(['icacls', str(self.dst), '/deny', f'{user}:(W,AD)'], check=True, capture_output=True)
            self.addCleanup(subprocess.run, ['icacls', str(self.dst), '/remove:d', user], capture_output=True)
        else:
            os.chmod(self.dst, 0o500)
            self.addCleanup(os.chmod, self.dst, 0o700)
        with self.assertRaisesRegex(ValueError, 'Cannot write to the output folder'):
            self.run_batch(self.settings)

    @unittest.skipUnless(WINDOWS, 'Windows sharing modes')
    def test_locked_source_reports_file_locked(self):
        import ctypes
        from ctypes import wintypes
        path = self.src / 'Office' / 'Invoice-1042.pdf'
        k32 = ctypes.WinDLL('kernel32', use_last_error=True)
        k32.CreateFileW.restype = wintypes.HANDLE
        handle = k32.CreateFileW(str(path), 0x80000000, 0, None, 3, 0x80, None)  # GENERIC_READ, no sharing
        self.assertNotEqual(handle, wintypes.HANDLE(-1).value)
        try:
            rows, _ = self.run_batch(self.settings)
        finally:
            k32.CloseHandle(handle)
        by = {Path(r['source']).name: r['status'] for r in rows}
        self.assertEqual(by['Invoice-1042.pdf'], 'FileLocked')
        self.originals_unchanged()


if __name__ == '__main__':
    unittest.main()
