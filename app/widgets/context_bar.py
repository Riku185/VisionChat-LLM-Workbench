"""
ContextBar — Animated context-window usage bar for the top model selector bar.

Shows used tokens vs max context as a gradient progress bar with percentage
and absolute token counts. Updated by ChatPanel after each generation.
"""

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget,
)

from app.config import Colors, CONTEXT_BAR_HEIGHT


class ContextBar(QWidget):
    """
    Compact context-window usage indicator.

    Call update_context(used_tokens, max_tokens) to refresh.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._used  = 0
        self._max   = 2048
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Label: "Context"
        ctx_lbl = QLabel("Context")
        ctx_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; "
            f"font-weight: 600; background: transparent;"
        )
        layout.addWidget(ctx_lbl)

        # Progress bar
        self._bar = QProgressBar()
        self._bar.setRange(0, 1000)     # use 0-1000 for sub-1% precision
        self._bar.setValue(0)
        self._bar.setFixedHeight(CONTEXT_BAR_HEIGHT)
        self._bar.setMinimumWidth(120)
        self._bar.setMaximumWidth(200)
        self._bar.setTextVisible(False)
        self._bar.setStyleSheet(self._bar_style(0))
        layout.addWidget(self._bar)

        # Percent label
        self._pct_lbl = QLabel("0%")
        self._pct_lbl.setStyleSheet(
            f"color: {Colors.TPS_COLOR}; font-size: 11px; "
            f"font-weight: 700; background: transparent; min-width: 36px;"
        )
        layout.addWidget(self._pct_lbl)

        # Token count label
        self._count_lbl = QLabel("(0 / 2048)")
        self._count_lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 10px; background: transparent;"
        )
        layout.addWidget(self._count_lbl)

    @staticmethod
    def _bar_style(pct: float) -> str:
        """Generate a gradient bar style that changes colour near capacity."""
        if pct < 60:
            bar_color  = Colors.TPS_COLOR
            chunk_grad = f"qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {Colors.ACCENT}, stop:1 {Colors.TPS_COLOR})"
        elif pct < 85:
            bar_color  = Colors.WARNING
            chunk_grad = f"qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {Colors.ACCENT}, stop:1 {Colors.WARNING})"
        else:
            bar_color  = Colors.ERROR
            chunk_grad = f"qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {Colors.WARNING}, stop:1 {Colors.ERROR})"

        return f"""
            QProgressBar {{
                background-color: {Colors.BG_INPUT};
                border: 1px solid {Colors.BORDER};
                border-radius: 7px;
            }}
            QProgressBar::chunk {{
                background: {chunk_grad};
                border-radius: 7px;
            }}
        """

    # ── Public API ────────────────────────────────────────────────────────────

    def update_context(self, used_tokens: int, max_tokens: int):
        """Refresh the bar with the latest token usage."""
        self._used = max(0, used_tokens)
        self._max  = max(1, max_tokens)

        pct      = min(100.0, (self._used / self._max) * 100.0)
        bar_val  = int(pct * 10)   # 0–1000

        self._bar.setValue(bar_val)
        self._bar.setStyleSheet(self._bar_style(pct))
        self._pct_lbl.setText(f"{pct:.0f}%")
        self._count_lbl.setText(f"({self._used:,} / {self._max:,})")

    def reset(self):
        self.update_context(0, self._max)

    def set_max(self, max_tokens: int):
        self._max = max(1, max_tokens)
        self.update_context(self._used, self._max)
