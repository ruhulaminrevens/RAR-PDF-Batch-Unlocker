"""Capture the actual Inno wizard without installing or modifying user data."""
import argparse
from pathlib import Path
import subprocess
import time
import win32con
import win32gui
from PIL import ImageGrab

parser=argparse.ArgumentParser();parser.add_argument('--installer',required=True);parser.add_argument('--output',default='qa/screenshots/installer.png');args=parser.parse_args()
proc=subprocess.Popen([str(Path(args.installer).resolve()),'/SP-'])
try:
    hwnd=0;deadline=time.monotonic()+20
    while not hwnd and time.monotonic()<deadline:
        found=[]
        def visit(window,_):
            title=win32gui.GetWindowText(window)
            if win32gui.IsWindowVisible(window) and 'Setup' in title and 'RAR PDF Batch Unlocker' in title:found.append(window)
        win32gui.EnumWindows(visit,None)
        if found:hwnd=found[0]
        time.sleep(.2)
    if not hwnd:raise RuntimeError('Visible installer wizard not found')
    win32gui.SetForegroundWindow(hwnd);time.sleep(.4)
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    ImageGrab.grab(bbox=win32gui.GetWindowRect(hwnd)).save(out)
    win32gui.PostMessage(hwnd,win32con.WM_CLOSE,0,0)
    time.sleep(.3)
    def dismiss(window,_):
        if win32gui.IsWindowVisible(window) and win32gui.GetWindowText(window)=='Exit Setup':win32gui.PostMessage(window,win32con.WM_COMMAND,win32con.IDYES,0)
    win32gui.EnumWindows(dismiss,None)
    try:proc.wait(timeout=5)
    except subprocess.TimeoutExpired:subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True)
finally:
    if proc.poll() is None:subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True)
