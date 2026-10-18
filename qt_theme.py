"""Design tokens, stylesheet and icon helpers for the Qt interface.

Dark, modern palette from the approved concept: deep navy ground, cyan and
violet accents, rounded cards. Colours are checked for 4.5:1 text contrast.
"""
from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# ---- tokens ----
BG = '#070b16'
SIDEBAR = '#0b1120'
SURFACE = '#0d1626'
RAISED = '#101a2d'
INPUT = '#070e1c'
BORDER = '#20304e'
BORDER_SOFT = '#1b2742'
TEXT = '#e9f0fb'
MUTED = '#9fb1cf'
FAINT = '#7f93b4'
CYAN = '#5ce0e0'
VIOLET = '#9b8cff'
GREEN = '#5fe0b0'
AMBER = '#ffc56e'
RED = '#ff9aa6'
BLUE = '#3b6ef5'
BLUE_HOVER = '#5684ff'
NAV_ACTIVE_BG = '#12294a'
NAV_ACTIVE_BORDER = '#28518a'
NAV_ACTIVE_TEXT = '#bdecff'

MONO = '"IBM Plex Mono","Cascadia Mono","Consolas",monospace'
SANS = '"Segoe UI","Nirmala UI","Noto Sans Bengali",sans-serif'

# status colour by core status
STATUS_TONE = {
    'Unlocked': GREEN, 'CopiedUnencrypted': GREEN,
    'PasswordNotMatched': RED, 'DecryptFailed': RED, 'VerificationFailed': RED,
    'InvalidPDF': AMBER, 'InspectionFailed': AMBER, 'Timeout': AMBER,
    'FileLocked': AMBER, 'AccessDenied': AMBER, 'DiskFull': RED, 'PathTooLong': AMBER,
    'SourceMissing': AMBER, 'OutputConflict': AMBER, 'Error': RED, 'Cancelled': MUTED,
    'PasswordRequired': AMBER, 'PermissionRestricted': VIOLET, 'Unencrypted': CYAN,
    'SkippedUnencrypted': VIOLET, 'SkippedExisting': VIOLET, 'DryRun': CYAN,
}


def tone(status: str) -> str:
    return STATUS_TONE.get(status, TEXT)


def stylesheet() -> str:
    return f"""
* {{ font-family: {SANS}; font-size: 13px; color: {TEXT}; outline: none; }}
QWidget#Root, QStackedWidget, QScrollArea, QWidget#PageBody {{ background: {BG}; }}
QScrollArea {{ border: none; }}
QWidget#Sidebar {{ background: {SIDEBAR}; border-right: 1px solid {BORDER_SOFT}; }}

QLabel {{ background: transparent; }}
QLabel[kind="eyebrow"] {{ color: {CYAN}; font-size: 11px; font-weight: 600; letter-spacing: 2px; }}
QLabel[kind="h1"] {{ font-size: 28px; font-weight: 700; }}
QLabel[kind="section"] {{ font-size: 15px; font-weight: 600; }}
QLabel[kind="muted"] {{ color: {MUTED}; }}
QLabel[kind="faint"] {{ color: {FAINT}; font-size: 12px; }}
QLabel[kind="fieldlabel"] {{ color: #8ea2c2; font-size: 11px; font-weight: 600; letter-spacing: .4px; }}
QLabel[kind="metric"] {{ font-size: 30px; font-weight: 600; font-family: {MONO}; }}
QLabel[kind="metriclabel"] {{ color: #90a2c2; font-size: 10px; font-weight: 600; letter-spacing: 1.4px; }}
QLabel[kind="brand"] {{ font-size: 16px; font-weight: 700; letter-spacing: .3px; }}
QLabel[kind="brandsub"] {{ color: {FAINT}; font-size: 10px; font-weight: 600; letter-spacing: 2.4px; }}
QLabel[kind="mono"] {{ font-family: {MONO}; color: {MUTED}; }}

QFrame#Card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 18px; }}
QFrame#Metric {{ background: {RAISED}; border: 1px solid {BORDER}; border-radius: 16px; }}
QFrame#AccentLine {{ border: none; border-radius: 1px; }}

QPushButton {{ background: #16233b; border: 1px solid #2a3c5c; border-radius: 11px; padding: 10px 16px; font-size: 13px; font-weight: 600; color: #cfe0f6; }}
QPushButton:hover {{ background: #1d2d49; }}
QPushButton:pressed {{ background: #16263f; }}
QPushButton:focus {{ border: 1px solid {CYAN}; }}
QPushButton:disabled {{ color: #6d80a2; background: #101a2c; border-color: #1d2b42; }}
QPushButton[kind="primary"] {{ background: {BLUE}; border: none; color: #ffffff; font-weight: 700; padding: 12px 22px; }}
QPushButton[kind="primary"]:hover {{ background: {BLUE_HOVER}; }}
QPushButton[kind="primary"]:disabled {{ background: #22365e; color: #8fa0bd; }}
QPushButton[kind="danger"] {{ color: {RED}; background: transparent; border: 1px solid #3a4661; }}
QPushButton[kind="danger"]:hover {{ background: #2a1c25; }}
QPushButton[kind="ghost"] {{ background: transparent; border: 1px solid transparent; color: {MUTED}; text-align: left; padding: 12px 14px; }}
QPushButton[kind="ghost"]:hover {{ background: #132440; color: {TEXT}; }}
QPushButton[kind="nav"] {{ background: transparent; border: 1px solid transparent; border-radius: 12px; color: {MUTED}; text-align: left; padding: 11px 14px; font-weight: 500; }}
QPushButton[kind="nav"]:hover {{ background: #132440; color: {TEXT}; }}
QPushButton[kind="nav"][active="true"] {{ background: {NAV_ACTIVE_BG}; border: 1px solid {NAV_ACTIVE_BORDER}; color: {NAV_ACTIVE_TEXT}; font-weight: 600; }}

QLineEdit, QPlainTextEdit, QComboBox, QSpinBox {{ background: {INPUT}; border: 1px solid #21314f; border-radius: 11px; padding: 10px 13px; selection-background-color: #2a4e7c; color: #dbe6f6; }}
QLineEdit[mono="true"] {{ font-family: {MONO}; font-size: 12.5px; }}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 1px solid {CYAN}; }}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{ color: #6d80a2; background: #0b1424; }}
QLineEdit[invalid="true"] {{ border: 1px solid {RED}; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox QAbstractItemView {{ background: {RAISED}; border: 1px solid {BORDER}; selection-background-color: #2a4e7c; color: {TEXT}; outline: none; }}

QCheckBox, QRadioButton {{ spacing: 9px; background: transparent; color: {TEXT}; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 18px; height: 18px; border: 1px solid #2a3c5c; background: {INPUT}; }}
QCheckBox::indicator {{ border-radius: 5px; }}
QRadioButton::indicator {{ border-radius: 9px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{ background: {BLUE}; border-color: {BLUE}; }}

QProgressBar {{ background: #13203a; border: none; border-radius: 5px; height: 9px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: {CYAN}; border-radius: 5px; }}

QTableView {{ background: {SURFACE}; alternate-background-color: #0b1424; border: none; gridline-color: transparent; selection-background-color: #1c3c63; selection-color: #ffffff; }}
QTableView::item {{ padding: 6px 10px; border-bottom: 1px solid #141f36; }}
QHeaderView::section {{ background: {RAISED}; color: #8ea2c2; font-size: 10.5px; font-weight: 700; letter-spacing: 1px; padding: 11px 12px; border: none; border-bottom: 1px solid {BORDER}; }}
QListWidget {{ background: {INPUT}; border: 1px solid #21314f; border-radius: 11px; padding: 4px; color: {TEXT}; outline: none; }}
QListWidget::item {{ padding: 7px 9px; border-radius: 7px; }}
QListWidget::item:selected {{ background: #1c3c63; color: #ffffff; }}

QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #2c4364; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #38527c; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #2c4364; border-radius: 5px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QToolTip {{ background: {RAISED}; color: {TEXT}; border: 1px solid {BORDER}; padding: 6px 8px; border-radius: 6px; }}
QFrame#Chip {{ border-radius: 999px; }}
"""


# ---- icons (inline stroke SVG rendered to a QIcon) ----
_ICONS = {
    'workspace': '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M3 9h18M8 4v16"/>',
    'key': '<circle cx="8" cy="15" r="4"/><path d="M11 12l8-8M16 7l2 2"/>',
    'results': '<path d="M5 4h14v16H5z"/><path d="M8 9h8M8 13h8M8 17h5"/>',
    'tools': '<path d="M6 3h8l4 4v14H6z"/><path d="M12 11v6M9 14h6"/>',
    'settings': '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2"/>',
    'help': '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .9-1 1.7M12 17h.01"/>',
    'play': '<path d="M7 5l12 7-12 7z"/>',
    'stop': '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    'shield': '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    'search': '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5"/>',
    'merge': '<path d="M4 7h10v10H4z"/><path d="M10 7V5h10v10h-2"/>',
    'split': '<path d="M5 4h9l5 5v11H5z"/><path d="M4 12h16"/>',
    'image': '<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="8.5" cy="10" r="1.6"/><path d="M5 17l5-4 4 3 3-2 4 3"/>',
    'export': '<path d="M6 3h8l4 4v14H6z"/><path d="M9 13l3 3 3-3M12 9v7"/>',
    'doc': '<path d="M6 3h8l4 4v14H6z"/><path d="M9 12h6M9 16h6"/>',
    'chevron': '<path d="M6 9l6 6 6-6"/>',
    'lock': '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    'brand': '<path d="M7 3h8l4 4v14H7z"/><path d="M15 3v4h4"/><rect x="9.5" y="12.5" width="6" height="5" rx="1.2"/><path d="M11 12.5v-1.3a1.6 1.6 0 0 1 3.2 0"/>',
}


def icon(name: str, color: str = TEXT, size: int = 40) -> QIcon:
    body = _ICONS.get(name, _ICONS['help'])
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           f'stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{body}</svg>')
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    painter.end()
    return QIcon(pix)


def pixmap(name: str, color: str = TEXT, size: int = 22) -> QPixmap:
    return icon(name, color, size).pixmap(size, size)
