"""Local crash diagnostics. Metadata only; every session password is redacted before writing."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import threading
import traceback

_secrets: set[str] = set()
_lock = threading.Lock()
_logger = logging.getLogger('rar-pdf')


def log_dir() -> Path:
    base = os.environ.get('LOCALAPPDATA') or str(Path.home() / '.local' / 'state')
    return Path(base) / 'RAR PDF Batch Unlocker' / 'logs'


def remember_secret(value: str):
    if value:
        with _lock:
            _secrets.add(value)


def forget_secrets():
    with _lock:
        _secrets.clear()


def redact(text: str) -> str:
    with _lock:
        secrets = sorted(_secrets, key=len, reverse=True)
    for secret in secrets:
        text = text.replace(secret, '[redacted]')
    return text


class _Redacting(logging.Formatter):
    def format(self, record):
        return redact(super().format(record))


def _ensure_handler():
    if _logger.handlers:
        return
    try:
        folder = log_dir()
        folder.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(folder / 'app.log', maxBytes=512 * 1024, backupCount=3, encoding='utf-8')
    except OSError:
        handler = logging.NullHandler()
    handler.setFormatter(_Redacting('%(asctime)s %(levelname)s %(message)s'))
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)


def log_event(message: str):
    _ensure_handler()
    _logger.info(message)


def log_exception(exc_type, exc, tb, where='app'):
    _ensure_handler()
    _logger.error('Unhandled error in %s:\n%s', where, ''.join(traceback.format_exception(exc_type, exc, tb)))


def install(root):
    """Route Tk callback, main-thread and worker-thread errors to the redacted log."""
    _ensure_handler()

    def tk_error(exc_type, exc, tb):
        log_exception(exc_type, exc, tb, 'window')
        try:
            from tkinter import messagebox
            messagebox.showerror('Unexpected error', 'Something went wrong. Your files were not changed by this error.\n'
                                 f'Details (no passwords) were saved to:\n{log_dir()}', parent=root)
        except Exception:
            pass
    root.report_callback_exception = tk_error
    sys.excepthook = lambda t, e, tb: log_exception(t, e, tb, 'main')
    threading.excepthook = lambda args: log_exception(args.exc_type, args.exc_value, args.exc_traceback,
                                                      f'thread {args.thread.name if args.thread else ""}')
