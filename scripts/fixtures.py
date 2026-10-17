"""Public synthetic PDFs only. These passwords are test fixtures, not credentials."""
from pathlib import Path
from pypdf import PdfWriter

KNOWN='rar-demo-2026'
UNKNOWN='synthetic-not-supplied'


def create_fixtures(root):
    source=Path(root)/'Source';source.mkdir(parents=True,exist_ok=True)
    for name,password in [('Finance/Monthly-statement.pdf',KNOWN),('Office/Invoice-1042.pdf',KNOWN),('Archive/Password-needed.pdf',UNKNOWN),('Guides/Welcome.pdf',None),('Office/Permissions-only.pdf','')]:
        path=source/name;path.parent.mkdir(exist_ok=True,parents=True)
        writer=PdfWriter();writer.add_blank_page(width=595,height=842)
        writer.add_metadata({'/Title':'RAR synthetic validation document','/Author':'RAR automated QA'})
        if password is not None:writer.encrypt(password,owner_password='synthetic-owner',algorithm='AES-256')
        with path.open('wb') as output:writer.write(output)
    return source
