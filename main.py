"""
Vision Chat — Entry Point
A modern desktop application for visual chat with any Ollama model.
"""

import sys
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt

from app.main_window import MainWindow


def load_stylesheet() -> str:
    """Load the QSS stylesheet from the app directory."""
    qss_path = os.path.join(os.path.dirname(__file__), "app", "styles.qss")
    try:
        with open(qss_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"[WARN] Stylesheet not found: {qss_path}")
        return ""


def main():
    # High-DPI scaling (Qt6 handles this well by default)
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    app = QApplication(sys.argv)
    app.setApplicationName("Vision Chat")
    app.setOrganizationName("VisionChat")

    # ── Font ─────────────────────────────────────────────
    font = QFont("Segoe UI", 10)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app.setFont(font)

    # ── Stylesheet ───────────────────────────────────────
    stylesheet = load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    # ── Window ───────────────────────────────────────────
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
