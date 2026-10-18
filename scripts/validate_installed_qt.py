"""Smoke the installed Qt executable on Windows: launch it, confirm its window
appears and renders, screenshot it, then close it cleanly. Functional coverage
is provided by the offscreen Qt tests run against the same build."""
import argparse
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import ImageGrab
from branding import APP_NAME, VERSION


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', required=True)
    ap.add_argument('--qa', default='qa')
    args = ap.parse_args()
    qa = Path(args.qa).resolve(); screens = qa / 'screenshots'; screens.mkdir(parents=True, exist_ok=True)
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    title = f'{APP_NAME} · {VERSION}'

    proc = subprocess.Popen([args.exe])
    hwnd = 0
    try:
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline and not hwnd:
            hwnd = user32.FindWindowW(None, title)
            if proc.poll() is not None:
                raise RuntimeError(f'Installed Qt app exited during startup (code {proc.returncode})')
            time.sleep(0.3)
        if not hwnd:
            ImageGrab.grab().save(screens / 'installed-failure-desktop.png')
            raise RuntimeError('Installed Qt window did not appear')
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
        time.sleep(2.0)  # let the first paint settle
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        if (rect.right - rect.left) < 400 or (rect.bottom - rect.top) < 300:
            raise RuntimeError('Installed Qt window is too small to be real')
        image = ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom))
        if len(image.getcolors(image.width * image.height) or []) < 20:
            raise RuntimeError('Installed Qt window capture is blank')
        image.save(screens / 'installed-window.png')
        (qa / 'installed-validation.json').write_text(json.dumps({
            'toolkit': 'PySide6/Qt', 'app_version': VERSION,
            'window_title_found': title, 'window_size': [rect.right - rect.left, rect.bottom - rect.top],
            'rendered_non_blank': True, 'interaction': 'Installed EXE launched; window found and captured',
        }, indent=2), encoding='utf-8')
        print('Installed Qt window verified:', rect.right - rect.left, 'x', rect.bottom - rect.top)
        user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            pass
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True)


if __name__ == '__main__':
    main()
