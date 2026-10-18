"""Headless Qt GUI tests (offscreen). Exercise the real engine and toolkit."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pathlib import Path
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from PySide6.QtWidgets import QApplication
    HAVE_QT = True
except Exception:
    HAVE_QT = False

from scripts.fixtures import create_fixtures, make_pdf, KNOWN

_app = None


def app():
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication(sys.argv)
    return _app


@unittest.skipUnless(HAVE_QT, 'PySide6 not available')
class QtGuiTests(unittest.TestCase):
    def setUp(self):
        app()
        import qt_main
        self.win = qt_main.MainWindow()
        self.addCleanup(self.win.deleteLater)
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def pump(self, until=None, timeout=30):
        end = time.time() + timeout
        while time.time() < end:
            app().processEvents()
            if until is not None and until():
                return
            if until is None and not self.win.busy:
                return
            time.sleep(0.02)
        if until is None and self.win.busy:
            self.fail('operation did not finish')

    def test_all_pages_build(self):
        for key in ('workspace', 'passwords', 'results', 'tools', 'settings', 'help'):
            self.win.navigate(key); app().processEvents()
            self.assertIsNotNone(self.win.pages[key])

    def test_real_unlock_fills_results(self):
        src = create_fixtures(self.root).resolve()
        self.win.source_edit.setText(str(src))
        self.win.output_edit.setText(str(self.root / 'Out'))
        self.win.password_groups['General'].append(KNOWN)
        self.win._start_unlock()
        self.pump()
        self.assertEqual(self.win.counts.get('Unlocked'), 3)
        self.assertEqual(self.win.counts.get('PasswordNotMatched'), 1)
        self.assertEqual(self.win.results_table.rowCount(), 5)
        self.assertTrue(self.win.last_report)
        # filter narrows to failures
        self.win.filter_combo.setCurrentText('Needs attention')
        app().processEvents()
        visible = [r for r in range(5) if not self.win.results_table.isRowHidden(r)]
        self.assertEqual(len(visible), 1)

    def test_settings_assembled_from_widgets(self):
        self.win.source_edit.setText(str(self.root))
        self.win.output_edit.setText(str(self.root / 'o'))
        self.win.timeout_edit.setText('90'); self.win.workers_combo.setCurrentText('3')
        self.win.copy_unenc_cb.setChecked(True)
        s = self.win.assemble_settings()
        self.assertEqual(s.timeout, 90)
        self.assertEqual(s.workers, 3)
        self.assertTrue(s.include_unencrypted)

    def test_password_group_add_and_mask(self):
        self.win.navigate('passwords'); app().processEvents()
        self.win.pw_entry.setText('synthetic-secret'); self.win._pw_add()
        self.assertIn('synthetic-secret', self.win.password_groups['General'])
        self.assertEqual(self.win.pw_entry.text(), '')
        self.assertIn('1 passwords in General', self.win.pw_count.text())

    def test_drop_source_and_output(self):
        folder = self.root / 'src'; folder.mkdir()
        pdf = make_pdf(self.root / 'one.pdf', None)
        self.win._drop_source([str(folder), str(pdf)])
        self.assertEqual(self.win.source_edit.text(), str(folder))
        self.assertIn(str(pdf), self.win.extra_files)
        out = self.root / 'out'; out.mkdir()
        self.win._drop_output([str(out)])
        self.assertEqual(self.win.output_edit.text(), str(out))

    def test_tools_merge_and_convert(self):
        self.win.navigate('tools'); app().processEvents()
        tp = self.win.tools_page
        import toolkit
        a = make_pdf(self.root / 'a.pdf', None, pages=2)
        b = make_pdf(self.root / 'b.pdf', None, pages=1)
        out = self.root / 'merged.pdf'
        tp.add_paths(tp.merge_list, 'pdf', [str(a), str(b)])
        self.assertEqual(len(tp.merge_list._paths), 2)
        res = toolkit.merge_pdfs([a, b], out)  # backend path the GUI calls
        self.assertEqual(res.pages, 3)

    def test_tools_add_folder_expands(self):
        self.win.navigate('tools'); app().processEvents()
        tp = self.win.tools_page
        sub = self.root / 'imgs'; sub.mkdir()
        from PIL import Image
        Image.new('RGB', (40, 30), (1, 2, 3)).save(sub / 'x.png')
        (sub / 'note.txt').write_text('x')
        tp.add_paths(tp.img_list, 'img', [str(sub)])
        self.assertEqual([Path(p).name for p in tp.img_list._paths], ['x.png'])


if __name__ == '__main__':
    unittest.main()
