import csv
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import core

class FakeResult:
    def __init__(self, code): self.returncode=code

class TestCore(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.src=self.root/'source'; self.dst=self.root/'output'
        self.src.mkdir()
        (self.src/'sub').mkdir()
        for file in ('a.pdf','sub/b.PDF','sub/c.pdf','d.txt'):
            f=self.src/file; f.write_bytes(b'file')
        self.settings=core.Settings(self.src,self.dst,sys.executable,['correct','wrong'])

    def test_scan_and_nested_rejection(self):
        _,_,files=core.scan(self.settings)
        self.assertEqual(len(files),3)
        self.settings.destination=self.src/'child'
        with self.assertRaises(ValueError): core.scan(self.settings)

    def test_full_process_and_report_no_password(self):
        def fake(qpdf,args,password=None,timeout=60):
            if args[0]=='--is-encrypted':
                p=Path(args[1])
                return FakeResult(2 if 'c.pdf' in str(p) or '.rar-part-' in str(p) else 0)
            if args[0]=='--requires-password':
                return FakeResult(0)
            if args[0]=='--password-file=-':
                if password=='correct': Path(args[-1]).write_bytes(b'%PDF-1.7\nresult')
                return FakeResult(0 if password=='correct' else 2)
            raise AssertionError(args)
        events=[]
        with patch.object(core,'run_qpdf',side_effect=fake):
            core.process(self.settings,lambda k,v:events.append((k,v)),threading.Event())
        rows=[v for k,v in events if k=='result']
        self.assertEqual([r['status'] for r in rows],['Unlocked','Unlocked','SkippedUnencrypted'])
        self.assertEqual(rows[0]['attempts'],2)
        self.assertTrue((self.dst/'sub/b.PDF').exists())
        self.assertFalse((self.dst/'sub/c.pdf').exists())
        report=Path(events[-1][1]['report'])
        self.assertTrue(report.exists())
        self.assertNotIn('correct',report.read_text(encoding='utf-8-sig'))
        events.clear()
        with patch.object(core,'run_qpdf',side_effect=fake):
            core.process(self.settings,lambda k,v:events.append((k,v)),threading.Event())
        self.assertEqual([v['status'] for k,v in events if k=='result'],['SkippedExisting','SkippedExisting','SkippedUnencrypted'])

    def test_unknown_password_and_dry_run(self):
        events=[]
        self.settings.limit=1
        with patch.object(core,'run_qpdf',side_effect=lambda q,a,p=None,timeout=60: FakeResult(0 if a[0] in ('--is-encrypted','--requires-password') else 2)):
            core.process(self.settings,lambda k,v:events.append((k,v)),threading.Event())
        self.assertEqual([v['status'] for k,v in events if k=='result'],['PasswordNotMatched'])
        self.settings.dry_run=True
        events.clear()
        with patch.object(core,'run_qpdf',side_effect=AssertionError('Must not invoke qpdf')):
            core.process(self.settings,lambda k,v:events.append((k,v)),threading.Event())
        self.assertEqual([v['status'] for k,v in events if k=='result'],['DryRun'])

    def test_cancel(self):
        stop=threading.Event(); stop.set(); events=[]
        core.process(self.settings,lambda k,v:events.append((k,v)),stop)
        self.assertEqual([k for k,v in events if k=='result'],[])
        self.assertTrue(events[-1][1]['cancelled'])

class ExtendedTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.src=self.root/'in';self.dst=self.root/'out'
        (self.src/'Bank').mkdir(parents=True)
        (self.src/'Bank'/'statement.pdf').write_bytes(b'%PDF fake')
        self.settings=core.Settings(self.src,self.dst,sys.executable,['general'],password_groups={'Bank':['bankpass']},folder_groups={'Bank':'Bank'},max_attempts=2)

    def test_groups_and_attempt_limit(self):
        path=self.src/'Bank'/'statement.pdf'
        self.assertEqual(core.group_for(path,self.src,self.settings.folder_groups),'Bank')
        self.assertEqual(core.candidates(self.settings,'Bank'),['','bankpass'])

    def test_security_categories(self):
        with patch.object(core,'run_qpdf',side_effect=[FakeResult(2)]):
            self.assertEqual(core.inspect_pdf('qpdf','any.pdf',60),'Unencrypted')
        with patch.object(core,'run_qpdf',side_effect=[FakeResult(0),FakeResult(3)]):
            self.assertEqual(core.inspect_pdf('qpdf','any.pdf',60),'PermissionRestricted')
        with patch.object(core,'run_qpdf',side_effect=[FakeResult(0),FakeResult(0)]):
            self.assertEqual(core.inspect_pdf('qpdf','any.pdf',60),'PasswordRequired')
        with patch.object(core,'run_qpdf',side_effect=[FakeResult(1)]):
            self.assertEqual(core.inspect_pdf('qpdf','any.pdf',60),'InvalidPDF')

    def test_retry_report_filters_failures_and_traversal(self):
        rp=self.root/'previous.csv'
        with rp.open('w',newline='',encoding='utf-8') as fh:
            w=csv.DictWriter(fh,fieldnames=['source','status']);w.writeheader()
            w.writerow({'source':'Bank/statement.pdf','status':'PasswordNotMatched'})
            w.writerow({'source':'../outside.pdf','status':'PasswordNotMatched'})
            w.writerow({'source':'Bank/statement.pdf','status':'Unlocked'})
        self.settings.failed_report=str(rp)
        _,_,files=core.scan(self.settings)
        self.assertEqual([p.resolve() for p in files],[(self.src/'Bank'/'statement.pdf').resolve()])

    def test_report_uses_relative_paths_and_never_password(self):
        def fake(qpdf,args,password=None,timeout=60):
            if args[0]=='--is-encrypted':return FakeResult(0)
            if args[0]=='--requires-password':return FakeResult(0)
            return FakeResult(2)
        emitted=[]
        with patch.object(core,'run_qpdf',side_effect=fake):
            core.process(self.settings,lambda k,p:emitted.append((k,p)),threading.Event())
        report=Path(emitted[-1][1]['report'])
        content=report.read_text(encoding='utf-8-sig')
        self.assertNotIn('general',content)
        self.assertNotIn('bankpass',content)
        self.assertNotIn(str(self.root),content)
        self.assertIn('Bank/statement.pdf',content)
        self.assertIn('PasswordNotMatched',content)

    def test_analyze_does_not_create_pdf(self):
        self.settings.analyze_only=True
        emitted=[]
        with patch.object(core,'run_qpdf',side_effect=[FakeResult(0),FakeResult(0)]):
            core.process(self.settings,lambda k,p:emitted.append((k,p)),threading.Event())
        self.assertEqual(emitted[1][1]['status'],'PasswordRequired')
        self.assertEqual(list(self.dst.rglob('*.pdf')),[])

if __name__ == '__main__': unittest.main()
