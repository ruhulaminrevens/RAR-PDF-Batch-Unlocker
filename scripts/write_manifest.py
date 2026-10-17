"""Record SHA-256 of every bundled engine file; the app re-checks them at start-up."""
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
files = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
         for p in sorted(root.rglob('*')) if p.is_file() and p.name != 'qpdf-manifest.json'}
(root / 'qpdf-manifest.json').write_text(json.dumps({'files': files}, indent=2), encoding='utf-8')
print(f'{len(files)} engine files recorded')
for name in files:
    print(' ', name)
