"""
PerformanceOverlay — Floating always-on-top widget showing live model metrics.

Displays: model name, TPS, latency, VRAM GB, model state.
Draggable. Toggle via MenuPanel signal.
"""

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsDropShadowEffect,
)

from app.config import Colors, OVERLAY_OPACITY, OVERLAY_WIDTH, OVERLAY_HEIGHT


class PerformanceOverlay(QWidget):
    """
    Frameless floating overlay (FPS-counter style).

    Use show()/hide() to toggle. Call update_* methods to refresh values.
    Drag by clicking anywhere on the widget.
    """

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(OVERLAY_WIDTH, OVERLAY_HEIGHT)

        self._drag_pos: QPoint | None = None
        self._model_name  = "—"
        self._tps         = 0.0
        self._latency     = 0.0
        self._vram_gb     = 0.0
        self._state       = "Idle"

        self._build_ui()
        self._position_default()

    # ── UI Construction ───────────────────────────────────────────────────

    def _build_ui(self):
        # Outer with drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Inner container (rounded, semi-transparent)
        self._container = QFrame()
        self._container.setObjectName("overlayContainer")
        self._container.setStyleSheet(
            f"""
            QFrame#overlayContainer {{
                background-color: rgba(14, 14, 20, {int(OVERLAY_OPACITY * 255)});
                border: 1px solid rgba(108, 99, 255, 0.4);
                border-radius: 14px;
            }}
            """
        )
        inner = QVBoxLayout(self._container)
        inner.setContentsMargins(14, 10, 14, 10)
        inner.setSpacing(5)

        # ── Title row + close button ───────────────────────────────────────
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)

        dot = QLabel("◉")
        dot.setStyleSheet(f"color: {Colors.ACCENT}; font-size: 12px; background: transparent;")
        title_row.addWidget(dot)

        title_lbl = QLabel("Performance")
        title_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; "
            f"font-weight: 700; background: transparent; letter-spacing: 0.5px;"
        )
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(18, 18)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; "
            f"color: {Colors.TEXT_MUTED}; font-size: 11px; }}"
            f"QPushButton:hover {{ color: {Colors.ERROR}; }}"
        )
        close_btn.clicked.connect(self.hide)
        title_row.addWidget(close_btn)
        inner.addLayout(title_row)

        # ── Separator ─────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: rgba(108, 99, 255, 0.3);")
        inner.addWidget(sep)

        # ── Metric rows ───────────────────────────────────────────────────
        self._model_lbl   = self._make_row(inner, "Model",   "—",   Colors.ACCENT)
        self._tps_lbl     = self._make_row(inner, "⚡ TPS",  "—",   Colors.TPS_COLOR)
        self._lat_lbl     = self._make_row(inner, "⏱ Lat",  "—",   Colors.LATENCY_COLOR)
        self._vram_lbl    = self._make_row(inner, "🎮 VRAM", "—",   Colors.VRAM_COLOR)
        self._state_lbl   = self._make_row(inner, "State",   "Idle", Colors.STATE_IDLE)

        layout.addWidget(self._container)

    @staticmethod
    def _make_row(layout: QVBoxLayout, label: str, value: str, color: str) -> QLabel:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 11px; "
            f"background: transparent; min-width: 52px;"
        )
        row.addWidget(lbl)
        row.addStretch()

        val = QLabel(value)
        val.setAlignment(Qt.AlignmentFlag.AlignRight)
        val.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: 700; background: transparent;"
        )
        row.addWidget(val)
        layout.addLayout(row)
        return val

    def _position_default(self):
        """Place in bottom-right corner on first show."""
        try:
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                self.move(
                    geo.right()  - self.width()  - 24,
                    geo.bottom() - self.height() - 48,
                )
        except Exception:
            pass

    # ── Public update API ─────────────────────────────────────────────────

    def update_model(self, name: str):
        self._model_name = name
        # Trim long names
        display = name if len(name) <= 22 else name[:19] + "…"
        self._model_lbl.setText(display)

    def update_tps(self, tps: float):
        self._tps = tps
        self._tps_lbl.setText(f"{tps:.1f} tok/s" if tps > 0 else "—")

    def update_latency(self, latency: float):
        self._latency = latency
        self._lat_lbl.setText(f"{latency:.2f}s" if latency > 0 else "—")

    def update_vram(self, used_gb: float, total_gb: float):
        self._vram_gb = used_gb
        if total_gb > 0:
            self._vram_lbl.setText(f"{used_gb:.1f}/{total_gb:.1f} GB")
        else:
            self._vram_lbl.setText("N/A")

    def update_state(self, state: str):
        self._state = state
        state_colors = {
            "Idle":    Colors.STATE_IDLE,
            "Loading": Colors.STATE_LOADING,
            "Running": Colors.STATE_RUNNING,
            "Error":   Colors.STATE_ERROR,
        }
        color = state_colors.get(state, Colors.STATE_IDLE)
        self._state_lbl.setText(state)
        self._state_lbl.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: 700; background: transparent;"
        )

    # ── Dragging ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
