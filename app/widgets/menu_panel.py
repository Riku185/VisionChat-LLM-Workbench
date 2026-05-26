"""
MenuPanel — Right-side narrow icon strip that expands into either the
Model Configuration flyout or the Analytics Dashboard, with Debug Mode
and Overlay toggles.
"""

from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QPushButton, QWidget, QSizePolicy,
    QLabel, QHBoxLayout, QScrollArea, QSpinBox, QDoubleSpinBox,
    QStackedWidget,
)

from app.config import Colors, DEFAULT_MENU_WIDTH, MENU_EXPANDED_WIDTH
from app.widgets.analytics_panel import AnalyticsPanel


# ── Default Ollama options ─────────────────────────────────────────────────────
DEFAULT_OPTIONS = {
    "num_ctx":        2048,
    "num_gpu":        -1,       # -1 = auto (offload all layers)
    "temperature":    0.7,
    "top_p":          0.9,
    "top_k":          40,
    "repeat_penalty": 1.1,
    "num_predict":    -1,       # -1 = unlimited
    "seed":           -1,       # -1 = random
    "mirostat":       0,        # 0=off, 1=v1, 2=v2
    "mirostat_tau":   5.0,
    "mirostat_eta":   0.1,
    "num_thread":     0,        # 0 = auto
    "num_batch":      512,
}

# Page indices in the stacked widget
_PAGE_SETTINGS   = 0
_PAGE_ANALYTICS  = 1


class MenuPanel(QFrame):
    """Narrow icon strip on the right with expandable settings / analytics flyout."""

    terminal_requested    = pyqtSignal()
    export_requested      = pyqtSignal()
    import_requested      = pyqtSignal()
    load_model_requested  = pyqtSignal()
    stop_model_requested  = pyqtSignal()
    debug_toggled         = pyqtSignal(bool)    # True = debug enabled
    overlay_toggled       = pyqtSignal(bool)    # True = overlay visible

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("menuPanel")
        self.setFixedWidth(DEFAULT_MENU_WIDTH)
        self._expanded      = False
        self._debug_on      = False
        self._overlay_on    = False
        self._active_page   = _PAGE_SETTINGS

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Icon strip (always visible, DEFAULT_MENU_WIDTH px) ────────────
        self._icon_strip = QFrame()
        self._icon_strip.setFixedWidth(DEFAULT_MENU_WIDTH)
        icon_layout = QVBoxLayout(self._icon_strip)
        icon_layout.setContentsMargins(4, 12, 4, 12)
        icon_layout.setSpacing(4)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Settings toggle
        self._toggle_btn = self._make_icon_btn("☰", "Settings & Menu")
        self._toggle_btn.clicked.connect(lambda: self._open_page(_PAGE_SETTINGS))
        icon_layout.addWidget(self._toggle_btn)
        icon_layout.addSpacing(8)

        # Analytics
        self._analytics_btn = self._make_icon_btn("📊", "Session Analytics")
        self._analytics_btn.clicked.connect(lambda: self._open_page(_PAGE_ANALYTICS))
        icon_layout.addWidget(self._analytics_btn)

        icon_layout.addSpacing(8)

        # Chat actions
        self._terminal_btn = self._make_icon_btn("⌨", "Terminal")
        self._terminal_btn.clicked.connect(self.terminal_requested.emit)
        icon_layout.addWidget(self._terminal_btn)

        self._export_btn = self._make_icon_btn("📤", "Export Chat")
        self._export_btn.clicked.connect(self.export_requested.emit)
        icon_layout.addWidget(self._export_btn)

        self._import_btn = self._make_icon_btn("📥", "Import Chat")
        self._import_btn.clicked.connect(self.import_requested.emit)
        icon_layout.addWidget(self._import_btn)

        self._stop_btn = self._make_icon_btn("⏹", "Stop Model")
        self._stop_btn.clicked.connect(self.stop_model_requested.emit)
        icon_layout.addWidget(self._stop_btn)

        icon_layout.addSpacing(8)

        # Debug mode toggle
        self._debug_btn = self._make_icon_btn("🐞", "Toggle Debug Mode")
        self._debug_btn.setCheckable(True)
        self._debug_btn.toggled.connect(self._on_debug_toggle)
        icon_layout.addWidget(self._debug_btn)

        # Performance overlay toggle
        self._overlay_btn = self._make_icon_btn("🖥", "Toggle Performance Overlay")
        self._overlay_btn.setCheckable(True)
        self._overlay_btn.toggled.connect(self._on_overlay_toggle)
        icon_layout.addWidget(self._overlay_btn)

        icon_layout.addStretch()

        # ── Stacked flyout (settings | analytics) ─────────────────────────
        self._stack = QStackedWidget()
        self._stack.setVisible(False)

        self._settings_widget = self._build_settings_panel()
        self._analytics_widget = AnalyticsPanel()

        self._stack.addWidget(self._settings_widget)   # index 0
        self._stack.addWidget(self._analytics_widget)  # index 1

        # ── Horizontal wrapper ─────────────────────────────────────────────
        h_wrapper = QHBoxLayout()
        h_wrapper.setContentsMargins(0, 0, 0, 0)
        h_wrapper.setSpacing(0)
        h_wrapper.addWidget(self._stack, 1)
        h_wrapper.addWidget(self._icon_strip, 0)

        layout.addLayout(h_wrapper)

    # ══════════════════════════════════════════════════════════════════════
    #  Settings Panel Construction
    # ══════════════════════════════════════════════════════════════════════

    def _build_settings_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("menuFlyout")
        panel.setStyleSheet(
            f"QFrame#menuFlyout {{ background-color: {Colors.BG_PANEL}; "
            f"border-left: 1px solid {Colors.BORDER}; }}"
        )

        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        form = QVBoxLayout(content)
        form.setContentsMargins(14, 14, 14, 14)
        form.setSpacing(6)

        title = QLabel("⚙  Model Configuration")
        title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 14px; "
            f"font-weight: 700; background: transparent;"
        )
        form.addWidget(title)

        hint = QLabel(
            "Adjust parameters, then click Load Model.\n"
            "Leave defaults to use the model's built-in config."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 11px; "
            f"background: transparent; margin-bottom: 4px;"
        )
        form.addWidget(hint)

        self._add_separator(form)

        # Context Length
        self._num_ctx = self._add_int_field(
            form, "Context Length (num_ctx)",
            "Max tokens the model can process at once.",
            DEFAULT_OPTIONS["num_ctx"], 512, 131072, 512,
        )

        # GPU Layers
        self._num_gpu = self._add_int_field(
            form, "GPU Layers (num_gpu)",
            "-1 = offload all layers to GPU.",
            DEFAULT_OPTIONS["num_gpu"], -1, 999, 1,
        )

        # CPU Threads
        self._num_thread = self._add_int_field(
            form, "CPU Threads (num_thread)",
            "0 = auto-detect.",
            DEFAULT_OPTIONS["num_thread"], 0, 128, 1,
        )

        # Batch Size
        self._num_batch = self._add_int_field(
            form, "Batch Size (num_batch)",
            "Number of tokens to process in parallel.",
            DEFAULT_OPTIONS["num_batch"], 1, 4096, 64,
        )

        self._add_separator(form)
        self._add_section_label(form, "Generation")

        self._temperature = self._add_float_field(
            form, "Temperature",
            "Higher = more creative. Lower = more focused.",
            DEFAULT_OPTIONS["temperature"], 0.0, 2.0, 0.05,
        )
        self._top_p = self._add_float_field(
            form, "Top P (nucleus sampling)",
            "Cumulative probability cutoff.",
            DEFAULT_OPTIONS["top_p"], 0.0, 1.0, 0.05,
        )
        self._top_k = self._add_int_field(
            form, "Top K",
            "Number of top tokens to consider.",
            DEFAULT_OPTIONS["top_k"], 0, 500, 5,
        )
        self._repeat_penalty = self._add_float_field(
            form, "Repeat Penalty",
            "Penalise repeated tokens. 1.0 = no penalty.",
            DEFAULT_OPTIONS["repeat_penalty"], 0.0, 3.0, 0.05,
        )
        self._num_predict = self._add_int_field(
            form, "Max Tokens (num_predict)",
            "-1 = unlimited generation.",
            DEFAULT_OPTIONS["num_predict"], -1, 32768, 64,
        )
        self._seed = self._add_int_field(
            form, "Seed",
            "-1 = random seed each time.",
            DEFAULT_OPTIONS["seed"], -1, 999999999, 1,
        )

        self._add_separator(form)
        self._add_section_label(form, "Mirostat")

        self._mirostat = self._add_int_field(
            form, "Mirostat Mode",
            "0 = off, 1 = Mirostat, 2 = Mirostat 2.0.",
            DEFAULT_OPTIONS["mirostat"], 0, 2, 1,
        )
        self._mirostat_tau = self._add_float_field(
            form, "Mirostat Tau",
            "Target entropy (perplexity).",
            DEFAULT_OPTIONS["mirostat_tau"], 0.0, 20.0, 0.1,
        )
        self._mirostat_eta = self._add_float_field(
            form, "Mirostat Eta",
            "Learning rate for Mirostat.",
            DEFAULT_OPTIONS["mirostat_eta"], 0.0, 1.0, 0.01,
        )

        self._add_separator(form)

        reset_btn = QPushButton("↺  Reset to Defaults")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet(self._action_btn_style(Colors.TEXT_SECONDARY, Colors.BORDER))
        reset_btn.clicked.connect(self._reset_defaults)
        form.addWidget(reset_btn)

        form.addSpacing(8)

        self._load_btn = QPushButton("▶  Load Model")
        self._load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._load_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {Colors.ACCENT};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {Colors.ACCENT_LIGHT};
            }}
            QPushButton:pressed {{
                background-color: {Colors.ACCENT_DIM};
            }}
            """
        )
        self._load_btn.clicked.connect(self.load_model_requested.emit)
        form.addWidget(self._load_btn)

        form.addSpacing(12)
        form.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        return panel

    # ══════════════════════════════════════════════════════════════════════
    #  Expand / page switching
    # ══════════════════════════════════════════════════════════════════════

    def _open_page(self, page_idx: int):
        """Open the flyout to the specified page, or collapse if already open on that page."""
        if self._expanded and self._active_page == page_idx:
            self._collapse()
            return

        self._active_page = page_idx
        self._stack.setCurrentIndex(page_idx)

        if self._expanded:
            # Already open — just switch page
            if page_idx == _PAGE_ANALYTICS:
                self._analytics_widget.refresh()
            return

        # Expand
        self._expanded = True
        self._stack.setVisible(True)
        if page_idx == _PAGE_ANALYTICS:
            self._analytics_widget.refresh()
        self._animate(MENU_EXPANDED_WIDTH)

    def _collapse(self):
        self._expanded = False
        anim_done = self._animate(DEFAULT_MENU_WIDTH)
        anim_done.finished.connect(lambda: self._stack.setVisible(False))

    def _animate(self, target_w: int):
        anim = QPropertyAnimation(self, b"maximumWidth")
        anim.setDuration(280)
        anim.setStartValue(self.width())
        anim.setEndValue(target_w)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        anim2 = QPropertyAnimation(self, b"minimumWidth")
        anim2.setDuration(280)
        anim2.setStartValue(self.width())
        anim2.setEndValue(target_w)
        anim2.setEasingCurve(QEasingCurve.Type.InOutCubic)

        anim.start()
        anim2.start()
        self._anim  = anim
        self._anim2 = anim2
        return anim

    # ══════════════════════════════════════════════════════════════════════
    #  Toggle handlers
    # ══════════════════════════════════════════════════════════════════════

    def _on_debug_toggle(self, checked: bool):
        self._debug_on = checked
        color = Colors.ACCENT if checked else Colors.TEXT_SECONDARY
        self._debug_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {"rgba(108,99,255,0.15)" if checked else "transparent"};
                border: {"1px solid " + Colors.ACCENT if checked else "none"};
                border-radius: 10px;
                font-size: 20px;
                color: {color};
            }}
            QPushButton:hover {{ background-color: {Colors.BG_CARD}; color: {Colors.TEXT_PRIMARY}; }}
            """
        )
        self.debug_toggled.emit(checked)

    def _on_overlay_toggle(self, checked: bool):
        self._overlay_on = checked
        color = Colors.TPS_COLOR if checked else Colors.TEXT_SECONDARY
        self._overlay_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {"rgba(0,229,255,0.1)" if checked else "transparent"};
                border: {"1px solid " + Colors.TPS_COLOR if checked else "none"};
                border-radius: 10px;
                font-size: 20px;
                color: {color};
            }}
            QPushButton:hover {{ background-color: {Colors.BG_CARD}; color: {Colors.TEXT_PRIMARY}; }}
            """
        )
        self.overlay_toggled.emit(checked)

    # ══════════════════════════════════════════════════════════════════════
    #  Field helpers
    # ══════════════════════════════════════════════════════════════════════

    def _add_int_field(
        self, layout, label, hint, default, min_val, max_val, step,
    ) -> QSpinBox:
        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 12px; "
            f"font-weight: 600; background: transparent; margin-top: 4px;"
        )
        layout.addWidget(lbl)
        h = QLabel(hint)
        h.setWordWrap(True)
        h.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px; background: transparent;")
        layout.addWidget(h)
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setSingleStep(step)
        spin.setStyleSheet(self._spin_style())
        layout.addWidget(spin)
        return spin

    def _add_float_field(
        self, layout, label, hint, default, min_val, max_val, step,
    ) -> QDoubleSpinBox:
        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 12px; "
            f"font-weight: 600; background: transparent; margin-top: 4px;"
        )
        layout.addWidget(lbl)
        h = QLabel(hint)
        h.setWordWrap(True)
        h.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px; background: transparent;")
        layout.addWidget(h)
        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setSingleStep(step)
        spin.setDecimals(2)
        spin.setStyleSheet(self._spin_style())
        layout.addWidget(spin)
        return spin

    def _add_separator(self, layout):
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {Colors.BORDER};")
        layout.addSpacing(6)
        layout.addWidget(sep)
        layout.addSpacing(6)

    def _add_section_label(self, layout, text: str):
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {Colors.ACCENT}; font-size: 12px; "
            f"font-weight: 700; background: transparent;"
        )
        layout.addWidget(lbl)

    @staticmethod
    def _spin_style() -> str:
        return (
            f"QSpinBox, QDoubleSpinBox {{"
            f"  background-color: {Colors.BG_INPUT};"
            f"  color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER};"
            f"  border-radius: 6px;"
            f"  padding: 5px 8px;"
            f"  font-size: 13px;"
            f"}}"
            f"QSpinBox:focus, QDoubleSpinBox:focus {{"
            f"  border-color: {Colors.ACCENT};"
            f"}}"
            f"QSpinBox::up-button, QDoubleSpinBox::up-button,"
            f"QSpinBox::down-button, QDoubleSpinBox::down-button {{"
            f"  width: 16px; background: {Colors.BG_CARD}; border: none;"
            f"}}"
        )

    @staticmethod
    def _action_btn_style(color: str, border_color: str) -> str:
        return (
            f"QPushButton {{"
            f"  background-color: transparent;"
            f"  color: {color};"
            f"  border: 1px solid {border_color};"
            f"  border-radius: 8px;"
            f"  padding: 8px;"
            f"  font-size: 12px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: {Colors.BG_CARD};"
            f"  color: {Colors.TEXT_PRIMARY};"
            f"}}"
        )

    def _make_icon_btn(self, icon: str, tooltip: str) -> QPushButton:
        btn = QPushButton(icon)
        btn.setObjectName("menuButton")
        btn.setToolTip(tooltip)
        btn.setFixedSize(44, 44)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 10px;
                font-size: 20px;
                color: {Colors.TEXT_SECONDARY};
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_CARD};
                color: {Colors.TEXT_PRIMARY};
            }}
            """
        )
        return btn

    # ══════════════════════════════════════════════════════════════════════
    #  Public API
    # ══════════════════════════════════════════════════════════════════════

    def get_model_options(self) -> dict:
        """Return the current Ollama model options from the UI fields."""
        opts = {}
        checks = [
            ("num_ctx",        self._num_ctx),
            ("num_gpu",        self._num_gpu),
            ("num_thread",     self._num_thread),
            ("num_batch",      self._num_batch),
            ("temperature",    self._temperature),
            ("top_p",          self._top_p),
            ("top_k",          self._top_k),
            ("repeat_penalty", self._repeat_penalty),
            ("num_predict",    self._num_predict),
            ("seed",           self._seed),
            ("mirostat",       self._mirostat),
            ("mirostat_tau",   self._mirostat_tau),
            ("mirostat_eta",   self._mirostat_eta),
        ]
        for key, widget in checks:
            if widget.value() != DEFAULT_OPTIONS[key]:
                opts[key] = widget.value()
        return opts

    def get_num_ctx(self) -> int:
        """Return the current context length setting."""
        return self._num_ctx.value()

    def is_debug_on(self) -> bool:
        return self._debug_on

    def _reset_defaults(self):
        self._num_ctx.setValue(DEFAULT_OPTIONS["num_ctx"])
        self._num_gpu.setValue(DEFAULT_OPTIONS["num_gpu"])
        self._num_thread.setValue(DEFAULT_OPTIONS["num_thread"])
        self._num_batch.setValue(DEFAULT_OPTIONS["num_batch"])
        self._temperature.setValue(DEFAULT_OPTIONS["temperature"])
        self._top_p.setValue(DEFAULT_OPTIONS["top_p"])
        self._top_k.setValue(DEFAULT_OPTIONS["top_k"])
        self._repeat_penalty.setValue(DEFAULT_OPTIONS["repeat_penalty"])
        self._num_predict.setValue(DEFAULT_OPTIONS["num_predict"])
        self._seed.setValue(DEFAULT_OPTIONS["seed"])
        self._mirostat.setValue(DEFAULT_OPTIONS["mirostat"])
        self._mirostat_tau.setValue(DEFAULT_OPTIONS["mirostat_tau"])
        self._mirostat_eta.setValue(DEFAULT_OPTIONS["mirostat_eta"])
