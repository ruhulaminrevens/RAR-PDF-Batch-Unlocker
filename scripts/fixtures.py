"""Public synthetic PDFs only. These passwords are test fixtures, not credentials."""
from pathlib import Path
import sys
from pypdf import PdfWriter

KNOWN = 'rar-demo-2026'
UNKNOWN = 'synthetic-not-supplied'


def _long(path):
    text = str(Path(path).resolve())
    if sys.platform == 'win32' and len(text) >= 240:
        return '\\\\?\\' + text
    return text


def make_pdf(path, password=None, pages=1, text_bytes=0):
    """Write one synthetic PDF. ``password=''`` gives a permissions-only file."""
    path = Path(path)
    import os
    os.makedirs(_long(path.parent), exist_ok=True)
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)
    meta = {'/Title': 'RAR synthetic validation document', '/Author': 'RAR automated QA'}
    if text_bytes:
        meta['/Subject'] = 'x' * text_bytes  # pads the file to a chosen size
    writer.add_metadata(meta)
    if password is not None:
        writer.encrypt(password, owner_password='synthetic-owner', algorithm='AES-256')
    with open(_long(path), 'wb') as output:
        writer.write(output)
    return path


def create_fixtures(root):
    source = Path(root) / 'Source'
    source.mkdir(parents=True, exist_ok=True)
    for name, password in [('Finance/Monthly-statement.pdf', KNOWN), ('Office/Invoice-1042.pdf', KNOWN),
                           ('Archive/Password-needed.pdf', UNKNOWN), ('Guides/Welcome.pdf', None),
                           ('Office/Permissions-only.pdf', '')]:
        make_pdf(source / name, password)
    return source
