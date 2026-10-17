import sys
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import vault

class VaultTests(unittest.TestCase):
    def test_explicit_storage_only_and_validation(self):
        with patch.object(vault,'_store') as store:
            with self.assertRaises(ValueError):vault.save('', 'fixture')
            store.assert_not_called()
            vault.save('fixture-label','fixture-value')
            store.return_value.set_password.assert_called_once_with(vault.SERVICE,'fixture-label','fixture-value')

    @unittest.skipUnless(sys.platform=='win32','Windows Credential Locker only')
    def test_windows_vault_round_trip(self):
        import uuid
        name='RAR-Automated-QA-'+uuid.uuid4().hex
        vault.save(name,'synthetic-qa-value')
        try:self.assertEqual(vault.load(name),'synthetic-qa-value')
        finally:vault.delete(name)
        self.assertIsNone(vault.load(name))
