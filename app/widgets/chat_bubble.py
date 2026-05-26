"""
ChatBubble — Individual chat message widget.
Supports user / assistant roles, inline images, streaming text,
a performance metrics bar, and a debug JSON panel.
"""

import json

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QColor
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QHBoxLayout, QSizePolicy, QWidget,
    QPushButton, QTextEdit,
)

from app.config import Colors


# ── Metric pill widget ────────────────────────────────────────────────────────

class _MetricPill(QLabel):
    """Compact coloured pill label for a single metric value."""

    def __init__(self, icon: str, value: str, color: str, parent=None):
        super().__init__(parent)
        self.setText(f"{icon} {value}")
        self.setStyleSheet(
            f"""
            QLabel {{
                color: {color};
                background-color: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
            }}
            """
        )
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


# ── ChatBubble ────────────────────────────────────────────────────────────────

class ChatBubble(QFrame):
    """A single chat message bubble (user or assistant)."""

    def __init__(
        self,
        role: str,
        text: str = "",
        image_path: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._role      = role
        self._full_text = text
        self._debug_visible = False
        self._metrics_bar: QFrame | None = None
        self._debug_panel: QFrame | None = None
        self._bubble_layout: QVBoxLayout | None = None  # reference for adding children

        is_user = role == "user"
        self.setObjectName("userBubble" if is_user else "assistantBubble")

        # ── Outer layout for alignment ─────────────────────────────────────
        outer = QHBoxLayout()
        outer.setContentsMargins(16, 4, 16, 4)

        if is_user:
            outer.addStretch()

        # ── Bubble frame ───────────────────────────────────────────────────
        bubble = QFrame()
        bubble.setObjectName("userBubble" if is_user else "assistantBubble")
        bubble.setMaximumWidth(640)
        bubble.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
        )

        self._bubble_layout = QVBoxLayout(bubble)
        self._bubble_layout.setContentsMargins(16, 12, 16, 12)
        self._bubble_layout.setSpacing(6)

        # ── Role label ─────────────────────────────────────────────────────
        role_label = QLabel("You" if is_user else "Assistant")
        role_label.setStyleSheet(
            f"color: {'#6C63FF' if not is_user else Colors.TEXT_SECONDARY}; "
            f"font-size: 11px; font-weight: 700; background: transparent;"
        )
        self._bubble_layout.addWidget(role_label)

        # ── Image thumbnail (user messages with media) ─────────────────────
        if image_path and is_user:
            img_label = QLabel()
            img_label.setStyleSheet("background: transparent;")
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaledToWidth(
                    300, Qt.TransformationMode.SmoothTransformation
                )
                img_label.setPixmap(pixmap)
                img_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                self._bubble_layout.addWidget(img_label)

        # ── Text content ───────────────────────────────────────────────────
        self._text_label = QLabel(text)
        self._text_label.setWordWrap(True)
        self._text_label.setTextFormat(Qt.TextFormat.PlainText)
        self._text_label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 14px; "
            f"line-height: 1.5; background: transparent;"
        )
        self._text_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
        )
        self._bubble_layout.addWidget(self._text_label)

        outer.addWidget(bubble)

        if not is_user:
            outer.addStretch()

        self.setLayout(outer)
        self.setStyleSheet("background: transparent; border: none;")
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

    # ── Streaming ──────────────────────────────────────────────────────────

    def append_token(self, token: str):
        """Append a token during streaming."""
        self._full_text += token
        self._text_label.setText(self._full_text)

    def set_text(self, text: str):
        """Replace the full text content."""
        self._full_text = text
        self._text_label.setText(text)

    # ── Metrics bar ────────────────────────────────────────────────────────

    def set_metrics_bar(self, metrics: dict, debug_mode: bool = False):
        """
        Append a compact performance bar below the message text.
        Call once after generation_complete. Safe to call multiple times
        (replaces the previous bar).
        """
        if self._role != "assistant" or self._bubble_layout is None:
            return

        # Remove previous bar if any
        if self._metrics_bar is not None:
            self._bubble_layout.removeWidget(self._metrics_bar)
            self._metrics_bar.deleteLater()
            self._metrics_bar = None

        # ── Build the bar ────────────────────────────────────────────────
        bar = QFrame()
        bar.setStyleSheet("background: transparent; border: none;")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(0, 4, 0, 0)
        bar_layout.setSpacing(6)

        tps         = metrics.get("tps", 0.0)
        total_time  = metrics.get("total_time", 0.0)
        ttft        = metrics.get("ttft", 0.0)
        out_tokens  = metrics.get("output_tokens", 0)
        in_tokens   = metrics.get("prompt_tokens", 0)
        load_dur    = metrics.get("load_duration", 0.0)
        is_warm     = metrics.get("is_warm", True)
        stop_reason = metrics.get("stop_reason", "")

        if tps > 0:
            bar_layout.addWidget(
                _MetricPill("⚡", f"{tps:.1f} tok/s", Colors.TPS_COLOR)
            )
        if total_time > 0:
            bar_layout.addWidget(
                _MetricPill("⏱", f"{total_time:.2f}s", Colors.LATENCY_COLOR)
            )
        if ttft > 0:
            bar_layout.addWidget(
                _MetricPill("🚀 TTFT", f"{ttft:.2f}s", Colors.TTFT_COLOR)
            )
        if out_tokens > 0 or in_tokens > 0:
            bar_layout.addWidget(
                _MetricPill("🧠", f"{out_tokens}↑ {in_tokens}↓ tok", Colors.TOKEN_COLOR)
            )
        if load_dur > 0:
            warm_label = "warm" if is_warm else "cold"
            bar_layout.addWidget(
                _MetricPill("📦", f"load {load_dur:.2f}s ({warm_label})", Colors.TEXT_SECONDARY)
            )
        if stop_reason:
            bar_layout.addWidget(
                _MetricPill("🏁", stop_reason, Colors.TEXT_MUTED)
            )

        bar_layout.addStretch()
        self._metrics_bar = bar
        self._bubble_layout.addWidget(bar)

        # ── Debug panel ──────────────────────────────────────────────────
        if debug_mode:
            self._add_debug_panel(metrics)

    # ── TTS metrics ────────────────────────────────────────────────────────

    def set_tts_metrics(self, tts_metrics: dict):
        """Append a TTS timing row below the metrics bar."""
        if self._bubble_layout is None:
            return

        tts_bar = QFrame()
        tts_bar.setStyleSheet("background: transparent; border: none;")
        row = QHBoxLayout(tts_bar)
        row.setContentsMargins(0, 2, 0, 0)
        row.setSpacing(6)

        gen_t    = tts_metrics.get("gen_time", 0.0)
        play_t   = tts_metrics.get("playback_est", 0.0)
        voice    = tts_metrics.get("voice", "default")

        row.addWidget(_MetricPill("🔊", f"TTS {gen_t:.1f}s gen", Colors.TTFT_COLOR))
        row.addWidget(_MetricPill("▶", f"~{play_t:.0f}s audio", Colors.TPS_COLOR))
        if voice and voice != "default":
            row.addWidget(_MetricPill("🎙", voice[:20], Colors.TEXT_SECONDARY))
        row.addStretch()
        self._bubble_layout.addWidget(tts_bar)

    # ── Debug panel ────────────────────────────────────────────────────────

    def _add_debug_panel(self, metrics: dict):
        """Add a collapsible JSON debug panel."""
        if self._debug_panel is not None:
            self._bubble_layout.removeWidget(self._debug_panel)
            self._debug_panel.deleteLater()

        container = QFrame()
        container.setStyleSheet(
            f"QFrame {{ background: {Colors.BG_DARKEST}; "
            f"border: 1px solid {Colors.BORDER}; border-radius: 6px; }}"
        )
        v = QVBoxLayout(container)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(4)

        # Toggle button
        toggle_btn = QPushButton("🐞 Debug — Raw Response  ▼")
        toggle_btn.setCheckable(True)
        toggle_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; "
            f"color: {Colors.ACCENT}; font-size: 11px; font-weight: 600; "
            f"text-align: left; padding: 0; }}"
            f"QPushButton:checked {{ color: {Colors.ACCENT_LIGHT}; }}"
        )

        json_view = QTextEdit()
        json_view.setReadOnly(True)
        json_view.setVisible(False)
        json_view.setMaximumHeight(200)
        json_view.setStyleSheet(
            f"QTextEdit {{ background: {Colors.BG_DARKEST}; color: {Colors.TTFT_COLOR}; "
            f"font-family: 'Consolas', monospace; font-size: 10px; border: none; }}"
        )

        raw = metrics.get("raw_response", {})
        # Build a clean display dict
        display = {k: v for k, v in metrics.items() if k != "raw_response"}
        display["raw_response"] = raw
        try:
            json_text = json.dumps(display, indent=2, default=str)
        except Exception:
            json_text = str(display)
        json_view.setPlainText(json_text)

        def _toggle(checked: bool):
            json_view.setVisible(checked)
            toggle_btn.setText(
                "🐞 Debug — Raw Response  ▲" if checked else "🐞 Debug — Raw Response  ▼"
            )

        toggle_btn.toggled.connect(_toggle)

        v.addWidget(toggle_btn)
        v.addWidget(json_view)
        self._debug_panel = container
        self._bubble_layout.addWidget(container)

    # ── Properties ─────────────────────────────────────────────────────────

    @property
    def text(self) -> str:
        return self._full_text

    @property
    def role(self) -> str:
        return self._role
