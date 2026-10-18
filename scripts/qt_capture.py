"""Render the real Qt GUI with synthetic fixtures and save screenshots.

Runs offscreen for determinism, exercises a real unlock through the engine,
asserts the expected result counts, and writes QA screenshots + a JSON record.
Synthetic data only.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication, QMessageBox
import qt_main
from branding import VERSION
from scripts.fixtures import create_fixtures, KNOWN

# Headless render: a modal dialog would block forever with no one to dismiss it.
# Correctness is still asserted from the result counts below.
for _name in ('information', 'warning', 'critical'):
    setattr(QMessageBox, _name, staticmethod(lambda *a, **k: QMessageBox.Ok))
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.No)


def grab(win, path):
    QApplication.processEvents()
    time.sleep(0.15)
    QApplication.processEvents()
    win.grab().save(str(path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', default='qa/screenshots')
    ap.add_argument('--workspace', default='qa/demo')
    args = ap.parse_args()
    out = Path(args.output).resolve(); out.mkdir(parents=True, exist_ok=True)
    root = Path(args.workspace).resolve()
    src = create_fixtures(root).resolve()
    dest = root / 'Output'
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in src.rglob('*.pdf')}

    app = QApplication.instance() or QApplication(sys.argv)
    win = qt_main.MainWindow(); win.resize(1320, 900); win.show()
    QApplication.processEvents()

    win.navigate('workspace')
    win.source_edit.setText(str(src)); win.output_edit.setText(str(dest))
    win.password_groups['General'].append(KNOWN)
    grab(win, out / 'workspace.png')

    win.navigate('tools'); grab(win, out / 'tools.png')
    win.navigate('passwords'); grab(win, out / 'passwords.png')
    win.navigate('settings'); grab(win, out / 'settings.png')

    win.navigate('workspace'); win._start_unlock()
    deadline = time.time() + 90
    while win.busy and time.time() < deadline:
        QApplication.processEvents(); time.sleep(0.02)
    if win.busy:
        raise SystemExit('Qt GUI batch did not finish')
    counts = dict(win.counts)
    expected = {'Unlocked': 3, 'PasswordNotMatched': 1, 'SkippedUnencrypted': 1}
    if counts != expected:
        raise SystemExit(f'Qt GUI results differ: {counts}')
    grab(win, out / 'workspace-done.png')
    win.navigate('results'); grab(win, out / 'results.png')

    after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in src.rglob('*.pdf')}
    if before != after:
        raise SystemExit('Source files changed')
    report = Path(win.last_report)
    if not report.is_file() or KNOWN in report.read_text(encoding='utf-8-sig'):
        raise SystemExit('Report missing or leaked a password')

    (out.parent / 'source-gui-validation.json').write_text(json.dumps({
        'toolkit': 'PySide6/Qt', 'app_version': VERSION, 'platform': sys.platform,
        'counts': counts, 'originals_unchanged': before == after,
        'password_absent_from_report': True,
        'screenshots': 'Offscreen Qt renders with synthetic fixtures only',
    }, indent=2), encoding='utf-8')
    print('Qt GUI screenshots and validation written:', counts)


if __name__ == '__main__':
    main()
