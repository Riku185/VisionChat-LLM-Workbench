"""
MainWindow — Top-level window assembling the three-panel layout:
  Left: StatsPanel  |  Center: ChatPanel  |  Right: MenuPanel
Handles model listing, loading, and stopping.
Wires all signals for the Performance Workbench (overlay, analytics, debug).
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter, QSizePolicy,
    QLabel, QVBoxLayout,
)

from app.config import (
    Colors, MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT,
    DEFAULT_STATS_WIDTH, APP_NAME,
)
from app.widgets.stats_panel import StatsPanel
from app.widgets.chat_panel import ChatPanel
from app.widgets.menu_panel import MenuPanel
from app.widgets.performance_overlay import PerformanceOverlay
from app.workers.ollama_worker import ModelListWorker, ModelLoadWorker, ModelStopWorker


class MainWindow(QMainWindow):
    """Primary application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.resize(1280, 800)

        self._loaded_model: str | None = None
        self._load_worker: ModelLoadWorker | None = None
        self._stop_worker: ModelStopWorker | None = None

        # ── Central widget ───────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Left panel — System Monitor ──────────────────
        self._stats_panel = StatsPanel()
        self._stats_panel.setFixedWidth(DEFAULT_STATS_WIDTH)

        # ── Center panel — Chat ──────────────────────────
        self._chat_panel = ChatPanel()
        self._chat_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding,
        )

        # ── Right panel — Menu ───────────────────────────
        self._menu_panel = MenuPanel()

        # ── Floating Overlay ─────────────────────────────
        self._overlay = PerformanceOverlay()

        # ── Wire signals ─────────────────────────────────
        self._menu_panel.terminal_requested.connect(self._chat_panel.toggle_terminal)
        self._menu_panel.export_requested.connect(self._chat_panel.export_session)
        self._menu_panel.import_requested.connect(self._chat_panel.import_session)
        self._menu_panel.load_model_requested.connect(self._on_load_model)
        self._menu_panel.stop_model_requested.connect(self._on_stop_model)

        # New workbench signals
        self._menu_panel.debug_toggled.connect(self._chat_panel.set_debug_mode)
        self._menu_panel.overlay_toggled.connect(self._toggle_overlay)

        # Wire model options: chat panel reads live from menu panel
        self._chat_panel.set_options_provider(self._menu_panel.get_model_options)

        # Wire live telemetry to stats panel and overlay
        self._chat_panel.speed_updated.connect(self._on_speed_updated)
        self._chat_panel.model_state_changed.connect(self._on_model_state_changed)
        self._stats_panel._worker.stats_updated.connect(self._on_sys_stats)

        # ── Splitter (left | center) ─────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.addWidget(self._stats_panel)
        splitter.addWidget(self._chat_panel)
        splitter.setStretchFactor(0, 0)  # stats: fixed
        splitter.setStretchFactor(1, 1)  # chat: stretch

        root_layout.addWidget(splitter, 1)
        root_layout.addWidget(self._menu_panel)

        # ── Status bar ───────────────────────────────────
        self._status_label = QLabel("")
        self._status_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; "
            f"padding: 4px 12px; background-color: {Colors.BG_DARK};"
        )
        self.statusBar().addWidget(self._status_label, 1)
        self.statusBar().setStyleSheet(
            f"QStatusBar {{ background-color: {Colors.BG_DARK}; "
            f"border-top: 1px solid {Colors.BORDER}; }}"
        )

        # ── Fetch available models on startup ────────────
        self._status_label.setText("⏳  Fetching available models…")
        self._list_worker = ModelListWorker()
        self._list_worker.models_loaded.connect(self._on_models_loaded)
        self._list_worker.error_occurred.connect(self._on_list_error)
        self._list_worker.start()

    # ══════════════════════════════════════════════════════
    #  Signal Routing
    # ══════════════════════════════════════════════════════

    def _on_speed_updated(self, tps: float):
        self._stats_panel.update_tps(tps)
        self._overlay.update_tps(tps)

    def _on_model_state_changed(self, state: str):
        self._stats_panel.set_model_state(state)
        self._overlay.update_state(state)
        if state == "Idle":
            self._stats_panel.reset_tps()

    def _on_sys_stats(self, cpu: float, gpu: float, ram: float, vram: float, vram_gb: float, total_gb: float, temp_c: float, power_w: float):
        self._overlay.update_vram(vram_gb, total_gb)

    def _toggle_overlay(self, checked: bool):
        if checked:
            self._overlay.update_model(self._loaded_model or self._chat_panel.get_selected_model())
            self._overlay.show()
        else:
            self._overlay.hide()

    # ══════════════════════════════════════════════════════
    #  Model list callbacks
    # ══════════════════════════════════════════════════════

    def _on_models_loaded(self, models: list[str], vision_models: list[str], model_info: dict):
        if models:
            self._chat_panel.set_models(models, vision_models)
            vision_count = len(vision_models)
            self._status_label.setText(
                f"✓  {len(models)} model(s) available ({vision_count} vision) "
                f"— select one and click ▶ Load Model"
            )
            # Update overlay with the initially selected model
            self._overlay.update_model(self._chat_panel.get_selected_model())
        else:
            self._status_label.setText("⚠  No models found. Pull a model with: ollama pull <model>")
            self._status_label.setStyleSheet(
                f"color: {Colors.WARNING}; font-size: 12px; "
                f"padding: 4px 12px; background-color: {Colors.BG_DARK};"
            )
        self._list_worker = None

    def _on_list_error(self, error: str):
        self._status_label.setText(f"⚠  {error}")
        self._status_label.setStyleSheet(
            f"color: {Colors.ERROR}; font-size: 12px; "
            f"padding: 4px 12px; background-color: {Colors.BG_DARK};"
        )
        self._list_worker = None

    # ══════════════════════════════════════════════════════
    #  Load Model
    # ══════════════════════════════════════════════════════

    def _on_load_model(self):
        model_name = self._chat_panel.get_selected_model()
        if not model_name:
            self._status_label.setText("⚠  No model selected")
            return

        options = self._menu_panel.get_model_options()

        self._status_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; "
            f"padding: 4px 12px; background-color: {Colors.BG_DARK};"
        )

        self._load_worker = ModelLoadWorker(model_name, options)
        self._load_worker.progress_updated.connect(self._on_load_progress)
        self._load_worker.load_complete.connect(self._on_load_complete)
        self._load_worker.error_occurred.connect(self._on_load_error)
        self._load_worker.start()

    def _on_load_progress(self, msg: str):
        self._status_label.setText(f"⏳  {msg}")

    def _on_load_complete(self, model_name: str, load_time_s: float, is_warm: bool):
        self._loaded_model = model_name
        self._overlay.update_model(model_name)
        warm_txt = "warm" if is_warm else "cold"
        self._status_label.setText(f"✓  '{model_name}' loaded in {load_time_s:.2f}s ({warm_txt})")
        self._status_label.setStyleSheet(
            f"color: {Colors.SUCCESS}; font-size: 12px; "
            f"padding: 4px 12px; background-color: {Colors.BG_DARK};"
        )
        self._load_worker = None

    def _on_load_error(self, error: str):
        self._status_label.setText(f"⚠  {error}")
        self._status_label.setStyleSheet(
            f"color: {Colors.ERROR}; font-size: 12px; "
            f"padding: 4px 12px; background-color: {Colors.BG_DARK};"
        )
        self._load_worker = None

    # ══════════════════════════════════════════════════════
    #  Stop Model
    # ══════════════════════════════════════════════════════

    def _on_stop_model(self):
        model_name = self._chat_panel.get_selected_model()
        if not model_name:
            self._status_label.setText("⚠  No model selected to stop")
            return

        self._status_label.setText(f"⏳  Stopping '{model_name}'…")
        self._stop_worker = ModelStopWorker(model_name)
        self._stop_worker.stop_complete.connect(self._on_stop_complete)
        self._stop_worker.error_occurred.connect(self._on_stop_error)
        self._stop_worker.start()

    def _on_stop_complete(self, model_name: str):
        if self._loaded_model == model_name:
            self._loaded_model = None
        self._status_label.setText(f"⏹  '{model_name}' stopped and unloaded")
        self._status_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; "
            f"padding: 4px 12px; background-color: {Colors.BG_DARK};"
        )
        self._stop_worker = None

    def _on_stop_error(self, error: str):
        self._status_label.setText(f"⚠  {error}")
        self._status_label.setStyleSheet(
            f"color: {Colors.ERROR}; font-size: 12px; "
            f"padding: 4px 12px; background-color: {Colors.BG_DARK};"
        )
        self._stop_worker = None

    # ── Cleanup on close ─────────────────────────────────
    def closeEvent(self, event):
        self._stats_panel.stop()
        if self._overlay:
            self._overlay.close()
        for worker in [self._load_worker, self._stop_worker]:
            if worker and worker.isRunning():
                worker.terminate()
        super().closeEvent(event)
