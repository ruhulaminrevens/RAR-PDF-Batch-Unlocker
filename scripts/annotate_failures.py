"""Turn unittest failures into GitHub annotations so they are readable without raw logs."""
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace')
blocks = re.split(r'^={50,}\n', text, flags=re.M)[1:]
for block in blocks[:10]:
    head, _, body = block.partition('\n')
    tail = body.split('\n-' * 1)[0]
    lines = [l for l in body.splitlines() if l.strip() and not l.startswith('---')]
    detail = '\n'.join(lines[-12:])
    message = (head + '\n' + detail).replace('%', '%25').replace('\r', '').replace('\n', '%0A')
    print(f'::error title={head[:120]}::{message[:3500]}')
summary = [l for l in text.splitlines() if l.startswith(('Ran ', 'FAILED', 'OK'))]
if summary:
    print('::notice title=unittest summary::' + ' | '.join(summary))
