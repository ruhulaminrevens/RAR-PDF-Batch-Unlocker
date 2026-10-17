"""Actual qpdf regression checks, using synthetic encrypted PDFs only."""
import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import core
from scripts.fixtures import create_fixtures, KNOWN

QPDF=os.environ.get('RAR_TEST_QPDF') or shutil.which('qpdf')

@unittest.skipUnless(QPDF,'Real qpdf executable not available')
class QpdfIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.src=create_fixtures(self.root)
        self.settings=core.Settings(self.src,self.root/'Output',QPDF,[KNOWN])
        self.before={p.relative_to(self.src):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.src.rglob('*.pdf')}

    def run_batch(self):
        events=[];core.process(self.settings,lambda k,p:events.append((k,p)),threading.Event())
        return [p for k,p in events if k=='result'],events[-1][1]

    def test_real_unlock_verify_retry_and_originals(self):
        rows,done=self.run_batch()
        statuses=[r['status'] for r in rows]
        self.assertEqual(statuses.count('Unlocked'),3)
        self.assertEqual(statuses.count('PasswordNotMatched'),1)
        self.assertEqual(statuses.count('SkippedUnencrypted'),1)
        for p in self.settings.destination.rglob('*.pdf'):
            self.assertTrue(core.is_unencrypted(QPDF,p,60))
        after={p.relative_to(self.src):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.src.rglob('*.pdf')}
        self.assertEqual(self.before,after)
        report=Path(done['report']).read_text(encoding='utf-8-sig')
        self.assertNotIn(KNOWN,report);self.assertNotIn(str(self.root),report)
        outputs={p:p.read_bytes() for p in self.settings.destination.rglob('*.pdf')}
        rows,_=self.run_batch();self.assertEqual(sum(r['status']=='SkippedExisting' for r in rows),3)
        self.assertEqual(outputs,{p:p.read_bytes() for p in outputs})
        self.settings.failed_report=done['report'];rows,_=self.run_batch()
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['status'],'PasswordNotMatched')
        self.assertFalse(list(self.settings.destination.rglob('*.rar-part-*')))

    def test_real_analyze_and_dry_run(self):
        self.settings.dry_run=True;rows,done=self.run_batch()
        self.assertTrue(all(r['status']=='DryRun' for r in rows));self.assertFalse(self.settings.destination.exists())
        self.settings.dry_run=False;self.settings.analyze_only=True
        rows,done=self.run_batch()
        self.assertEqual(sorted(r['status'] for r in rows),['PasswordRequired']*3+['PermissionRestricted','Unencrypted'])
        self.assertFalse(list(self.settings.destination.rglob('*.pdf')))
        self.assertTrue(Path(done['report']).is_file())
