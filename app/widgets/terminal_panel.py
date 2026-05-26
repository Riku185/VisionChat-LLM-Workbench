"""
TerminalPanel — A sliding terminal overlay at the bottom of the chat area.
Runs commands via QProcess and displays real-time output.
"""

import os
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QLineEdit, QPushButton, QLabel, QWidget,
)
from PyQt6.QtCore import QProcess

from app.config import Colors, TERMINAL_HEIGHT


class TerminalPanel(QFrame):
    """Slide-up terminal overlay for running shell commands."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("terminalPanel")
        self.setFixedHeight(0)  # Starts collapsed
        self._target_height = TERMINAL_HEIGHT
        self._is_open = False

        self._process: QProcess | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # ── Header ───────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("⌨  Terminal")
        title.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; "
            f"font-weight: 700; background: transparent;"
        )
        header.addWidget(title)
        header.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(
            f"background: transparent; color: {Colors.TEXT_SECONDARY}; "
            f"border: none; font-size: 16px; border-radius: 14px;"
        )
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.toggle)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # ── Output area ──────────────────────────────────
        self._output = QPlainTextEdit()
        self._output.setObjectName("terminalOutput")
        self._output.setReadOnly(True)
        self._output.setFont(QFont("Cascadia Code", 12))
        layout.addWidget(self._output)

        # ── Input line ───────────────────────────────────
        self._input = QLineEdit()
        self._input.setObjectName("terminalInput")
        self._input.setPlaceholderText("Enter command...")
        self._input.setFont(QFont("Cascadia Code", 12))
        self._input.returnPressed.connect(self._run_command)
        layout.addWidget(self._input)

    # ── Toggle animation ─────────────────────────────────
    def toggle(self):
        anim = QPropertyAnimation(self, b"fixedHeight")
        # We animate maximumHeight + minimumHeight to simulate fixedHeight
        self._is_open = not self._is_open
        start_h = self.height()
        end_h = self._target_height if self._is_open else 0

        anim = QPropertyAnimation(self, b"maximumHeight")
        anim.setDuration(300)
        anim.setStartValue(start_h)
        anim.setEndValue(end_h)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        # Also animate minimum height
        anim2 = QPropertyAnimation(self, b"minimumHeight")
        anim2.setDuration(300)
        anim2.setStartValue(start_h)
        anim2.setEndValue(end_h)
        anim2.setEasingCurve(QEasingCurve.Type.InOutCubic)

        anim.start()
        anim2.start()

        # Keep references so they aren't garbage-collected
        self._anim = anim
        self._anim2 = anim2

        if self._is_open:
            self._input.setFocus()

    @property
    def is_open(self) -> bool:
        return self._is_open

    # ── Run command ──────────────────────────────────────
    def _run_command(self):
        cmd = self._input.text().strip()
        if not cmd:
            return

        self._output.appendPlainText(f"> {cmd}")
        self._input.clear()

        self._process = QProcess(self)
        self._process.setProcessChannelMode(
            QProcess.ProcessChannelMode.MergedChannels
        )
        self._process.readyReadStandardOutput.connect(self._read_output)
        self._process.finished.connect(self._on_finished)
        self._process.start("cmd.exe", ["/c", cmd])

    def _read_output(self):
        if self._process:
            data = self._process.readAllStandardOutput().data().decode(
                "utf-8", errors="replace"
            )
            self._output.insertPlainText(data)
            # Auto-scroll
            sb = self._output.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _on_finished(self):
        self._output.appendPlainText("")  # blank line separator
