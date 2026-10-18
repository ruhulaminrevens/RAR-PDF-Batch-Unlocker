"""Passwords, Results, Run settings and About pages for the Qt interface,
as a mixin on the main window. Engine/logic stay in core/toolkit/vault."""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QHBoxLayout,
                               QHeaderView, QInputDialog, QLineEdit, QMessageBox, QPlainTextEdit,
                               QPushButton, QRadioButton, QScrollArea, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

import core
import diagnostics
import qt_theme as T
from qt_widgets import Card, Chip, eyebrow_title, icon_button, label

STATUS_LABEL = {
    'Unlocked': 'Unlocked', 'CopiedUnencrypted': 'Copied', 'PasswordNotMatched': 'No match',
    'PasswordRequired': 'Password required', 'PermissionRestricted': 'Permission only',
    'Unencrypted': 'Unencrypted', 'SkippedUnencrypted': 'Already open', 'SkippedExisting': 'Output exists',
    'InvalidPDF': 'Invalid PDF', 'InspectionFailed': 'Inspection failed', 'VerificationFailed': 'Verify failed',
    'DecryptFailed': 'Rebuild failed', 'Timeout': 'Timed out', 'Error': 'Error', 'Cancelled': 'Cancelled',
    'DryRun': 'Dry run', 'FileLocked': 'File locked', 'AccessDenied': 'Access denied', 'DiskFull': 'Disk full',
    'PathTooLong': 'Path too long', 'SourceMissing': 'Source missing', 'OutputConflict': 'Name conflict',
}


def _scroll(build) -> QScrollArea:
    area = QScrollArea(); area.setWidgetResizable(True); area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    body = QWidget(); body.setObjectName('PageBody')
    lay = QVBoxLayout(body); lay.setContentsMargins(32, 26, 32, 28); lay.setSpacing(18)
    build(lay); lay.addStretch(1)
    area.setWidget(body)
    return area


class PagesMixin:
    # ---------------------------------------------------------------- passwords
    def build_passwords(self) -> QScrollArea:
        def build(lay):
            lay.addLayout(eyebrow_title('KNOWN PASSWORDS', 'Private by default.'))
            lay.addWidget(label('Passwords stay in this session unless you save a named Windows vault entry. '
                                'They never appear in reports or logs.', 'muted'))
            card = Card(pad=(22, 20, 22, 22))
            card.add(label('Session password groups', 'section'))
            card.add(label('A matching folder group is tried first, then General.', 'muted'))
            row = QHBoxLayout(); row.setSpacing(10)
            self.group_combo = QComboBox(); self.group_combo.addItems(list(self.password_groups)); self.group_combo.setMinimumWidth(180)
            self.group_combo.currentTextChanged.connect(lambda *_: self._pw_update_count())
            row.addWidget(self.group_combo)
            row.addWidget(QPushButton('New group', clicked=self._pw_new_group))
            row.addStretch(1)
            row.addWidget(QPushButton('Delete group', clicked=self._pw_delete_group))
            row.addWidget(QPushButton('Clear group', clicked=self._pw_clear))
            card.add_layout(row)
            self.pw_count = label('0 passwords in General (values hidden)', 'faint'); card.add(self.pw_count)
            entry = QHBoxLayout(); entry.setSpacing(10)
            self.pw_entry = QLineEdit(); self.pw_entry.setEchoMode(QLineEdit.Password); self.pw_entry.setPlaceholderText('Type a known password')
            self.pw_entry.returnPressed.connect(self._pw_add)
            entry.addWidget(self.pw_entry, 1)
            self.show_pw = QCheckBox('Show'); self.show_pw.toggled.connect(self._pw_toggle_show); entry.addWidget(self.show_pw)
            entry.addWidget(icon_button('key', '#fff', 'Add to group', kind='primary', on_click=self._pw_add))
            card.add_layout(entry)
            lay.addWidget(card)

            mp = Card(pad=(22, 20, 22, 22))
            mp.add(label('Folder → group mapping', 'section'))
            mp.add(label('One relative folder=Group per line. The most specific folder wins. Example: Statements=Bank', 'muted'))
            self.mapping_text = QPlainTextEdit(); self.mapping_text.setFixedHeight(96)
            self.mapping_text.setStyleSheet(f'background:{T.INPUT};border:1px solid #21314f;border-radius:11px;font-family:{T.MONO};')
            mp.add(self.mapping_text)
            lay.addWidget(mp)

            vault = Card(pad=(22, 20, 22, 22))
            vault.add(label('Windows Credential Locker · optional', 'section'))
            vault.add(label('Save the password in the entry box, or load a named credential into the selected group. '
                            'Uses your Windows account store; no password file is created.', 'muted'))
            vrow = QHBoxLayout(); vrow.setSpacing(10)
            vrow.addWidget(QPushButton('Save entered password', clicked=lambda: self._vault('save')))
            vrow.addWidget(QPushButton('Load saved password', clicked=lambda: self._vault('load')))
            vrow.addWidget(QPushButton('Delete saved password', clicked=lambda: self._vault('delete')))
            vrow.addStretch(1)
            vault.add_layout(vrow)
            lay.addWidget(vault)
        return _scroll(build)

    def _pw_update_count(self):
        g = self.group_combo.currentText()
        self.pw_count.setText(f'{len(self.password_groups.get(g, []))} passwords in {g} (values hidden)')

    def _pw_toggle_show(self, on):
        self.pw_entry.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password)

    def _pw_new_group(self):
        name, ok = QInputDialog.getText(self, 'New group', 'Label (e.g. Bank or Office):')
        name = (name or '').strip()
        if ok and name and name not in self.password_groups and not any(c in name for c in '=\r\n'):
            self.password_groups[name] = []
            self.group_combo.addItem(name); self.group_combo.setCurrentText(name); self._pw_update_count()

    def _pw_delete_group(self):
        g = self.group_combo.currentText()
        if g == 'General':
            QMessageBox.information(self, 'Delete group', 'The General group cannot be deleted.'); return
        if QMessageBox.question(self, 'Delete group', f'Delete the group “{g}” and its session passwords?') == QMessageBox.Yes:
            self.password_groups.pop(g, None)
            self.group_combo.removeItem(self.group_combo.currentIndex()); self.group_combo.setCurrentText('General'); self._pw_update_count()

    def _pw_add(self):
        pw = self.pw_entry.text(); self.pw_entry.clear()
        if self.busy or not pw or '\n' in pw or '\r' in pw:
            return
        diagnostics.remember_secret(pw)
        arr = self.password_groups.setdefault(self.group_combo.currentText(), [])
        if pw not in arr:
            arr.append(pw)
        self._pw_update_count()

    def _pw_clear(self):
        self.password_groups[self.group_combo.currentText()].clear(); self.pw_entry.clear(); self._pw_update_count()

    def _vault(self, action):
        name, ok = QInputDialog.getText(self, 'Windows Credential Locker', 'Vault entry name (not the password):')
        if not ok or not name:
            return
        try:
            import vault
            if action == 'save':
                vault.save(name, self.pw_entry.text()); self.pw_entry.clear()
                QMessageBox.information(self, 'Saved', 'Password stored in your Windows Credential Locker.')
            elif action == 'load':
                value = vault.load(name)
                if value:
                    diagnostics.remember_secret(value)
                    arr = self.password_groups.setdefault(self.group_combo.currentText(), [])
                    if value not in arr:
                        arr.append(value)
                    self._pw_update_count(); QMessageBox.information(self, 'Loaded', 'Password loaded into the current group.')
                else:
                    QMessageBox.information(self, 'Not found', 'No stored credential with this name.')
            else:
                if QMessageBox.question(self, 'Delete', 'Remove this entry from the Windows Credential Locker?') == QMessageBox.Yes:
                    vault.delete(name); QMessageBox.information(self, 'Deleted', 'Vault entry deleted.')
        except Exception as exc:
            QMessageBox.warning(self, 'Vault', str(exc))

    # ---------------------------------------------------------------- results
    def build_results(self) -> QScrollArea:
        def build(lay):
            lay.addLayout(eyebrow_title('BATCH EVIDENCE', 'Results & reports'))
            card = Card(pad=(0, 0, 0, 0), gap=0, soft_shadow=True)
            top = QWidget(); tl = QVBoxLayout(top); tl.setContentsMargins(22, 18, 22, 10); tl.setSpacing(12)
            tools = QHBoxLayout(); tools.setSpacing(10)
            self.search_edit = QLineEdit(); self.search_edit.setPlaceholderText('Search file or status…')
            self.search_edit.textChanged.connect(self._results_filter)
            tools.addWidget(self.search_edit, 1)
            self.filter_combo = QComboBox(); self.filter_combo.addItems(['All statuses', 'Needs attention', 'Unlocked'])
            self.filter_combo.currentTextChanged.connect(lambda *_: self._results_filter())
            tools.addWidget(self.filter_combo)
            tl.addLayout(tools)
            top.setStyleSheet('background: transparent;')
            card.body.addWidget(top)

            self.results_table = QTableWidget(0, 5)
            self.results_table.setHorizontalHeaderLabels(['STATUS', 'FILE · PATH', 'SECURITY', 'TRIES', 'TIME'])
            self.results_table.verticalHeader().setVisible(False)
            self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.results_table.setShowGrid(False)
            self.results_table.setSortingEnabled(True)
            self.results_table.setMinimumHeight(360)
            self.results_table.verticalHeader().setDefaultSectionSize(46)
            h = self.results_table.horizontalHeader()
            h.setSectionResizeMode(0, QHeaderView.Fixed); self.results_table.setColumnWidth(0, 150)
            h.setSectionResizeMode(1, QHeaderView.Stretch)
            h.setSectionResizeMode(2, QHeaderView.Fixed); self.results_table.setColumnWidth(2, 160)
            h.setSectionResizeMode(3, QHeaderView.Fixed); self.results_table.setColumnWidth(3, 80)
            h.setSectionResizeMode(4, QHeaderView.Fixed); self.results_table.setColumnWidth(4, 80)
            card.body.addWidget(self.results_table)

            footer = QWidget(); fl = QHBoxLayout(footer); fl.setContentsMargins(22, 12, 22, 16); fl.setSpacing(10)
            footer.setStyleSheet('background: transparent;')
            self.report_label = label('No report yet.', 'faint'); fl.addWidget(self.report_label, 1)
            fl.addWidget(QPushButton('Open HTML summary', clicked=lambda: self.open_path(self.last_html)))
            fl.addWidget(QPushButton('Open CSV report', clicked=lambda: self.open_path(self.last_report)))
            fl.addWidget(QPushButton('Open output folder', clicked=lambda: self.open_path(self.last_output)))
            card.body.addWidget(footer)
            lay.addWidget(card)
        return _scroll(build)

    def add_result_row(self, payload):
        table = self.results_table
        table.setSortingEnabled(False)
        r = table.rowCount(); table.insertRow(r)
        status = payload['status']
        chip = Chip(STATUS_LABEL.get(status, status), T.tone(status))
        holder = QWidget(); hl = QHBoxLayout(holder); hl.setContentsMargins(8, 4, 8, 4); hl.addWidget(chip); hl.addStretch(1)
        holder.setStyleSheet('background: transparent;')
        table.setCellWidget(r, 0, holder)
        name = payload.get('relative') or Path(payload['source']).name
        for col, val, mono in [(1, name, True), (2, STATUS_LABEL.get(payload.get('security', ''), payload.get('security', '')), False),
                               (3, str(payload.get('attempts', '')), True), (4, str(payload.get('elapsed_seconds', '')), True)]:
            item = QTableWidgetItem(val)
            if mono:
                from PySide6.QtGui import QFont
                item.setFont(QFont('IBM Plex Mono, Consolas, monospace'))
            if col in (3, 4):
                item.setTextAlignment(Qt.AlignCenter)
            table.setItem(r, col, item)
        table.setSortingEnabled(True)
        table._status_by_row = getattr(table, '_status_by_row', {})
        table._status_by_row[r] = status

    def _results_filter(self):
        table = getattr(self, 'results_table', None)
        if table is None:
            return
        query = self.search_edit.text().casefold().strip()
        sel = self.filter_combo.currentText()
        for r in range(table.rowCount()):
            status = getattr(table, '_status_by_row', {}).get(r, '')
            text = ' '.join(table.item(r, c).text() for c in (1, 2) if table.item(r, c)).casefold()
            ok = (sel == 'All statuses' or (sel == 'Needs attention' and status in core.FAILED)
                  or (sel == 'Unlocked' and status in ('Unlocked', 'CopiedUnencrypted')))
            ok = ok and (not query or query in text or query in status.casefold())
            table.setRowHidden(r, not ok)

    def clear_results(self):
        if hasattr(self, 'results_table'):
            self.results_table.setRowCount(0)
            self.results_table._status_by_row = {}

    # ---------------------------------------------------------------- settings
    def build_settings(self) -> QScrollArea:
        def build(lay):
            lay.addLayout(eyebrow_title('CONTROLLED EXECUTION', 'Run settings'))
            limits = Card(pad=(22, 20, 22, 22))
            limits.add(label('Processing limits', 'section'))
            grid = QHBoxLayout(); grid.setSpacing(18)
            self.limit_edit = self._num_field(grid, 'File limit', '0', '0 = all')
            self.attempts_edit = self._num_field(grid, 'Attempts / PDF', '30', '1–1,000')
            self.timeout_edit = self._num_field(grid, 'Timeout (s)', '60', '1–3,600')
            grid.addStretch(1)
            limits.add_layout(grid)
            wrow = QHBoxLayout(); wrow.setSpacing(10)
            wrow.addWidget(label('Parallel workers', 'muted'))
            self.workers_combo = QComboBox(); self.workers_combo.addItems([str(i) for i in range(1, 9)])
            self.workers_combo.setCurrentText(str(min(4, max(1, (os.cpu_count() or 2) // 2))))
            wrow.addWidget(self.workers_combo); wrow.addStretch(1)
            limits.add_layout(wrow)
            lay.addWidget(limits)

            mode = Card(pad=(22, 20, 22, 22))
            mode.add(label('Mode & privacy', 'section'))
            self.dry_run_cb = QCheckBox('Dry run — list matching files; test no passwords and write nothing'); mode.add(self.dry_run_cb)
            self.copy_unenc_cb = QCheckBox('Copy already-unencrypted PDFs into the output folder'); mode.add(self.copy_unenc_cb)
            self.relative_cb = QCheckBox('Use relative file paths in CSV reports (recommended)'); self.relative_cb.setChecked(True); mode.add(self.relative_cb)
            self.html_cb = QCheckBox('Also write a readable HTML summary'); self.html_cb.setChecked(True); mode.add(self.html_cb)
            lay.addWidget(mode)

            cont = Card(pad=(22, 20, 22, 22))
            cont.add(label('Continue from a previous report', 'section'))
            cont.add(label('Retry processes only failed records. Resume skips verified files and does the rest. '
                           'Use the same source as that run.', 'muted'))
            rrow = QHBoxLayout(); rrow.setSpacing(16)
            self.retry_radio = QRadioButton('Retry failed only'); self.retry_radio.setChecked(True)
            self.resume_radio = QRadioButton('Resume interrupted run')
            rrow.addWidget(self.retry_radio); rrow.addWidget(self.resume_radio); rrow.addStretch(1)
            cont.add_layout(rrow)
            prow = QHBoxLayout(); prow.setSpacing(10)
            self.retry_edit = QLineEdit(); self.retry_edit.setProperty('mono', 'true'); self.retry_edit.setPlaceholderText('unlock-report-….csv')
            prow.addWidget(self.retry_edit, 1)
            prow.addWidget(QPushButton('Choose CSV', clicked=self._pick_report))
            prow.addWidget(QPushButton('Clear', clicked=lambda: self.retry_edit.clear()))
            cont.add_layout(prow)
            lay.addWidget(cont)

            eng = Card(pad=(22, 20, 22, 22))
            eng.add(label('qpdf engine', 'section'))
            self.engine_label = label(self.qpdf or 'qpdf not found — add it to PATH', 'faint'); self.engine_label.setWordWrap(True)
            eng.add(self.engine_label)
            lay.addWidget(eng)
        return _scroll(build)

    def _num_field(self, grid, labtext, default, hint):
        box = QVBoxLayout(); box.setSpacing(5)
        box.addWidget(label(labtext, 'fieldlabel'))
        edit = QLineEdit(default); edit.setFixedWidth(120)
        box.addWidget(edit)
        box.addWidget(label(hint, 'faint'))
        grid.addLayout(box)
        return edit

    def _pick_report(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose report', '', 'CSV reports (*.csv)')
        if path:
            self.retry_edit.setText(path)

    # ---------------------------------------------------------------- about
    def build_help(self) -> QScrollArea:
        def build(lay):
            from branding import VERSION
            lay.addLayout(eyebrow_title('RAR TOOLS', f'RAR PDF Batch Unlocker {VERSION}'))
            flow = Card(pad=(22, 20, 22, 22))
            flow.add(label('A simple workflow', 'section'))
            flow.add(label('1. Choose separate source and output folders, or add individual PDFs.\n'
                           '2. Scan or analyze to understand the batch.\n'
                           '3. Add the passwords you know; map folders to groups if needed.\n'
                           '4. Unlock. Review the results and the CSV/HTML report.', 'muted'))
            lay.addWidget(flow)
            safe = Card(pad=(22, 20, 22, 22))
            safe.add(label('Built around your originals', 'section'))
            safe.add(label('Original files are never changed. Existing outputs are skipped, and every decrypted output is '
                           'checked with qpdf before it is accepted. Passwords go to qpdf through stdin, never the command '
                           'line, and never appear in reports, logs or screenshots.', 'muted'))
            lay.addWidget(safe)
            lim = Card(pad=(22, 20, 22, 22))
            lim.add(label('What this app can and cannot do', 'section'))
            lim.add(label('Use only PDFs and passwords you are authorized to access. A strong unknown opening password '
                          'cannot be bypassed — there is no online upload, guessing service or brute force. The Windows '
                          'build is unsigned unless separately signed with an Authenticode certificate.', 'muted'))
            lay.addWidget(lim)
        return _scroll(build)

    # ---------------------------------------------------------------- settings assembly
    def assemble_settings(self, analyze=False):
        from branding import VERSION
        src = self.source_edit.text().strip()
        if not (src or self.extra_files):
            raise ValueError('Choose a source folder or add PDF files.')
        if not self.output_edit.text().strip():
            raise ValueError('Choose an output folder.')
        try:
            limit = int(self.limit_edit.text()); attempts = int(self.attempts_edit.text()); timeout = int(self.timeout_edit.text())
        except ValueError:
            raise ValueError('Limit, attempts and timeout must be whole numbers.')
        mapping = {}
        for line in self.mapping_text.toPlainText().splitlines():
            if not line.strip():
                continue
            if '=' not in line:
                raise ValueError('Mapping needs folder=Group per line.')
            folder, group = line.split('=', 1); folder = folder.strip(); group = group.strip()
            if not folder or group not in self.password_groups or folder.startswith(('/', '\\')) or '..' in Path(folder.replace('\\', '/')).parts:
                raise ValueError('Invalid mapping or unknown group: ' + line)
            mapping[folder] = group
        report = self.retry_edit.text().strip(); resume = self.resume_radio.isChecked()
        return core.Settings(Path(src) if src else None, Path(self.output_edit.text().strip()), self.qpdf or 'qpdf',
                             list(self.password_groups['General']), limit, self.dry_run_cb.isChecked(),
                             analyze_only=analyze, failed_report='' if resume else report, resume_report=report if resume else '',
                             timeout=timeout, workers=int(self.workers_combo.currentText()), html_summary=self.html_cb.isChecked(),
                             app_version=VERSION, inputs=[Path(f) for f in self.extra_files],
                             password_groups={k: list(v) for k, v in self.password_groups.items() if k != 'General'},
                             folder_groups=mapping, max_attempts=attempts,
                             relative_reports=self.relative_cb.isChecked(), include_unencrypted=self.copy_unenc_cb.isChecked())
