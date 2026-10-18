"""RAR PDF Batch Unlocker — PySide6 desktop GUI. Engine and logic stay in
core.py / toolkit.py / reports.py / vault.py / diagnostics.py."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys
import threading

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal, QSize
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout,
                               QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton,
                               QScrollArea, QStackedWidget, QVBoxLayout, QWidget)

import core
import diagnostics
from branding import APP_NAME, VERSION
import qt_theme as T
from qt_widgets import (Card, Chip, DropLineEdit, MetricTile, NavButton, eyebrow_title,
                        icon_button, label, shadow)
from qt_pages import PagesMixin

NAV = [('workspace', 'Batch workspace', 'workspace'), ('passwords', 'Passwords', 'key'),
       ('results', 'Results & reports', 'results'), ('tools', 'PDF tools', 'tools'),
       ('settings', 'Run settings', 'settings'), ('help', 'About & help', 'help')]

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tif', '.tiff', '.webp'}


def find_qpdf() -> str:
    here = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    for c in [Path(sys.executable).resolve().parent / 'qpdf' / 'bin' / 'qpdf.exe',
              here / 'qpdf' / 'bin' / 'qpdf.exe']:
        if c.is_file():
            return str(c)
    return shutil.which('qpdf') or ''


class UnlockWorker(QObject):
    event = Signal(str, object)
    finished = Signal()

    def __init__(self, settings, stop):
        super().__init__()
        self.settings = settings
        self.stop = stop

    def run(self):
        try:
            core.process(self.settings, lambda kind, payload: self.event.emit(kind, payload), self.stop)
        except Exception as exc:  # pragma: no cover - surfaced to UI
            diagnostics.log_exception(type(exc), exc, exc.__traceback__, 'qt-unlock')
            self.event.emit('error', str(exc))
        finally:
            self.finished.emit()


def scroll_page(build) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    body = QWidget()
    body.setObjectName('PageBody')
    lay = QVBoxLayout(body)
    lay.setContentsMargins(32, 26, 32, 28)
    lay.setSpacing(18)
    build(lay)
    lay.addStretch(1)
    area.setWidget(body)
    return area


class MainWindow(PagesMixin, QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName('Root')
        self.setWindowTitle(f'{APP_NAME} · {VERSION}')
        self.resize(1280, 840)
        self.setMinimumSize(980, 640)
        self.setStyleSheet(T.stylesheet())
        diagnostics.install_qt(self) if hasattr(diagnostics, 'install_qt') else None

        self.qpdf = find_qpdf()
        self.password_groups = {'General': []}
        self.extra_files: list[str] = []
        self.stop_flag = threading.Event()
        self.thread = None
        self.worker = None
        self.busy = False
        self.counts: dict[str, int] = {}
        self.total = 0
        self.completed = 0
        self.last_report = ''
        self.last_html = ''
        self.last_output = ''

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._sidebar())
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        from qt_tools import ToolsPage
        self.pages = {}
        self.pages['workspace'] = scroll_page(self._workspace)
        tools_area = QScrollArea(); tools_area.setWidgetResizable(True)
        tools_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tools_page = ToolsPage(self); tools_area.setWidget(self.tools_page)
        self.pages['tools'] = tools_area
        self.pages['passwords'] = self.build_passwords()
        self.pages['results'] = self.build_results()
        self.pages['settings'] = self.build_settings()
        self.pages['help'] = self.build_help()
        self._pw_update_count()
        for key, _, _ in NAV:
            self.stack.addWidget(self.pages[key])
        self.navigate('workspace')

    # ---- sidebar ----
    def _sidebar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName('Sidebar')
        bar.setFixedWidth(244)
        lay = QVBoxLayout(bar)
        lay.setContentsMargins(18, 26, 18, 20)
        lay.setSpacing(6)
        brand = QHBoxLayout(); brand.setSpacing(12)
        mark = QLabel(); mark.setPixmap(T.pixmap('brand', T.CYAN, 22)); mark.setFixedSize(42, 42)
        mark.setAlignment(Qt.AlignCenter)
        mark.setStyleSheet(f'background:#0f2036;border:1px solid #27476f;border-radius:13px;')
        brand.addWidget(mark)
        names = QVBoxLayout(); names.setSpacing(0)
        names.addWidget(label('RAR PDF', 'brand'))
        names.addWidget(label('UNLOCKER', 'brandsub'))
        brand.addLayout(names); brand.addStretch(1)
        wrap = QWidget(); wrap.setLayout(brand); wrap.setStyleSheet('background:transparent;')
        lay.addWidget(wrap)
        lay.addSpacing(18)
        self.nav_buttons = {}
        for key, text, ico in NAV:
            btn = NavButton(key, text, ico, self.navigate)
            self.nav_buttons[key] = btn
            lay.addWidget(btn)
        lay.addStretch(1)
        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet(f'background:{T.BORDER_SOFT};')
        lay.addWidget(sep)
        priv = QHBoxLayout(); priv.setSpacing(8)
        dot = QLabel(); dot.setFixedSize(7, 7); dot.setStyleSheet(f'background:{T.GREEN};border-radius:3px;')
        priv.addWidget(dot)
        p = QLabel('LOCAL · PRIVATE · OFFLINE'); p.setStyleSheet(f'color:{T.GREEN};font-size:10.5px;font-weight:600;letter-spacing:0.8px;background:transparent;')
        priv.addWidget(p); priv.addStretch(1)
        pw = QWidget(); pw.setLayout(priv); pw.setStyleSheet('background:transparent;')
        lay.addSpacing(10); lay.addWidget(pw)
        ver = QLabel(f'v{VERSION} · qpdf'); ver.setProperty('kind', 'mono'); ver.setStyleSheet(f'color:{T.FAINT};font-size:11px;font-family:{T.MONO};background:transparent;')
        lay.addWidget(ver)
        return bar

    def navigate(self, key: str):
        self.stack.setCurrentWidget(self.pages[key])
        for k, btn in self.nav_buttons.items():
            btn.set_active(k == key)

    def _placeholder(self, key: str) -> QWidget:
        titles = {k: t for k, t, _ in NAV}
        def build(lay):
            lay.addLayout(eyebrow_title('COMING NEXT', titles[key]))
            lay.addWidget(label('This page is being built in the Qt redesign.', 'muted'))
        return scroll_page(build)

    # ---- workspace ----
    def _workspace(self, lay):
        head = QHBoxLayout()
        head.addLayout(eyebrow_title('SECURE OFFLINE WORKSPACE', 'Your PDFs, unlocked.'))
        head.addStretch(1)
        chip = Chip('No upload · on this PC', T.CYAN)
        head.addWidget(chip, 0, Qt.AlignBottom)
        lay.addLayout(head)

        metrics = QHBoxLayout(); metrics.setSpacing(14)
        self.metrics = {}
        for key, cap, color in [('total', 'PDFs in scan', T.CYAN), ('unlocked', 'Unlocked', T.GREEN),
                                ('attention', 'Need attention', T.AMBER), ('skipped', 'Skipped', T.VIOLET)]:
            tile = MetricTile(cap, color)
            self.metrics[key] = tile
            metrics.addWidget(tile)
        lay.addLayout(metrics)

        inputs = Card(pad=(22, 20, 22, 22))
        row = QHBoxLayout()
        row.addWidget(label('Inputs & output', 'section'))
        row.addStretch(1)
        row.addWidget(label('Drag a folder or PDFs onto the boxes', 'faint'))
        inputs.add_layout(row)
        self.source_edit = self._path_row(inputs, 'SOURCE FOLDER', folder=True, on_drop=self._drop_source)
        self.output_edit = self._path_row(inputs, 'OUTPUT FOLDER', folder=True, on_drop=self._drop_output)
        files_row = QHBoxLayout()
        self.files_label = label('No single PDFs added — use a folder, add PDFs, or both', 'faint')
        files_row.addWidget(self.files_label, 1)
        files_row.addWidget(icon_button('tools', T.MUTED, 'Add PDFs…', on_click=self._add_files))
        files_row.addWidget(QPushButton('Clear', clicked=self._clear_files))
        inputs.add_layout(files_row)
        lay.addWidget(inputs)

        run = Card(pad=(22, 18, 22, 20))
        bar = QHBoxLayout(); bar.setSpacing(12)
        self.unlock_btn = icon_button('play', '#fff', 'Unlock batch', kind='primary', on_click=self._start_unlock)
        bar.addWidget(self.unlock_btn)
        self.stop_btn = icon_button('stop', T.RED, 'Stop safely', kind='danger', on_click=self._stop)
        self.stop_btn.setEnabled(False)
        bar.addWidget(self.stop_btn)
        bar.addStretch(1)
        self.progress_label = label('0 / 0', 'mono')
        bar.addWidget(self.progress_label)
        run.add_layout(bar)
        self.progress = QProgressBar(); self.progress.setTextVisible(False); self.progress.setRange(0, 100); self.progress.setValue(0)
        run.add(self.progress)
        self.timing_label = label('Ready when you are. Choose your folders to begin.', 'faint')
        run.add(self.timing_label)
        lay.addWidget(run)

        prev = Card(pad=(22, 18, 22, 18))
        prev.add(label('Latest results', 'section'))
        self.preview = label('Run a batch to see results here.', 'muted'); self.preview.setWordWrap(True)
        prev.add(self.preview)
        lay.addWidget(prev)

    def _path_row(self, card: Card, text: str, folder: bool, on_drop=None) -> QLineEdit:
        card.add(label(text, 'fieldlabel'))
        row = QHBoxLayout(); row.setSpacing(10)
        edit = DropLineEdit(on_drop) if on_drop else QLineEdit()
        edit.setProperty('mono', 'true'); edit.setPlaceholderText('— drop a folder or PDFs here —')
        row.addWidget(edit, 1)
        browse = QPushButton('Browse')
        browse.clicked.connect(lambda: self._browse(edit, folder))
        row.addWidget(browse)
        card.add_layout(row)
        return edit

    # ---- actions ----
    def _browse(self, edit: QLineEdit, folder: bool):
        path = QFileDialog.getExistingDirectory(self, 'Choose folder') if folder else \
            QFileDialog.getOpenFileName(self, 'Choose file')[0]
        if path:
            edit.setText(path)

    def _add_files(self):
        if self.busy:
            return
        files, _ = QFileDialog.getOpenFileNames(self, 'Add PDF files', '', 'PDF files (*.pdf);;All files (*)')
        known = {os.path.normcase(os.path.abspath(f)) for f in self.extra_files}
        for f in files:
            k = os.path.normcase(os.path.abspath(f))
            if k not in known:
                self.extra_files.append(f); known.add(k)
        self._files_changed()

    def _clear_files(self):
        if self.busy:
            return
        self.extra_files.clear(); self._files_changed()

    def _files_changed(self):
        n = len(self.extra_files)
        if not n:
            self.files_label.setText('No single PDFs added — use a folder, add PDFs, or both')
        else:
            names = ', '.join(Path(f).name for f in self.extra_files[:3]) + (' …' if n > 3 else '')
            self.files_label.setText(f'{n} PDF{"s" if n != 1 else ""}: {names}')

    def _drop_source(self, paths):
        if self.busy:
            return
        dirs = [p for p in paths if Path(p).is_dir()]
        pdfs = [p for p in paths if Path(p).is_file() and Path(p).suffix.lower() == '.pdf']
        if dirs:
            self.source_edit.setText(dirs[0])
        if pdfs:
            self._add_extra_files(pdfs)

    def _drop_output(self, paths):
        if self.busy:
            return
        dirs = [p for p in paths if Path(p).is_dir()]
        if dirs:
            self.output_edit.setText(dirs[0])

    def _add_extra_files(self, paths):
        known = {os.path.normcase(os.path.abspath(f)) for f in self.extra_files}
        for f in paths:
            p = Path(f)
            if p.is_file() and p.suffix.lower() == '.pdf':
                k = os.path.normcase(os.path.abspath(p))
                if k not in known:
                    self.extra_files.append(str(p)); known.add(k)
        self._files_changed()

    def _start_unlock(self):
        if self.busy:
            return
        try:
            settings = self.assemble_settings()
        except Exception as exc:
            QMessageBox.warning(self, 'Configuration', str(exc)); return
        self.stop_flag = threading.Event()
        self.counts = {}; self.total = 0; self.completed = 0
        self.last_output = str(settings.destination)
        self.clear_results()
        self._set_busy(True)
        self.timing_label.setText('Processing…')
        self.preview.setText('')
        self.thread = QThread()
        self.worker = UnlockWorker(settings, self.stop_flag)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.event.connect(self._on_event)
        # Canonical cleanup: never block the GUI thread with thread.wait().
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._run_finished)
        self.thread.start()

    def _stop(self):
        self.stop_flag.set()
        self.stop_btn.setEnabled(False)
        self.timing_label.setText('Stopping after the current qpdf step…')

    def _on_event(self, kind: str, payload):
        if kind == 'scan':
            self.total = payload['count']; self.metrics['total'].set(self.total)
        elif kind == 'result':
            self.completed = payload['index']; self.total = payload['total']
            self.counts[payload['status']] = self.counts.get(payload['status'], 0) + 1
            pct = int(100 * self.completed / self.total) if self.total else 0
            self.progress.setValue(pct)
            self.progress_label.setText(f'{self.completed} / {self.total} · {pct}%')
            self._update_metrics()
            self.add_result_row(payload)
            name = payload.get('relative') or Path(payload['source']).name
            self.preview.setText(f"{payload['status']} — {name}")
        elif kind == 'done':
            summary = payload.get('summary') or {}
            elapsed = summary.get('elapsed_seconds')
            self.last_report = payload.get('report') or ''
            self.last_html = payload.get('html') or ''
            state = 'Stopped: output drive full' if payload.get('halted') == 'DiskFull' else \
                'Stopped safely' if payload.get('cancelled') else 'Complete'
            self.timing_label.setText(f"{state} · {self.completed} of {self.total} PDFs" + (f' · {elapsed:.1f}s' if elapsed else ''))
            if hasattr(self, 'report_label'):
                self.report_label.setText(f'CSV: {self.last_report}' if self.last_report else 'No report (dry run).')
        elif kind == 'error':
            self.timing_label.setText('Could not finish — see the error.')
            QMessageBox.critical(self, 'Processing error', str(payload))

    def _update_metrics(self):
        self.metrics['total'].set(self.total)
        self.metrics['unlocked'].set(self.counts.get('Unlocked', 0) + self.counts.get('CopiedUnencrypted', 0))
        self.metrics['attention'].set(sum(v for k, v in self.counts.items() if k in core.FAILED))
        self.metrics['skipped'].set(sum(v for k, v in self.counts.items() if k.startswith('Skipped') or k == 'DryRun'))

    def _run_finished(self):
        self.thread = None
        self.worker = None
        self._set_busy(False)

    def _set_busy(self, value: bool):
        self.busy = value
        self.unlock_btn.setEnabled(not value)
        self.stop_btn.setEnabled(value)

    def set_busy(self, value: bool):
        self._set_busy(value)

    def open_path(self, path):
        import subprocess
        p = Path(path)
        if not p.exists():
            QMessageBox.information(self, 'Not available', 'The file or folder no longer exists.'); return
        try:
            if sys.platform == 'win32':
                os.startfile(str(p.resolve()))
            else:
                subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', str(p.resolve())])
        except OSError as exc:
            QMessageBox.warning(self, 'Could not open', str(exc))


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
