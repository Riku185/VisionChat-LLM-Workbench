"""
StatsPanel — Left sidebar showing real-time CPU / GPU / RAM / VRAM graphs
with gradient fills, live value overlays, a TPS gauge, model state badge,
and absolute VRAM GB display.
"""

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QWidget, QHBoxLayout,
    QProgressBar, QSizePolicy,
)

from app.config import Colors, STATS_BUFFER_SIZE, TPS_GAUGE_MAX
from app.workers.stats_worker import StatsWorker


# ── _MiniGraph ────────────────────────────────────────────────────────────────

class _MiniGraph(QWidget):
    """A single stat graph with title, live value, and gradient fill."""

    def __init__(self, title: str, color_hex: str, parent=None):
        super().__init__(parent)
        self._color_hex = color_hex
        self._data = np.zeros(STATS_BUFFER_SIZE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 0)
        layout.setSpacing(2)

        # ── Header row: title + value ──────────────────────────────────────
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; "
            f"font-weight: 600; letter-spacing: 0.5px;"
        )
        header.addWidget(title_lbl)

        self._value_lbl = QLabel("0 %")
        self._value_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._value_lbl.setStyleSheet(
            f"color: {color_hex}; font-size: 20px; font-weight: 700;"
        )
        header.addWidget(self._value_lbl)
        layout.addLayout(header)

        # ── Plot widget ────────────────────────────────────────────────────
        self._plot = pg.PlotWidget()
        self._plot.setBackground("#141414")
        self._plot.setFixedHeight(80)
        self._plot.hideAxis("bottom")
        self._plot.hideAxis("left")
        self._plot.setYRange(0, 100, padding=0.05)
        self._plot.setMouseEnabled(x=False, y=False)
        self._plot.hideButtons()
        self._plot.setMenuEnabled(False)

        pen = pg.mkPen(color=color_hex, width=2)
        self._curve = self._plot.plot(self._data, pen=pen)

        color = QColor(color_hex)
        color.setAlpha(50)
        self._fill = pg.FillBetweenItem(
            self._curve,
            self._plot.plot(np.zeros(STATS_BUFFER_SIZE), pen=pg.mkPen(None)),
            brush=pg.mkBrush(color),
        )
        self._plot.addItem(self._fill)
        layout.addWidget(self._plot)

    def update_value(self, value: float, suffix: str = "%", max_val: float = 100.0):
        self._data = np.roll(self._data, -1)
        self._data[-1] = max(0.0, min(max_val, value))
        self._curve.setData(self._data)
        self._plot.setYRange(0, max_val, padding=0.05)
        if value < 0:
            self._value_lbl.setText("N/A")
        else:
            self._value_lbl.setText(f"{value:.0f} {suffix}")


# ── _TpsGauge ─────────────────────────────────────────────────────────────────

class _TpsGauge(QWidget):
    """Compact live TPS (tokens/sec) gauge with horizontal bar + numeric label."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel("⚡ Live TPS")
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; "
            f"font-weight: 600; background: transparent;"
        )
        header.addWidget(lbl)

        self._val_lbl = QLabel("—")
        self._val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._val_lbl.setStyleSheet(
            f"color: {Colors.TPS_COLOR}; font-size: 18px; font-weight: 700; background: transparent;"
        )
        header.addWidget(self._val_lbl)
        layout.addLayout(header)

        # Progress bar
        self._bar = QProgressBar()
        self._bar.setRange(0, int(TPS_GAUGE_MAX))
        self._bar.setValue(0)
        self._bar.setFixedHeight(10)
        self._bar.setTextVisible(False)
        self._bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {Colors.BG_INPUT};
                border: none;
                border-radius: 5px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {Colors.ACCENT}, stop:1 {Colors.TPS_COLOR});
                border-radius: 5px;
            }}
        """)
        layout.addWidget(self._bar)

    def update_tps(self, tps: float):
        self._val_lbl.setText(f"{tps:.1f}")
        self._bar.setValue(int(min(tps, TPS_GAUGE_MAX)))

    def reset(self):
        self._val_lbl.setText("—")
        self._bar.setValue(0)


# ── _ModelStateBadge ──────────────────────────────────────────────────────────

class _ModelStateBadge(QWidget):
    """Coloured pill showing the current model state."""

    _STATE_STYLES = {
        "Idle":    (Colors.STATE_IDLE,    "⬡"),
        "Loading": (Colors.STATE_LOADING, "⟳"),
        "Running": (Colors.STATE_RUNNING, "▶"),
        "Error":   (Colors.STATE_ERROR,   "✕"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        lbl = QLabel("Model State")
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; "
            f"font-weight: 600; background: transparent;"
        )
        layout.addWidget(lbl)
        layout.addStretch()

        self._badge = QLabel("⬡  Idle")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setStyleSheet(self._make_style(Colors.STATE_IDLE))
        layout.addWidget(self._badge)

    @staticmethod
    def _make_style(color: str) -> str:
        return (
            f"color: {color}; background: rgba(255,255,255,0.05); "
            f"border: 1px solid {color}; border-radius: 10px; "
            f"padding: 2px 10px; font-size: 11px; font-weight: 700;"
        )

    def set_state(self, state: str):
        color, icon = self._STATE_STYLES.get(state, (Colors.STATE_IDLE, "⬡"))
        self._badge.setText(f"{icon}  {state}")
        self._badge.setStyleSheet(self._make_style(color))


# ── _GpuSensorWidget ────────────────────────────────────────────────────────────

class _GpuSensorWidget(QWidget):
    """Shows GPU temperature and power consumption."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 4)
        layout.setSpacing(4)

        lbl = QLabel("Sensors:")
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 10px; background: transparent;"
        )
        layout.addWidget(lbl)

        self._val_lbl = QLabel("— °C  /  — W")
        self._val_lbl.setStyleSheet(
            f"color: {Colors.GPU_COLOR}; font-size: 11px; "
            f"font-weight: 700; background: transparent;"
        )
        layout.addWidget(self._val_lbl)
        layout.addStretch()

    def update_sensors(self, temp_c: float, power_w: float):
        if temp_c <= 0 and power_w <= 0:
            self._val_lbl.setText("N/A")
        else:
            self._val_lbl.setText(f"{temp_c:.0f} °C  /  {power_w:.1f} W")


# ── _VramAbsWidget ────────────────────────────────────────────────────────────

class _VramAbsWidget(QWidget):
    """Shows absolute VRAM usage in MB alongside the graph."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 4)
        layout.setSpacing(4)

        lbl = QLabel("VRAM used:")
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 10px; background: transparent;"
        )
        layout.addWidget(lbl)

        self._val_lbl = QLabel("— MB / — MB")
        self._val_lbl.setStyleSheet(
            f"color: {Colors.VRAM_COLOR}; font-size: 11px; "
            f"font-weight: 700; background: transparent;"
        )
        layout.addWidget(self._val_lbl)
        layout.addStretch()

    def update_vram(self, used_mb: float, total_mb: float):
        if total_mb <= 0:
            self._val_lbl.setText("N/A")
        else:
            self._val_lbl.setText(f"{used_mb:.0f} MB / {total_mb:.0f} MB")


# ── StatsPanel ────────────────────────────────────────────────────────────────

class StatsPanel(QFrame):
    """Left sidebar with system graphs, TPS gauge, model state, and VRAM GB."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statsPanel")
        self.setMinimumWidth(220)
        self.setMaximumWidth(340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(6)

        # ── Panel title ────────────────────────────────────────────────────
        title = QLabel("System Monitor")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {Colors.BORDER};")
        layout.addWidget(sep)
        layout.addSpacing(2)

        # ── Hardware graphs ────────────────────────────────────────────────
        self._cpu_graph  = _MiniGraph("CPU",  Colors.CPU_COLOR)
        self._gpu_graph  = _MiniGraph("GPU",  Colors.GPU_COLOR)
        self._ram_graph  = _MiniGraph("RAM",  Colors.RAM_COLOR)
        self._vram_graph = _MiniGraph("VRAM", Colors.VRAM_COLOR)

        layout.addWidget(self._cpu_graph)
        layout.addWidget(self._gpu_graph)
        self._gpu_sensors = _GpuSensorWidget()
        layout.addWidget(self._gpu_sensors)
        layout.addWidget(self._ram_graph)
        layout.addWidget(self._vram_graph)

        # Absolute VRAM label (below VRAM graph)
        self._vram_abs = _VramAbsWidget()
        layout.addWidget(self._vram_abs)

        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet(f"background-color: {Colors.BORDER};")
        layout.addWidget(sep2)

        # ── TPS gauge ─────────────────────────────────────────────────────
        self._tps_gauge = _TpsGauge()
        layout.addWidget(self._tps_gauge)

        sep3 = QFrame()
        sep3.setFixedHeight(1)
        sep3.setStyleSheet(f"background-color: {Colors.BORDER};")
        layout.addWidget(sep3)

        # ── Model state badge ──────────────────────────────────────────────
        self._state_badge = _ModelStateBadge()
        layout.addWidget(self._state_badge)

        # ── Footer ─────────────────────────────────────────────────────────
        layout.addStretch()
        footer = QLabel("Vision Chat")
        footer.setObjectName("secondaryLabel")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

        # ── Worker ─────────────────────────────────────────────────────────
        self._worker = StatsWorker(self)
        self._worker.stats_updated.connect(self._on_stats)
        self._worker.start()

    # ── Slots ──────────────────────────────────────────────────────────────

    def _on_stats(
        self,
        cpu: float, gpu: float, ram_mb: float,
        vram_mb: float, vram_total_mb: float, ram_total_mb: float,
        temp_c: float, power_w: float,
    ):
        self._cpu_graph.update_value(cpu, suffix="%")
        self._gpu_graph.update_value(gpu, suffix="%")
        self._gpu_sensors.update_sensors(temp_c, power_w)
        self._ram_graph.update_value(ram_mb, suffix="MB", max_val=ram_total_mb)
        self._vram_graph.update_value(vram_mb, suffix="MB", max_val=vram_total_mb)
        self._vram_abs.update_vram(vram_mb, vram_total_mb)

        # Forward to session stats (peak tracking)
        from app.models.session_stats import SessionStats
        ss = SessionStats()
        ss.update_peak_ram(ram_mb)
        ss.update_peak_vram(vram_mb, vram_mb / 1024.0)

    def update_tps(self, tps: float):
        """Called by ChatPanel with live speed estimate."""
        self._tps_gauge.update_tps(tps)

    def reset_tps(self):
        self._tps_gauge.reset()

    def set_model_state(self, state: str):
        """Update the model state badge. state ∈ {Idle, Loading, Running, Error}."""
        self._state_badge.set_state(state)

    # ── Cleanup ────────────────────────────────────────────────────────────
    def stop(self):
        self._worker.stop()
