"""Reusable Qt building blocks: cards, metric tiles, nav buttons, chips."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
                               QPushButton, QSizePolicy, QVBoxLayout, QWidget)

import qt_theme as T


def shadow(widget: QWidget, blur: int = 34, dy: int = 14, alpha: int = 90):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setXOffset(0)
    effect.setYOffset(dy)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)
    return widget


def label(text='', kind=None, wrap=False) -> QLabel:
    lab = QLabel(text)
    if kind:
        lab.setProperty('kind', kind)
    if wrap:
        lab.setWordWrap(True)
    return lab


class Card(QFrame):
    """Rounded surface card with an optional glowing accent line on top."""
    def __init__(self, accent: str | None = None, parent=None, pad=(20, 20, 20, 20), gap=12, soft_shadow=True):
        super().__init__(parent)
        self.setObjectName('Card')
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        if accent:
            line = QFrame()
            line.setObjectName('AccentLine')
            line.setFixedHeight(2)
            line.setStyleSheet(f'background:{accent};border-radius:1px;')
            glow = QGraphicsDropShadowEffect(line)
            glow.setBlurRadius(14); glow.setXOffset(0); glow.setYOffset(0); glow.setColor(QColor(accent))
            line.setGraphicsEffect(glow)
            outer.addWidget(line)
        self.body = QVBoxLayout()
        self.body.setContentsMargins(*pad)
        self.body.setSpacing(gap)
        holder = QWidget()
        holder.setLayout(self.body)
        holder.setStyleSheet('background: transparent;')
        outer.addWidget(holder)
        if soft_shadow:
            shadow(self)

    def add(self, widget, **kw):
        self.body.addWidget(widget, **kw)
        return widget

    def add_layout(self, lay):
        self.body.addLayout(lay)
        return lay


class MetricTile(QFrame):
    def __init__(self, caption: str, color: str, parent=None):
        super().__init__(parent)
        self.setObjectName('Metric')
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        line = QFrame(); line.setFixedHeight(2); line.setStyleSheet(f'background:{color};border-radius:1px;')
        glow = QGraphicsDropShadowEffect(line); glow.setBlurRadius(12); glow.setXOffset(0); glow.setYOffset(0); glow.setColor(QColor(color))
        line.setGraphicsEffect(glow)
        lay.addWidget(line)
        inner = QVBoxLayout(); inner.setContentsMargins(16, 14, 16, 14); inner.setSpacing(3)
        self.value = label('—', 'metric'); self.value.setStyleSheet(f'color:{color};')
        inner.addWidget(self.value)
        inner.addWidget(label(caption.upper(), 'metriclabel'))
        box = QWidget(); box.setLayout(inner); box.setStyleSheet('background:transparent;')
        lay.addWidget(box)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set(self, value):
        self.value.setText(str(value))


class NavButton(QPushButton):
    def __init__(self, key: str, text: str, icon_name: str, on_click, parent=None):
        super().__init__(text.replace('&', '&&'), parent)  # && shows a literal ampersand
        self.key = key
        self._icon_name = icon_name
        self.setProperty('kind', 'nav')
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        from PySide6.QtCore import QSize
        self.setIconSize(QSize(18, 18))
        self.clicked.connect(lambda: on_click(key))
        self.set_active(False)

    def set_active(self, active: bool):
        self.setProperty('active', 'true' if active else 'false')
        color = T.CYAN if active else T.MUTED
        self.setIcon(T.icon(self._icon_name, color, 36))
        self.style().unpolish(self); self.style().polish(self)


class Chip(QFrame):
    """Pill-shaped status chip with a coloured dot."""
    def __init__(self, text: str, color: str, dot=True, parent=None):
        super().__init__(parent)
        self.setObjectName('Chip')
        bg = QColor(color); bg.setAlpha(32)
        self.setStyleSheet(f'background: rgba({bg.red()},{bg.green()},{bg.blue()},0.13); border-radius: 999px;')
        lay = QHBoxLayout(self); lay.setContentsMargins(11, 5, 12, 5); lay.setSpacing(6)
        if dot:
            d = QLabel(); d.setFixedSize(6, 6); d.setStyleSheet(f'background:{color};border-radius:3px;')
            lay.addWidget(d)
        t = QLabel(text); t.setStyleSheet(f'color:{color};font-size:12px;font-weight:600;background:transparent;')
        lay.addWidget(t)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)


def eyebrow_title(eyebrow: str, title: str) -> QVBoxLayout:
    lay = QVBoxLayout(); lay.setSpacing(6)
    lay.addWidget(label(eyebrow, 'eyebrow'))
    lay.addWidget(label(title, 'h1'))
    return lay


def icon_button(icon_name: str, color: str, text: str, kind=None, on_click=None) -> QPushButton:
    from PySide6.QtCore import QSize
    btn = QPushButton(text)
    btn.setIcon(T.icon(icon_name, '#ffffff' if kind == 'primary' else color, 34))
    btn.setIconSize(QSize(17, 17))
    btn.setCursor(Qt.PointingHandCursor)
    if kind:
        btn.setProperty('kind', kind)
    if on_click:
        btn.clicked.connect(on_click)
    return btn


# ---- drag-and-drop aware inputs ----
from PySide6.QtWidgets import QLineEdit, QListWidget  # noqa: E402


class DropLineEdit(QLineEdit):
    """A line edit that also accepts dropped files/folders via a callback."""
    def __init__(self, on_drop, parent=None):
        super().__init__(parent)
        self._on_drop = on_drop
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths and self._on_drop:
            self._on_drop(paths)
            e.acceptProposedAction()


class DropList(QListWidget):
    """A list widget that accepts dropped files/folders via a callback."""
    def __init__(self, on_drop, parent=None):
        super().__init__(parent)
        self._on_drop = on_drop
        self._paths = []
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths and self._on_drop:
            self._on_drop(paths)
            e.acceptProposedAction()
