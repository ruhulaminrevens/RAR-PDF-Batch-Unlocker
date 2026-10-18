"""PDF tools page and worker for the Qt interface. Logic stays in toolkit.py."""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QInputDialog, QLineEdit,
                               QListWidget, QMessageBox, QPushButton, QVBoxLayout, QWidget)

import diagnostics
import qt_theme as T
from qt_widgets import Card, icon_button, label

IMAGE_FILTER = 'Images (*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff *.webp);;All files (*)'
PDF_FILTER = 'PDF files (*.pdf);;All files (*)'


class ToolWorker(QObject):
    done = Signal(object, str)      # (toolkit.Result, output_dir)
    failed = Signal(str)
    need_password = Signal()

    def __init__(self, make_call, open_target):
        super().__init__()
        self.make_call = make_call
        self.open_target = open_target
        self.password = None

    def run(self):
        import toolkit
        try:
            try:
                result = self.make_call(self.password)
            except toolkit.PasswordNeeded:
                if self.password is None:
                    self.need_password.emit(); return
                raise
            self.done.emit(result, str(self.open_target))
        except toolkit.ToolkitError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # pragma: no cover
            diagnostics.log_exception(type(exc), exc, exc.__traceback__, 'qt-tool')
            self.failed.emit(f'Unexpected error: {type(exc).__name__}')


class ToolsPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName('PageBody')
        self.host = host  # MainWindow, for busy state
        self.thread = None
        self.worker = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 26, 32, 28)
        lay.setSpacing(18)
        from qt_widgets import eyebrow_title
        lay.addLayout(eyebrow_title('OFFLINE PDF TOOLKIT', 'PDF tools'))
        self.status = label('Choose a tool below. Protected PDFs ask for their open password. Nothing is uploaded.', 'muted')
        self.status.setWordWrap(True)
        lay.addWidget(self.status)

        lay.addWidget(self._merge_card())
        lay.addWidget(self._split_card())
        lay.addWidget(self._images_card())
        lay.addWidget(self._raster_card())
        lay.addWidget(self._convert_card())
        lay.addStretch(1)

    # ---- cards ----
    def _list_box(self, kind) -> QListWidget:
        from qt_widgets import DropList
        box = DropList(lambda paths: self.add_paths(box, kind, paths))
        box.setFixedHeight(104)
        return box

    def _list_buttons(self, box, kind):
        row = QHBoxLayout(); row.setSpacing(8)
        label_txt = 'Add images…' if kind == 'img' else 'Add PDFs…'
        row.addWidget(icon_button('tools', T.MUTED, label_txt, on_click=lambda: self._add(box, kind)))
        row.addWidget(QPushButton('Remove', clicked=lambda: self._remove(box)))
        row.addWidget(QPushButton('Up', clicked=lambda: self._move(box, -1)))
        row.addWidget(QPushButton('Down', clicked=lambda: self._move(box, 1)))
        row.addWidget(QPushButton('Clear', clicked=lambda: self._clear(box)))
        row.addStretch(1)
        return row

    def _merge_card(self):
        c = Card(accent=T.CYAN, pad=(22, 20, 22, 22))
        c.add(label('Merge PDFs', 'section'))
        c.add(label('Combine several PDFs into one, in the order shown. Drag files in or use Up/Down.', 'muted'))
        self.merge_list = self._list_box("pdf"); c.add(self.merge_list)
        c.add_layout(self._list_buttons(self.merge_list, 'pdf'))
        c.add(icon_button('merge', '#fff', 'Merge into one PDF…', kind='primary', on_click=self._merge))
        return c

    def _split_card(self):
        c = Card(accent=T.VIOLET, pad=(22, 20, 22, 22))
        c.add(label('Split & organize', 'section'))
        c.add(label('Split each page into its own file, or keep/reorder/rotate pages like 1,3-5,8.', 'muted'))
        self.split_input = self._file_row(c, 'Source PDF')
        row = QHBoxLayout(); row.setSpacing(10)
        row.addWidget(label('Pages', 'muted'))
        self.split_pages = QLineEdit(); self.split_pages.setPlaceholderText('e.g. 1,3-5,8'); row.addWidget(self.split_pages, 1)
        row.addWidget(label('Rotate', 'muted'))
        self.split_rotate = QComboBox(); self.split_rotate.addItems(['0', '90', '180', '270']); row.addWidget(self.split_rotate)
        c.add_layout(row)
        btns = QHBoxLayout(); btns.setSpacing(10)
        btns.addWidget(icon_button('split', '#fff', 'Split every page…', kind='primary', on_click=lambda: self._split('each')))
        btns.addWidget(QPushButton('Export selected pages…', clicked=lambda: self._split('keep')))
        btns.addStretch(1)
        c.add_layout(btns)
        return c

    def _images_card(self):
        c = Card(accent=T.GREEN, pad=(22, 20, 22, 22))
        c.add(label('Images → PDF', 'section'))
        c.add(label('Combine jpg, png, bmp, tiff or webp images into one PDF, in the order shown.', 'muted'))
        self.img_list = self._list_box("img"); c.add(self.img_list)
        c.add_layout(self._list_buttons(self.img_list, 'img'))
        c.add(icon_button('image', '#fff', 'Make PDF from images…', kind='primary', on_click=self._images))
        return c

    def _raster_card(self):
        c = Card(accent=T.AMBER, pad=(22, 20, 22, 22))
        c.add(label('PDF → images', 'section'))
        c.add(label('Save each page as an image. Larger DPI is sharper and bigger. Keeps the exact layout.', 'muted'))
        self.raster_input = self._file_row(c, 'Source PDF')
        row = QHBoxLayout(); row.setSpacing(10)
        row.addWidget(label('Format', 'muted'))
        self.raster_fmt = QComboBox(); self.raster_fmt.addItems(['png', 'jpg', 'tiff', 'webp']); row.addWidget(self.raster_fmt)
        row.addWidget(label('DPI', 'muted'))
        self.raster_dpi = QComboBox(); self.raster_dpi.addItems(['72', '100', '150', '200', '300']); self.raster_dpi.setCurrentText('150'); row.addWidget(self.raster_dpi)
        row.addStretch(1)
        c.add_layout(row)
        c.add(icon_button('export', '#fff', 'Export pages as images…', kind='primary', on_click=self._raster))
        return c

    def _convert_card(self):
        c = Card(accent='#8fd9e6', pad=(22, 20, 22, 22))
        head = QHBoxLayout()
        head.addWidget(label('PDF → Word / Excel', 'section'))
        from qt_widgets import Chip
        head.addWidget(Chip('DRAFT', T.AMBER, dot=False))
        head.addStretch(1)
        c.add_layout(head)
        c.add(label('Text-based export. Scanned (image-only) PDFs need OCR, which is not included — use PDF → images for those.', 'muted'))
        self.convert_input = self._file_row(c, 'Source PDF')
        btns = QHBoxLayout(); btns.setSpacing(10)
        btns.addWidget(icon_button('doc', '#fff', 'Export to Word (.docx)…', kind='primary', on_click=lambda: self._convert('docx')))
        btns.addWidget(QPushButton('Export to Excel (.xlsx)…', clicked=lambda: self._convert('xlsx')))
        btns.addStretch(1)
        c.add_layout(btns)
        return c

    def _file_row(self, card, text) -> QLineEdit:
        row = QHBoxLayout(); row.setSpacing(10)
        row.addWidget(label(text, 'muted'))
        edit = QLineEdit(); edit.setProperty('mono', 'true'); row.addWidget(edit, 1)
        row.addWidget(QPushButton('Browse', clicked=lambda: self._pick(edit)))
        card.add_layout(row)
        return edit

    # ---- list helpers ----
    def _add(self, box, kind):
        if self.host.busy:
            return
        files, _ = QFileDialog.getOpenFileNames(self, 'Add files', '', IMAGE_FILTER if kind == 'img' else PDF_FILTER)
        self.add_paths(box, kind, files)

    def add_paths(self, box, kind, paths):
        from qt_main import IMAGE_EXTS
        exts = IMAGE_EXTS if kind == 'img' else {'.pdf'}
        known = {os.path.normcase(os.path.abspath(p)) for p in box._paths}
        for f in paths:
            p = Path(f)
            targets = [s for s in sorted(p.rglob('*')) if s.is_file() and s.suffix.lower() in exts] if p.is_dir() else \
                ([p] if p.suffix.lower() in exts and p.is_file() else [])
            for s in targets:
                k = os.path.normcase(os.path.abspath(s))
                if k not in known:
                    box._paths.append(str(s)); known.add(k); box.addItem(s.name)

    def _remove(self, box):
        for i in sorted((box.row(it) for it in box.selectedItems()), reverse=True):
            del box._paths[i]; box.takeItem(i)

    def _clear(self, box):
        box._paths.clear(); box.clear()

    def _move(self, box, delta):
        i = box.currentRow(); j = i + delta
        if i < 0 or not 0 <= j < len(box._paths):
            return
        box._paths[i], box._paths[j] = box._paths[j], box._paths[i]
        it = box.takeItem(i); box.insertItem(j, it); box.setCurrentRow(j)

    def _pick(self, edit):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose PDF', '', PDF_FILTER)
        if path:
            edit.setText(path)

    # ---- run ----
    def _save_as(self, default, filt):
        path, _ = QFileDialog.getSaveFileName(self, 'Save as', default, filt)
        return Path(path) if path else None

    def _save_dir(self):
        path = QFileDialog.getExistingDirectory(self, 'Choose output folder')
        return Path(path) if path else None

    def _run(self, make_call, open_target):
        if self.host.busy:
            return
        self.host.set_busy(True)
        self.status.setText('Working…')
        self.thread = QThread()
        self.worker = ToolWorker(make_call, open_target)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.done.connect(self._done)
        self.worker.failed.connect(self._failed)
        self.worker.need_password.connect(self._need_password)
        self.thread.start()

    def _end_thread(self):
        if self.thread:
            self.thread.quit(); self.thread.wait(); self.thread = None

    def _done(self, result, open_target):
        self._end_thread(); self.host.set_busy(False)
        self.status.setText(f'Done — {result.note}. Saved to: {Path(open_target)}')
        if QMessageBox.question(self, 'Finished', f'{result.note}.\n\nOpen the output folder?') == QMessageBox.Yes:
            self.host.open_path(open_target)

    def _failed(self, message):
        self._end_thread(); self.host.set_busy(False)
        self.status.setText('Could not finish: ' + message)
        QMessageBox.critical(self, 'PDF tools', message)

    def _need_password(self):
        pw, ok = QInputDialog.getText(self, 'Protected PDF', 'This PDF needs its open password:', QLineEdit.Password)
        make_call = self.worker.make_call; target = self.worker.open_target
        self._end_thread()
        if not ok or not pw:
            self.host.set_busy(False); self.status.setText('Cancelled — the PDF is password-protected.'); return
        diagnostics.remember_secret(pw)
        self.thread = QThread()
        self.worker = ToolWorker(make_call, target); self.worker.password = pw
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.done.connect(self._done); self.worker.failed.connect(self._failed)
        self.worker.need_password.connect(lambda: self._failed('The supplied password did not open the PDF.'))
        self.thread.start()

    def _merge(self):
        import toolkit
        if len(self.merge_list._paths) < 2:
            QMessageBox.information(self, 'Merge', 'Add at least two PDFs.'); return
        out = self._save_as('merged.pdf', 'PDF (*.pdf)')
        if out:
            paths = [Path(p) for p in self.merge_list._paths]
            self._run(lambda pw: toolkit.merge_pdfs(paths, out), out.parent)

    def _split(self, mode):
        import toolkit
        src = self.split_input.text().strip()
        if not src:
            QMessageBox.information(self, 'Split', 'Choose a source PDF.'); return
        rotate = int(self.split_rotate.currentText())
        if mode == 'each':
            out = self._save_dir()
            if out:
                self._run(lambda pw: toolkit.split_pdf(Path(src), out, password=pw), out)
        else:
            spec = self.split_pages.text().strip()
            if not spec:
                QMessageBox.information(self, 'Export pages', 'Enter page numbers, e.g. 1,3-5.'); return
            out = self._save_as(Path(src).stem + '-pages.pdf', 'PDF (*.pdf)')
            if out:
                def call(pw):
                    n = toolkit.page_count(Path(src), pw)
                    keep = toolkit.parse_page_spec(spec, n)
                    rot = {p: rotate for p in keep} if rotate else None
                    return toolkit.organize_pdf(Path(src), out, keep=keep, rotations=rot, password=pw)
                self._run(call, out.parent)

    def _images(self):
        import toolkit
        if not self.img_list._paths:
            QMessageBox.information(self, 'Images → PDF', 'Add at least one image.'); return
        out = self._save_as('images.pdf', 'PDF (*.pdf)')
        if out:
            paths = [Path(p) for p in self.img_list._paths]
            self._run(lambda pw: toolkit.images_to_pdf(paths, out), out.parent)

    def _raster(self):
        import toolkit
        src = self.raster_input.text().strip()
        if not src:
            QMessageBox.information(self, 'PDF → images', 'Choose a source PDF.'); return
        out = self._save_dir()
        if out:
            fmt = self.raster_fmt.currentText(); dpi = int(self.raster_dpi.currentText())
            self._run(lambda pw: toolkit.pdf_to_images(Path(src), out, fmt=fmt, dpi=dpi, password=pw), out)

    def _convert(self, kind):
        import toolkit
        src = self.convert_input.text().strip()
        if not src:
            QMessageBox.information(self, 'Convert', 'Choose a source PDF.'); return
        out = self._save_as(Path(src).stem + '.' + kind, f'{kind.upper()} (*.{kind})')
        if out:
            fn = toolkit.pdf_to_docx if kind == 'docx' else toolkit.pdf_to_xlsx
            self._run(lambda pw: fn(Path(src), out, password=pw), out.parent)
