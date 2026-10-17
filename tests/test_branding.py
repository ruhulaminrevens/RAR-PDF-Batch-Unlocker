from pathlib import Path
import struct
import unittest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from branding import asset_path

class BrandingTests(unittest.TestCase):
    def test_ico_has_all_native_sizes(self):
        data=asset_path('app.ico').read_bytes()
        self.assertEqual(struct.unpack('<HHH',data[:6]),(0,1,7))
        sizes=set()
        for i in range(7):
            w,h,_,_,planes,bits,length,offset=struct.unpack('<BBBBHHII',data[6+i*16:22+i*16])
            sizes.add(w or 256);self.assertEqual(w,h);self.assertEqual(bits,32)
            self.assertEqual(data[offset:offset+8],b'\x89PNG\r\n\x1a\n')
            self.assertLessEqual(offset+length,len(data))
        self.assertEqual(sizes,{16,24,32,48,64,128,256})

    def test_frozen_assets_use_bundle_directory(self):
        from unittest.mock import patch
        with patch.object(sys,'_MEIPASS','/bundle',create=True):self.assertEqual(asset_path('app.ico'),Path('/bundle/assets/app.ico'))


class VersionConsistencyTests(unittest.TestCase):
    def test_every_version_string_matches_branding(self):
        import re
        from branding import VERSION
        root = Path(__file__).resolve().parents[1]
        iss = (root / 'installer' / 'setup.iss').read_text(encoding='utf-8')
        self.assertIn(f'#define MyAppVersion "{VERSION}"', iss)
        info = (root / 'assets' / 'version-info.txt').read_text(encoding='utf-8')
        self.assertEqual(set(re.findall(r"'(?:File|Product)Version','([^']+)'", info)), {VERSION})
        nums = tuple(int(x) for x in VERSION.split('.')) + (0,)
        self.assertEqual(set(re.findall(r'(?:file|prod)vers=\(([^)]*)\)', info)), {','.join(map(str, nums))})
        self.assertTrue((root / 'THIRD-PARTY-NOTICES.txt').is_file())
