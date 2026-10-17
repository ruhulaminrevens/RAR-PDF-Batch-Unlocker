"""Real Tk event tests; require a desktop (Windows CI or Xvfb)."""
from pathlib import Path
import tempfile
import threading
import time
import tkinter as tk
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
