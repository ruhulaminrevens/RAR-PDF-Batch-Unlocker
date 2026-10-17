"""Exercise the real GUI with synthetic PDFs and capture actual desktop pixels."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import ImageGrab
from app import App, find_qpdf
from scripts.fixtures import create_fixtures, KNOWN


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='qa/screenshots');parser.add_argument('--workspace',default='qa/demo')
    args=parser.parse_args();out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    root=Path(args.workspace).resolve();src=create_fixtures(root)
    app=App();app.geometry('1320x960+20+20');app.update()
    if app.winfo_screenwidth()<1400 or app.winfo_screenheight()<1060:
        app._shutdown();raise RuntimeError('Desktop too small for a complete screenshot')
    app.source.set(str(src));app.destination.set(str(root/'Output'))
    before={str(p.relative_to(src)):hashlib.sha256(p.read_bytes()).hexdigest() for p in src.rglob('*.pdf')}
    def capture(name,page):
        app._navigate(page);app.pages[page].canvas.yview_moveto(0);app.update()
        time.sleep(.3);app.update()
        image=ImageGrab.grab(bbox=(app.winfo_rootx(),app.winfo_rooty(),app.winfo_rootx()+app.winfo_width(),app.winfo_rooty()+app.winfo_height()))
        if len(image.getcolors(image.width*image.height) or [])<20:raise RuntimeError('Desktop capture is blank')
        image.save(out/name)
    def wait():
        deadline=time.monotonic()+90
        while app.busy and time.monotonic()<deadline:app.update();time.sleep(.03)
        if app.busy:raise RuntimeError('GUI batch timed out')
        app.update()
    try:
        with patch('app.messagebox.askyesno',return_value=True),patch('app.messagebox.showinfo'),patch('app.messagebox.showerror',side_effect=lambda title,body,**kw:(_ for _ in ()).throw(RuntimeError(title+': '+body))):
            capture('main-window.png','workspace')
            app._start(True);wait()
            assert app.counts=={'PasswordRequired':3,'Unencrypted':1,'PermissionRestricted':1},app.counts
            capture('security-analysis.png','results')
            app.password_groups['Finance']=[KNOWN];app.groupbox.configure(values=list(app.password_groups));app.group.set('Finance');app._update_count()
            app.mapping.insert('1.0','Finance=Finance\nOffice=Finance')
            app.pw_entry.insert(0,KNOWN)
            capture('password-groups.png','passwords')
            app.pw_entry.delete(0,'end')
            app._start(False);wait()
            assert app.counts=={'PasswordNotMatched':1,'Unlocked':3,'SkippedUnencrypted':1},app.counts
            capture('batch-workspace.png','workspace');capture('batch-results.png','results')
            capture('run-settings.png','settings')
            after={str(p.relative_to(src)):hashlib.sha256(p.read_bytes()).hexdigest() for p in src.rglob('*.pdf')}
            assert before==after,'Source files changed'
            # Capture positions from the real widgets for installed-GUI automation.
            coords={'client_size':[app.winfo_width(),app.winfo_height()],'client_origin':[app.winfo_rootx(),app.winfo_rooty()]}
            def record(key,w):
                coords[key]=[w.winfo_rootx()+w.winfo_width()//2,w.winfo_rooty()+w.winfo_height()//2]
            app._navigate('workspace');app.update()
            for label,w in app.path_entries.items():record(label,w)
            record('start',app.start_btn);record('password_nav',app.nav['passwords']);record('workspace_nav',app.nav['workspace'])
            app._navigate('passwords');app.update();record('password',app.pw_entry)
            (out.parent/'ui-coordinates.json').write_text(json.dumps(coords,indent=2))
            (out.parent/'source-gui-validation.json').write_text(json.dumps({'platform':sys.platform,'qpdf':find_qpdf(),'fixture_count':5,'counts':app.counts,'originals_unchanged':before==after,'screenshots':'Actual source GUI desktop captures; synthetic fixtures only'},indent=2))
    finally:app._shutdown()

if __name__=='__main__':main()
