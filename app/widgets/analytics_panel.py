"""
AnalyticsPanel — Session analytics dashboard shown as the right-menu flyout.

Displays summary cards (total tokens, requests, avg TPS, avg latency,
peak RAM, peak VRAM) and live pyqtgraph line/bar charts.
"""

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QWidget, QPushButton, QGridLayout,
)

from app.config import Colors, ANALYTICS_HISTORY
from app.models.session_stats import SessionStats


# ── _SummaryCard ─────────────────────────────────────────────────────────────

class _SummaryCard(QFrame):
    """A compact metric card with icon, value, and label."""

    def __init__(self, icon: str, label: str, color: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{ background-color: {Colors.BG_CARD}; "
            f"border: 1px solid {Colors.BORDER}; border-radius: 10px; }}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 20px; background: transparent; border: none;")
        layout.addWidget(icon_lbl)

        self._val = QLabel("—")
        self._val.setStyleSheet(
            f"color: {color}; font-size: 18px; font-weight: 700; "
            f"background: transparent; border: none;"
        )
        layout.addWidget(self._val)

        lbl = QLabel(label)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 10px; "
            f"background: transparent; border: none;"
        )
        layout.addWidget(lbl)

    def set_value(self, text: str):
        self._val.setText(text)


# ── _MiniChart ────────────────────────────────────────────────────────────────

class _MiniChart(QWidget):
    """A small pyqtgraph chart (line or bar) for the analytics panel."""

    def __init__(self, title: str, color: str, mode: str = "line", parent=None):
        super().__init__(parent)
        self._color = color
        self._mode  = mode

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(2)

        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; "
            f"font-weight: 600; background: transparent;"
        )
        layout.addWidget(lbl)

        self._plot = pg.PlotWidget()
        self._plot.setBackground(Colors.BG_DARK)
        self._plot.setFixedHeight(90)
        self._plot.hideAxis("bottom")
        self._plot.getAxis("left").setTextPen(pg.mkPen(Colors.TEXT_MUTED))
        self._plot.getAxis("left").setWidth(36)
        self._plot.setMouseEnabled(x=False, y=False)
        self._plot.hideButtons()
        self._plot.setMenuEnabled(False)
        layout.addWidget(self._plot)

        self._items: list = []

    def set_data(self, values: list[float]):
        """Refresh chart with new data series."""
        if not values:
            return

        # Clear old items
        for item in self._items:
            self._plot.removeItem(item)
        self._items.clear()

        x = np.arange(len(values), dtype=float)
        y = np.array(values, dtype=float)

        if self._mode == "bar":
            color = QColor(self._color)
            color.setAlpha(180)
            bg = pg.BarGraphItem(
                x=x, height=y, width=0.8,
                brush=pg.mkBrush(color),
                pen=pg.mkPen(self._color, width=1),
            )
            self._plot.addItem(bg)
            self._items.append(bg)
        else:
            pen   = pg.mkPen(color=self._color, width=2)
            curve = self._plot.plot(x, y, pen=pen)
            # Fill under
            fill_color = QColor(self._color)
            fill_color.setAlpha(40)
            zero_line  = self._plot.plot(x, np.zeros_like(y), pen=pg.mkPen(None))
            fill = pg.FillBetweenItem(curve, zero_line, brush=pg.mkBrush(fill_color))
            self._plot.addItem(fill)
            self._items += [curve, zero_line, fill]

        if len(y) > 0 and y.max() > 0:
            self._plot.setYRange(0, y.max() * 1.15, padding=0)


# ── AnalyticsPanel ────────────────────────────────────────────────────────────

class AnalyticsPanel(QFrame):
    """Session analytics dashboard (right flyout content)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("analyticsPanel")
        self._ss = SessionStats()
        self._build_ui()

        # Auto-refresh every 2 s
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(2000)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout  = QVBoxLayout(content)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # ── Header ────────────────────────────────────────────────────────
        hdr_row = QHBoxLayout()
        title = QLabel("📊  Session Analytics")
        title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 14px; "
            f"font-weight: 700; background: transparent;"
        )
        hdr_row.addWidget(title)
        hdr_row.addStretch()

        reset_btn = QPushButton("↺ Reset")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {Colors.TEXT_MUTED}; "
            f"border: 1px solid {Colors.BORDER}; border-radius: 6px; "
            f"padding: 4px 10px; font-size: 11px; }}"
            f"QPushButton:hover {{ color: {Colors.TEXT_PRIMARY}; }}"
        )
        reset_btn.clicked.connect(self._on_reset)
        hdr_row.addWidget(reset_btn)
        layout.addLayout(hdr_row)

        # ── Summary cards grid ─────────────────────────────────────────────
        grid = QGridLayout()
        grid.setSpacing(8)

        self._card_requests   = _SummaryCard("📨", "Total Requests",   Colors.ACCENT)
        self._card_tokens     = _SummaryCard("🧠", "Total Tokens",     Colors.TOKEN_COLOR)
        self._card_avg_tps    = _SummaryCard("⚡", "Avg TPS",          Colors.TPS_COLOR)
        self._card_avg_time   = _SummaryCard("⏱", "Avg Latency",      Colors.LATENCY_COLOR)
        self._card_peak_ram   = _SummaryCard("💾", "Peak RAM",         Colors.RAM_COLOR)
        self._card_peak_vram  = _SummaryCard("🎮", "Peak VRAM",        Colors.VRAM_COLOR)
        self._card_errors     = _SummaryCard("⚠", "Errors",           Colors.ERROR)
        self._card_uptime     = _SummaryCard("🕐", "Session Time",     Colors.TEXT_SECONDARY)

        cards = [
            self._card_requests, self._card_tokens,
            self._card_avg_tps,  self._card_avg_time,
            self._card_peak_ram, self._card_peak_vram,
            self._card_errors,   self._card_uptime,
        ]
        for i, card in enumerate(cards):
            grid.addWidget(card, i // 2, i % 2)

        layout.addLayout(grid)

        # ── Charts ─────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {Colors.BORDER};")
        layout.addWidget(sep)

        charts_lbl = QLabel("Charts")
        charts_lbl.setStyleSheet(
            f"color: {Colors.ACCENT}; font-size: 12px; font-weight: 700; background: transparent;"
        )
        layout.addWidget(charts_lbl)

        self._chart_tps  = _MiniChart("⚡ TPS per Request",       Colors.CHART_TPS,  "line")
        self._chart_time = _MiniChart("⏱ Response Time (s)",      Colors.CHART_TIME, "bar")

        layout.addWidget(self._chart_tps)
        layout.addWidget(self._chart_time)

        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    # ── Refresh ────────────────────────────────────────────────────────────

    def refresh(self):
        ss = self._ss

        self._card_requests.set_value(str(ss.total_requests))
        self._card_tokens.set_value(f"{ss.total_tokens:,}")

        avg_tps = ss.avg_tps
        self._card_avg_tps.set_value(f"{avg_tps:.1f}" if avg_tps > 0 else "—")

        avg_t = ss.avg_response_time
        self._card_avg_time.set_value(f"{avg_t:.2f}s" if avg_t > 0 else "—")

        self._card_peak_ram.set_value(
            f"{ss.peak_ram:.0f}%" if ss.peak_ram > 0 else "—"
        )
        self._card_peak_vram.set_value(
            f"{ss.peak_vram:.0f}%  ({ss.peak_vram_gb:.1f} GB)"
            if ss.peak_vram > 0 else "—"
        )
        self._card_errors.set_value(str(ss.failed_requests))

        # Session duration
        secs = int(ss.session_duration)
        h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
        self._card_uptime.set_value(f"{h:02d}:{m:02d}:{s:02d}")

        # Charts
        self._chart_tps.set_data(ss.tps_history())
        self._chart_time.set_data(ss.response_time_history())

    def _on_reset(self):
        self._ss.reset()
        self.refresh()
