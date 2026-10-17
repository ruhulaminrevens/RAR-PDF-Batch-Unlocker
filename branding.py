"""Shared application identity; assets resolve in source and PyInstaller builds."""
from pathlib import Path
import sys

APP_NAME = 'RAR PDF Batch Unlocker'
APP_ID = 'RARTools.PDFBatchUnlocker'
VERSION = '1.2.0'


def asset_path(name):
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'assets' / name


def prepare_windows():
    if sys.platform != 'win32':
        return
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    # Set DPI awareness before Tk creates its first window. Older Windows fallback.
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        ctypes.windll.user32.SetProcessDPIAware()


def apply_window_icon(window):
    import tkinter as tk
    window._brand_icon = tk.PhotoImage(file=str(asset_path('app-64.png')))
    window.iconphoto(True, window._brand_icon)
    if sys.platform == 'win32':
        window.iconbitmap(default=str(asset_path('app.ico')))
        window.iconbitmap(str(asset_path('app.ico')))
        window.update_idletasks()
        # Native title bar remains accessible and supports normal Windows snapping.
        import ctypes
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        dark = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), 4)
