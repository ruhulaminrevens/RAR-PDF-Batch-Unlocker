"""Windows installed-GUI QA with public synthetic fixtures and actual mouse/keyboard input."""
import argparse
import ctypes
from ctypes import wintypes
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import ImageGrab
from branding import APP_NAME, VERSION
from scripts.fixtures import create_fixtures, KNOWN


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--exe',required=True);parser.add_argument('--qa',default='qa');args=parser.parse_args()
    qa=Path(args.qa).resolve();screens=qa/'screenshots';screens.mkdir(parents=True,exist_ok=True)
    user32=ctypes.windll.user32
    user32.SetProcessDPIAware()
    # Public data in a predictable local folder. Never use the user's documents.
    root=qa/'installed-demo';src=create_fixtures(root);dest=root/'Output'
    before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in src.rglob('*.pdf')}
    coords=json.loads((qa/'ui-coordinates.json').read_text())
    proc=subprocess.Popen([args.exe]);hwnd=0
    try:
        deadline=time.monotonic()+30
        while time.monotonic()<deadline and not hwnd:
            hwnd=user32.FindWindowW(None,f'{APP_NAME} · {VERSION}');time.sleep(.2)
            if proc.poll() is not None:raise RuntimeError('Installed GUI exited during startup')
        if not hwnd:raise RuntimeError('Installed application window not found')
        user32.ShowWindow(hwnd,9);user32.SetForegroundWindow(hwnd)
        # Match the source capture's client size, retaining native frame dimensions.
        client=wintypes.RECT();outer=wintypes.RECT()
        user32.GetClientRect(hwnd,ctypes.byref(client));user32.GetWindowRect(hwnd,ctypes.byref(outer))
        user32.MoveWindow(hwnd,outer.left,outer.top,1320+(outer.right-outer.left-client.right),960+(outer.bottom-outer.top-client.bottom),True)
        time.sleep(1)
        def click(key):
            x,y=coords[key];user32.SetCursorPos(x,y);user32.mouse_event(2,0,0,0,0);user32.mouse_event(4,0,0,0,0);time.sleep(.15)
        def key(v):user32.keybd_event(v,0,0,0);user32.keybd_event(v,0,2,0)
        def enter_text(text):
            user32.keybd_event(0x11,0,0,0);key(0x41);user32.keybd_event(0x11,0,2,0)
            # WM_CHAR to the focused Tk native window avoids keyboard-layout dependence.
            info=GUITHREADINFO();info.cbSize=ctypes.sizeof(info)
            user32.GetGUIThreadInfo(0,ctypes.byref(info))
            if not info.hwndFocus:raise RuntimeError('No focused edit control')
            for ch in text:user32.SendMessageW(info.hwndFocus,0x0102,ord(ch),0)
        def snap(name):
            point=wintypes.POINT(0,0);user32.ClientToScreen(hwnd,ctypes.byref(point))
            im=ImageGrab.grab(bbox=(point.x,point.y,point.x+1320,point.y+960));im.save(screens/name)
        click('Source folder');enter_text(str(src))
        click('Output folder');enter_text(str(dest))
        click('password_nav');click('password');enter_text(KNOWN);key(0x0D)
        click('workspace_nav');snap('installed-ready.png')
        click('start')
        # Confirmation is part of the actual GUI flow, not patched in installed QA.
        deadline=time.monotonic()+20;confirm=0
        while time.monotonic()<deadline and not confirm:
            confirm=user32.FindWindowW(None,'Confirm batch');time.sleep(.2)
        if not confirm:raise RuntimeError('Installed GUI never reached batch confirmation')
        user32.SetForegroundWindow(confirm);key(0x0D)
        deadline=time.monotonic()+90;rows=[];report=None
        while time.monotonic()<deadline:
            reports=list(dest.glob('unlock-report-*.csv')) if dest.exists() else []
            if reports:
                report=reports[0]
                try:
                    with report.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
                except PermissionError:pass
                if len(rows)==5:break
            time.sleep(.2)
        counts={}
        for row in rows:counts[row['status']]=counts.get(row['status'],0)+1
        expected={'Unlocked':3,'PasswordNotMatched':1,'SkippedUnencrypted':1}
        if counts!=expected:raise RuntimeError(f'Installed GUI results differ: {counts}')
        qpdf=Path(args.exe).parent/'qpdf/bin/qpdf.exe'
        for pdf in dest.rglob('*.pdf'):
            result=subprocess.run([str(qpdf),'--is-encrypted',str(pdf)],capture_output=True)
            if result.returncode!=2:raise RuntimeError('Installed output still encrypted')
        if before!={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in before}:raise RuntimeError('Originals changed')
        if KNOWN in report.read_text(encoding='utf-8-sig'):raise RuntimeError('Password leaked to report')
        time.sleep(.6);snap('installed-batch.png')
        (qa/'installed-validation.json').write_text(json.dumps({'counts':counts,'originals_unchanged':True,'outputs_verified_unencrypted':3,'password_absent_from_report':True,'interaction':'Actual installed EXE, mouse/keyboard input and confirmation dialog','platform':sys.platform},indent=2))
        user32.PostMessageW(hwnd,0x0010,0,0);proc.wait(timeout=15)
        if proc.returncode!=0:raise RuntimeError('Installed app did not exit cleanly')
    finally:
        if proc.poll() is None:proc.terminate();proc.wait(timeout=10)


class GUITHREADINFO(ctypes.Structure):
    _fields_=[('cbSize',wintypes.DWORD),('flags',wintypes.DWORD),('hwndActive',wintypes.HWND),('hwndFocus',wintypes.HWND),('hwndCapture',wintypes.HWND),('hwndMenuOwner',wintypes.HWND),('hwndMoveSize',wintypes.HWND),('hwndCaret',wintypes.HWND),('rcCaret',wintypes.RECT)]

if __name__=='__main__':main()
