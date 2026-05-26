"""
UploadArea — Drag-and-drop / click-to-browse widget for uploading
images and videos.
"""

import os
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QFont
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QFileDialog, QSizePolicy,
)

from app.config import ALL_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, Colors


class UploadArea(QFrame):
    """
    Central drop zone displayed before any conversation starts.
    Emits file_selected(path) when a valid file is chosen.
    """

    file_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("uploadArea")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(300, 220)
        self.setMaximumSize(480, 300)
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        # ── Icon ─────────────────────────────────────────
        icon_label = QLabel("📷")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 48px; background: transparent;")
        layout.addWidget(icon_label)

        # ── Title ────────────────────────────────────────
        title = QLabel("Upload an Image or Video")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; "
            f"font-weight: 600; background: transparent;"
        )
        layout.addWidget(title)

        # ── Subtitle ─────────────────────────────────────
        subtitle = QLabel("Drag & drop here, or click to browse")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; background: transparent;"
        )
        layout.addWidget(subtitle)

        # ── Formats ──────────────────────────────────────
        formats = QLabel("JPG · PNG · MP4 · AVI")
        formats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        formats.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 11px; background: transparent;"
        )
        layout.addWidget(formats)

    # ── Click to browse ──────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._browse()

    def _browse(self):
        exts = " ".join(f"*{e}" for e in ALL_EXTENSIONS)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image or Video",
            "",
            f"Media Files ({exts})",
        )
        if path:
            self.file_selected.emit(path)

    # ── Drag-and-drop ────────────────────────────────────
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(ALL_EXTENSIONS):
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(ALL_EXTENSIONS):
                self.file_selected.emit(path)
                return
