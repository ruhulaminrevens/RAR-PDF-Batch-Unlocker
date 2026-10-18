"""Real Tk event tests; require a desktop (Windows CI or Xvfb)."""
from pathlib import Path
import tempfile
import threading
import time
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import App


class GuiTests(unittest.TestCase):
    def setUp(self):
        try:self.app=App()
        except tk.TclError as exc:
            if 'display' in str(exc).lower():self.skipTest('Desktop display not available')
            raise
        self.app.withdraw()
        self.addCleanup(self.app._shutdown)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);(self.root/'in').mkdir()
        (self.root/'in'/'one.pdf').write_bytes(b'%PDF synthetic')
        self.app.source.set(str(self.root/'in'));self.app.destination.set(str(self.root/'out'))
        self.app.qpdf.set(sys.executable)

    def pump(self):
        end=time.monotonic()+5
        while self.app.busy and time.monotonic()<end:
            self.app.update();time.sleep(.01)
        self.assertFalse(self.app.busy,'GUI run failed to finish')
        self.app.update()

    def test_password_group_count_mask_and_snapshot(self):
        a=self.app;a.pw_entry.insert(0,'synthetic-secret');a._add_password()
        self.assertEqual(a.password_groups['General'],['synthetic-secret'])
        self.assertEqual(a.pw_entry.get(),'')
        a.password_groups['Bank']=[];a.group.set('Bank');a._update_count()
        self.assertIn('0 passwords in Bank',a.pw_count.get())
        a.pw_entry.insert(0,'bank-fixture');a._add_password()
        a.mapping.insert('1.0','Bank=Bank')
        settings=a._settings();a.password_groups['Bank'].append('later')
        self.assertEqual(settings.password_groups['Bank'],['bank-fixture'])
        a.show_password.set(True);a._toggle_password();a._navigate('workspace')
        self.assertTrue(a.pw_entry.cget('show'))
        self.assertFalse(a.show_password.get())

    def test_all_controls_disable_during_run(self):
        a=self.app;a._set_busy(True)
        for widget,_ in a.mutables:self.assertEqual(str(widget.cget('state')),'disabled')
        a._set_busy(False)
        self.assertEqual(str(a.groupbox.cget('state')),'readonly')
        self.assertEqual(str(a.stop_btn.cget('state')),'disabled')

    def test_async_dry_run_no_output_and_search(self):
        a=self.app;a.dry_run.set(True);a._start(False);self.pump()
        self.assertEqual(a.counts,{'DryRun':1});self.assertFalse((self.root/'out').exists())
        self.assertEqual(len(a.table.get_children()),1)
        a.filter_status.set('Unlocked');a._filter_rows();self.assertEqual(a.table.get_children(),())
        a.filter_status.set('All statuses');a.search.set('one.pdf');self.assertEqual(len(a.table.get_children()),1)
        a.search.set('missing');self.assertEqual(a.table.get_children(),())
        a.search.set('');self.assertEqual(len(a.table.get_children()),1)

    def test_source_snapshot_controls_result_paths(self):
        a=self.app;a.active_source=self.root/'in'
        a.source.set(str(self.root/'somewhere-else'))
        a._result({'index':1,'total':1,'source':str(self.root/'in'/'one.pdf'),'status':'Unlocked','attempts':2,'elapsed_seconds':.12,'details':'Verified'})
        self.assertEqual(a.row_items[0][1][1],'one.pdf')
        self.assertEqual(a.metric_vars['unlocked'].get(),'1')

    def test_invalid_mapping_and_nested_folders_rejected(self):
        a=self.app;a.mapping.insert('1.0','../Bank=General')
        with self.assertRaises(ValueError):a._settings()
        a.mapping.delete('1.0','end');a.destination.set(str(self.root/'in'/'child'))
        with patch('app.messagebox.showerror') as error:
            a._scan();self.pump();error.assert_called_once()

    def test_safe_stop_keeps_ui_busy_until_done(self):
        a=self.app;a._set_busy(True);a._stop()
        self.assertTrue(a.stop_flag.is_set());self.assertTrue(a.busy)
        a.events.put(('done',{'report':None,'cancelled':True}))
        self.pump();self.assertIn('Stopped safely',a.status.get())

    def test_retry_uses_last_report(self):
        a=self.app;a.last_report=str(self.root/'previous.csv')
        with patch('app.messagebox.showinfo'):a._use_last_report()
        self.assertEqual(a.retry_report.get(),a.last_report)

if __name__=='__main__':unittest.main()


class FeatureTests(GuiTests):
    def test_add_single_pdfs_dedupes_and_runs_without_folder(self):
        a = self.app
        a.source.set('')
        f = str(self.root / 'in' / 'one.pdf')
        with patch('app.filedialog.askopenfilenames', return_value=(f, f)):
            a._add_files()
        self.assertEqual(a.extra_files, [f])
        self.assertIn('1 duplicate ignored', a.files_summary.get())
        settings = a._settings()
        self.assertIsNone(settings.source)
        self.assertEqual(settings.inputs, [Path(f)])
        a.dry_run.set(True)
        a._start(False)
        self.pump()
        self.assertEqual(a.counts, {'DryRun': 1})

    def test_delete_group_and_duplicate_password_notice(self):
        a = self.app
        a.password_groups['Bank'] = ['x']
        a.groupbox.config(values=list(a.password_groups))
        a.group.set('Bank')
        with patch('app.messagebox.askyesno', return_value=True):
            a._delete_group()
        self.assertNotIn('Bank', a.password_groups)
        self.assertEqual(a.group.get(), 'General')
        a.pw_entry.insert(0, 'dup')
        a._add_password()
        a.pw_entry.insert(0, 'dup')
        a._add_password()
        self.assertEqual(a.password_groups['General'], ['dup'])
        self.assertIn('duplicate', a.status.get())

    def test_sorting_and_attention_filter(self):
        a = self.app
        a.active_source = self.root / 'in'
        for i, (status, secs) in enumerate([('Unlocked', 3.0), ('PasswordNotMatched', 1.0), ('SkippedExisting', 2.0)], 1):
            a._result({'index': i, 'total': 3, 'source': str(self.root / 'in' / f'f{i}.pdf'), 'relative': f'f{i}.pdf',
                       'status': status, 'attempts': i, 'elapsed_seconds': secs, 'details': ''})
        a._sort_table(a.table, 'seconds')
        self.assertEqual([a.table.set(i, 'seconds') for i in a.table.get_children()], ['1.0', '2.0', '3.0'])
        a._sort_table(a.table, 'seconds')
        self.assertEqual(a.table.set(a.table.get_children()[0], 'seconds'), '3.0')
        a.filter_status.set('Needs attention')
        a._filter_rows()
        self.assertEqual(len(a.table.get_children()), 1)
        a.table.selection_set(a.table.get_children()[0])
        a._select_result(a.table)
        self.assertIn('Add the correct password', a.result_detail.get())

    def test_preview_text_lists_real_plan_values(self):
        a = self.app
        a.pw_entry.insert(0, 'fixture-pass')
        a._add_password()
        settings = a._settings()
        import core
        plan = core.plan(settings)
        text = a._preview_text({'plan': plan, 'settings': settings, 'free': 5 * 1024 ** 3})
        self.assertIn('Process 1 PDFs', text)
        self.assertIn('Passwords: 1', text)
        self.assertNotIn('fixture-pass', text)


class DiagnosticsTests(unittest.TestCase):
    def test_passwords_redacted_from_crash_log(self):
        import diagnostics, logging
        with tempfile.TemporaryDirectory() as tmp, patch.dict('os.environ', {'LOCALAPPDATA': tmp}):
            diagnostics._logger.handlers.clear()
            diagnostics.remember_secret('synthetic-secret-77')
            try:
                raise ValueError('failed with synthetic-secret-77')
            except ValueError as exc:
                diagnostics.log_exception(type(exc), exc, exc.__traceback__)
            for h in diagnostics._logger.handlers:
                h.flush(); h.close()
            text = (Path(tmp) / 'RAR PDF Batch Unlocker' / 'logs' / 'app.log').read_text(encoding='utf-8')
            diagnostics._logger.handlers.clear()
            diagnostics.forget_secrets()
        self.assertIn('[redacted]', text)
        self.assertNotIn('synthetic-secret-77', text)


class ScalingLayoutTests(unittest.TestCase):
    """Emulates Windows 125/150/200 % scaling through Tk's DPI factor and checks for clipping."""

    def check(self, factor, screen):
        import os
        with patch.dict(os.environ, {'RAR_TK_SCALING': str(96 * factor / 72)}):
            try:
                app = App()
            except tk.TclError as exc:
                self.skipTest(str(exc))
        try:
            w, h = screen
            app.geometry(f'{w - 60}x{h - 80}+0+0')
            problems = []
            for page in app.pages:
                app._navigate(page)
                app.update()
                canvas = app.pages[page].canvas
                limit = canvas.winfo_rootx() + canvas.winfo_width() + 1
                stack = [app.pages[page].body]
                while stack:
                    widget = stack.pop()
                    stack.extend(widget.winfo_children())
                    if not widget.winfo_ismapped() or isinstance(widget, (ttk.Treeview, ttk.Scrollbar, tk.Canvas)):
                        continue
                    right = widget.winfo_rootx() + widget.winfo_width()
                    if right > limit:
                        problems.append(f'{page}: {widget.winfo_class()} {widget} exceeds width by {right - limit}px')
                    if isinstance(widget, (ttk.Button, ttk.Checkbutton, ttk.Radiobutton)) and widget.winfo_width() < widget.winfo_reqwidth() - 2:
                        problems.append(f'{page}: clipped {widget.winfo_class()} "{widget.cget("text")}"')
            self.assertEqual(problems, [], f'scale {factor} on {screen}')
        finally:
            app._shutdown()

    def test_100_125_150_200_percent(self):
        for factor, screen in [(1.0, (1366, 768)), (1.25, (1920, 1080)), (1.25, (1366, 768)),
                               (1.5, (1366, 768)), (1.5, (1920, 1080)), (2.0, (1920, 1080)), (2.0, (2560, 1440)), (2.0, (3840, 2160))]:
            with self.subTest(factor=factor, screen=screen):
                self.check(factor, screen)


class ToolkitGuiTests(unittest.TestCase):
    def setUp(self):
        try:self.app=App()
        except tk.TclError as exc:
            if 'display' in str(exc).lower():self.skipTest('no display')
            raise
        self.app.withdraw();self.addCleanup(self.app._shutdown)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.out=self.root/'out';self.out.mkdir()
        from scripts.fixtures import make_pdf
        self.make=make_pdf
        self.app._navigate('tools');self.app.update()

    def pump(self):
        end=time.monotonic()+15
        while self.app.busy and time.monotonic()<end:
            self.app.update();time.sleep(.01)
        self.assertFalse(self.app.busy,'tool run did not finish')
        self.app.update()

    def test_merge_via_gui(self):
        a,b=self.make(self.root/'a.pdf',None,pages=2),self.make(self.root/'b.pdf',None,pages=1)
        out=self.out/'merged.pdf'
        self.app.merge_list._paths=[str(a),str(b)]
        with patch('app.filedialog.asksaveasfilename',return_value=str(out)),patch('app.messagebox.askyesno',return_value=False):
            self.app._tool_merge();self.pump()
        self.assertTrue(out.exists())
        from pypdf import PdfReader;self.assertEqual(len(PdfReader(str(out)).pages),3)
        self.assertIn('Done',self.app.tool_status.get())

    def test_images_to_pdf_via_gui(self):
        from PIL import Image
        p=self.root/'x.png';Image.new('RGB',(120,80),(20,60,120)).save(p)
        out=self.out/'img.pdf';self.app.img_list._paths=[str(p)]
        with patch('app.filedialog.asksaveasfilename',return_value=str(out)),patch('app.messagebox.askyesno',return_value=False):
            self.app._tool_img2pdf();self.pump()
        self.assertTrue(out.exists())

    def test_pdf_to_images_via_gui(self):
        src=self.make(self.root/'r.pdf',None,pages=2)
        self.app.rimg_input.set(str(src));self.app.rimg_fmt.set('png');self.app.rimg_dpi.set('72')
        with patch('app.filedialog.askdirectory',return_value=str(self.out)),patch('app.messagebox.askyesno',return_value=False):
            self.app._tool_pdf2img();self.pump()
        self.assertEqual(len(list(self.out.glob('*.png'))),2)

    def test_convert_docx_via_gui(self):
        src=self.make(self.root/'c.pdf',None,pages=1)
        out=self.out/'c.docx';self.app.conv_input.set(str(src))
        with patch('app.filedialog.asksaveasfilename',return_value=str(out)),patch('app.messagebox.askyesno',return_value=False):
            self.app._tool_convert('docx');self.pump()
        self.assertTrue(out.exists())

    def test_protected_pdf_prompts_for_password(self):
        from scripts.fixtures import KNOWN
        src=self.make(self.root/'enc.pdf',KNOWN,pages=1)
        self.app.rimg_input.set(str(src));self.app.rimg_dpi.set('72')
        with patch('app.filedialog.askdirectory',return_value=str(self.out)),\
             patch('app.simpledialog.askstring',return_value=KNOWN),patch('app.messagebox.askyesno',return_value=False):
            self.app._tool_pdf2img();self.pump()
        self.assertEqual(len(list(self.out.glob('*.png'))),1)

    def test_protected_pdf_cancel(self):
        from scripts.fixtures import KNOWN
        src=self.make(self.root/'enc.pdf',KNOWN,pages=1)
        self.app.conv_input.set(str(src))
        out=self.out/'c.docx'
        with patch('app.filedialog.asksaveasfilename',return_value=str(out)),\
             patch('app.simpledialog.askstring',return_value=None):
            self.app._tool_convert('docx');self.pump()
        self.assertFalse(out.exists())
        self.assertIn('password-protected',self.app.tool_status.get())


class DragDropTests(unittest.TestCase):
    def setUp(self):
        try:self.app=App()
        except tk.TclError as exc:
            if 'display' in str(exc).lower():self.skipTest('no display')
            raise
        self.app.withdraw();self.addCleanup(self.app._shutdown)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        from scripts.fixtures import make_pdf
        self.make=make_pdf

    def test_splitlist_parses_braced_paths(self):
        data='{%s} {%s}'%(str(self.root/'a b.pdf'),str(self.root/'c.pdf'))
        self.assertEqual(list(self.app.tk.splitlist(data)),[str(self.root/'a b.pdf'),str(self.root/'c.pdf')])

    def test_drop_source_sets_folder_and_adds_pdfs(self):
        folder=self.root/'src';folder.mkdir()
        f=self.make(self.root/'one.pdf',None)
        self.app._drop_source([str(folder),str(f)])
        self.assertEqual(self.app.source.get(),str(folder))
        self.assertIn(str(f),self.app.extra_files)

    def test_drop_output_requires_folder(self):
        folder=self.root/'out';folder.mkdir()
        self.app._drop_output([str(folder)])
        self.assertEqual(self.app.destination.get(),str(folder))
        with patch('app.messagebox.showinfo') as info:
            self.app._drop_output([str(self.make(self.root/'x.pdf',None))])
            info.assert_called_once()

    def test_drop_into_merge_list_and_folder_expand(self):
        self.app._navigate('tools');self.app.update()
        a=self.make(self.root/'a.pdf',None)
        sub=self.root/'more';sub.mkdir();b=self.make(sub/'b.pdf',None);(sub/'note.txt').write_text('x')
        self.app._add_paths_to_list(self.app.merge_list,'pdf',[str(a),str(sub)])
        self.assertEqual(sorted(Path(p).name for p in self.app.merge_list._paths),['a.pdf','b.pdf'])

    def test_drop_single_pdf_picks_first_pdf(self):
        self.app._navigate('tools');self.app.update()
        f=self.make(self.root/'c.pdf',None)
        self.app._drop_single_pdf(self.app.conv_input,[str(self.root/'x.txt'),str(f)])
        self.assertEqual(self.app.conv_input.get(),str(f))

    def test_drop_is_ignored_while_busy(self):
        self.app.busy=True
        class E: data=str(self.make(self.root/'d.pdf',None))
        called=[]
        self.app._on_drop(E(),lambda p:called.append(p))
        self.assertEqual(called,[])
