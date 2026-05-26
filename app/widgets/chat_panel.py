"""
ChatPanel — Central chat area with model selector dropdown, upload overlay,
message bubbles, input bar, loading indicator, and terminal integration.
Orchestrates the full conversation flow with Ollama.
"""

import base64
import json
import os
import time
from datetime import datetime

import cv2
import numpy as np

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QEvent
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QTextEdit, QSizePolicy, QFileDialog,
    QApplication, QComboBox,
)

from app.config import (
    Colors, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS,
    IMAGE_PROMPT, VIDEO_PROMPT, DEFAULT_MODEL,
)
from app.widgets.chat_bubble import ChatBubble
from app.widgets.upload_area import UploadArea
from app.widgets.terminal_panel import TerminalPanel
from app.widgets.context_bar import ContextBar
from app.workers.ollama_worker import OllamaWorker
from app.workers.video_worker import VideoWorker
from app.workers.tts_worker import TTSWorker
from app.models.session_stats import SessionStats, RequestRecord


class ChatPanel(QFrame):
    """Center panel: model selector → upload → auto-describe → chat loop."""

    # Emitted to update stats panel
    model_state_changed = pyqtSignal(str)   # Idle, Loading, Running, Error
    speed_updated       = pyqtSignal(float) # live tps

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chatPanel")

        self._messages: list[dict] = []        # Ollama message history
        self._media_path: str | None = None    # Original file path
        self._current_worker: OllamaWorker | None = None
        self._current_bubble: ChatBubble | None = None
        self._last_assistant_bubble: ChatBubble | None = None
        self._input_enabled = False
        self._model_options: dict = {}
        self._get_options_fn = None
        self._tts_enabled = False
        self._tts_worker: TTSWorker | None = None
        self._vision_models: set[str] = set()
        self._is_vision = True
        self._chat_font_size = 14
        self._debug_mode = False

        self._build_ui()
        self.model_state_changed.emit("Idle")

    # ══════════════════════════════════════════════════════
    #  UI Construction
    # ══════════════════════════════════════════════════════

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Model selector bar (top) ─────────────────────
        model_bar = QFrame()
        model_bar.setStyleSheet(
            f"background-color: {Colors.BG_DARK}; "
            f"border-bottom: 1px solid {Colors.BORDER};"
        )
        model_bar_layout = QHBoxLayout(model_bar)
        model_bar_layout.setContentsMargins(16, 8, 16, 8)
        model_bar_layout.setSpacing(10)

        model_icon = QLabel("🤖")
        model_icon.setStyleSheet("font-size: 18px; background: transparent;")
        model_bar_layout.addWidget(model_icon)

        model_label = QLabel("Model")
        model_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; "
            f"font-weight: 600; background: transparent;"
        )
        model_bar_layout.addWidget(model_label)

        self._model_combo = QComboBox()
        self._model_combo.setMinimumWidth(200)
        self._model_combo.setStyleSheet(
            f"""
            QComboBox {{
                background-color: {Colors.BG_INPUT};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 500;
            }}
            QComboBox:hover {{ border-color: {Colors.ACCENT}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox::down-arrow {{ image: none; border: none; }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_CARD};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                selection-background-color: {Colors.ACCENT_DIM};
                padding: 4px;
            }}
            """
        )
        self._model_combo.addItem(DEFAULT_MODEL)
        self._model_combo.currentTextChanged.connect(self._on_model_changed)
        model_bar_layout.addWidget(self._model_combo)

        # Context Bar
        model_bar_layout.addSpacing(16)
        self._context_bar = ContextBar()
        model_bar_layout.addWidget(self._context_bar)

        model_bar_layout.addStretch()
        root.addWidget(model_bar)

        # ── Scroll area for messages ─────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._scroll_content = QWidget()
        self._chat_layout = QVBoxLayout(self._scroll_content)
        self._chat_layout.setContentsMargins(0, 16, 0, 16)
        self._chat_layout.setSpacing(4)
        self._chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll.setWidget(self._scroll_content)

        root.addWidget(self._scroll, 1)

        # ── Upload overlay (centred) ─────────────────────
        self._upload_area = UploadArea()
        self._upload_area.file_selected.connect(self._on_file_selected)
        self._chat_layout.addStretch()
        self._chat_layout.addWidget(self._upload_area, 0, Qt.AlignmentFlag.AlignCenter)
        self._chat_layout.addStretch()

        # ── Loading indicator ────────────────────────────
        self._loading_label = QLabel("  ● ● ●  Generating…")
        self._loading_label.setObjectName("loadingLabel")
        self._loading_label.setVisible(False)
        self._loading_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 13px; "
            f"padding: 8px 24px; background: transparent;"
        )

        # ── Input bar ────────────────────────────────────
        input_bar = QFrame()
        input_bar.setStyleSheet(f"background-color: {Colors.BG_DARK}; border-top: 1px solid {Colors.BORDER};")
        input_layout = QHBoxLayout(input_bar)
        input_layout.setContentsMargins(16, 10, 16, 10)
        input_layout.setSpacing(8)

        # Attach button
        self._attach_btn = QPushButton("📎")
        self._attach_btn.setFixedSize(40, 40)
        self._attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._attach_btn.setToolTip("Attach image or video")
        self._attach_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; font-size: 20px; border-radius: 20px; color: {Colors.TEXT_SECONDARY}; }}"
            f"QPushButton:hover {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_PRIMARY}; }}"
        )
        self._attach_btn.clicked.connect(self._browse_attach)
        input_layout.addWidget(self._attach_btn)

        # Text input
        self._input = QTextEdit()
        self._input.setPlaceholderText("Upload an image or video to start…")
        self._input.setFixedHeight(44)
        self._input.setEnabled(False)
        self._input.setStyleSheet(
            f"QTextEdit {{ background-color: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY}; border: 1px solid {Colors.BORDER}; border-radius: 22px; padding: 10px 16px; font-size: 14px; }}"
            f"QTextEdit:focus {{ border-color: {Colors.ACCENT}; }}"
            f"QTextEdit:disabled {{ color: {Colors.TEXT_MUTED}; }}"
        )
        input_layout.addWidget(self._input, 1)

        # Speaker toggle button
        self._tts_btn = QPushButton("🔇")
        self._tts_btn.setFixedSize(40, 40)
        self._tts_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tts_btn.setToolTip("Enable voice (text-to-speech)")
        self._tts_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; font-size: 20px; border-radius: 20px; color: {Colors.TEXT_MUTED}; }}"
            f"QPushButton:hover {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_PRIMARY}; }}"
        )
        self._tts_btn.clicked.connect(self._toggle_tts)
        input_layout.addWidget(self._tts_btn)

        # Send button
        self._send_btn = QPushButton("➤")
        self._send_btn.setObjectName("sendButton")
        self._send_btn.setFixedSize(44, 44)
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setEnabled(False)
        self._send_btn.clicked.connect(self._on_send)
        input_layout.addWidget(self._send_btn)

        root.addWidget(self._loading_label)
        root.addWidget(input_bar)

        # ── Terminal panel (initially collapsed) ─────────
        self._terminal = TerminalPanel()
        root.addWidget(self._terminal)
        
        # Install event filters at the very end
        self._scroll.viewport().installEventFilter(self)
        self._input.installEventFilter(self)

    # ══════════════════════════════════════════════════════
    #  Model selector
    # ══════════════════════════════════════════════════════

    def get_selected_model(self) -> str:
        return self._model_combo.currentText()

    def set_models(self, models: list[str], vision_models: list[str] | None = None):
        self._vision_models = set(vision_models or [])

        current = self._model_combo.currentText()
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        for m in models:
            self._model_combo.addItem(m)
        self._model_combo.blockSignals(False)

        idx = self._model_combo.findText(current)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)
        elif models:
            default_idx = self._model_combo.findText(DEFAULT_MODEL)
            if default_idx >= 0:
                self._model_combo.setCurrentIndex(default_idx)
            else:
                self._model_combo.setCurrentIndex(0)

        self._on_model_changed(self._model_combo.currentText())

    def _on_model_changed(self, model_name: str):
        self._is_vision = model_name in self._vision_models
        self._messages.clear()
        self._media_path = None
        self._context_bar.reset()
        self.model_state_changed.emit("Idle")

        while self._chat_layout.count():
            item = self._chat_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        if self._is_vision:
            self._upload_area = UploadArea()
            self._upload_area.file_selected.connect(self._on_file_selected)
            self._chat_layout.addStretch()
            self._chat_layout.addWidget(self._upload_area, 0, Qt.AlignmentFlag.AlignCenter)
            self._chat_layout.addStretch()
            self._input.setPlaceholderText("Upload an image or video to start…")
            self._set_input_enabled(False)
        else:
            self._input.setPlaceholderText(f"Chat with {model_name}…")
            self._set_input_enabled(True)

    def set_debug_mode(self, enabled: bool):
        self._debug_mode = enabled

    # ══════════════════════════════════════════════════════
    #  Event filter — Enter to send + pinch-to-zoom
    # ══════════════════════════════════════════════════════

    def eventFilter(self, obj, event):
        if hasattr(self, '_input') and obj is self._input and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self._on_send()
                return True

        if hasattr(self, '_scroll') and obj is self._scroll.viewport() and event.type() == QEvent.Type.Wheel:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                delta = event.angleDelta().y()
                if delta > 0:
                    self._chat_font_size = min(32, self._chat_font_size + 1)
                elif delta < 0:
                    self._chat_font_size = max(10, self._chat_font_size - 1)
                self._apply_zoom()
                return True

        return super().eventFilter(obj, event)

    def _apply_zoom(self):
        size = self._chat_font_size
        for i in range(self._chat_layout.count()):
            item = self._chat_layout.itemAt(i)
            widget = item.widget()
            if widget and isinstance(widget, ChatBubble):
                widget._text_label.setStyleSheet(
                    f"color: {Colors.TEXT_PRIMARY}; font-size: {size}px; line-height: 1.5; background: transparent;"
                )

    # ══════════════════════════════════════════════════════
    #  Upload handling
    # ══════════════════════════════════════════════════════

    def _browse_attach(self):
        self._upload_area._browse()

    def _on_file_selected(self, path: str):
        self._media_path = path
        ext = os.path.splitext(path)[1].lower()
        self._remove_upload_overlay()

        if ext in IMAGE_EXTENSIONS:
            self._handle_image(path)
        elif ext in VIDEO_EXTENSIONS:
            self._handle_video(path)

    def _remove_upload_overlay(self):
        while self._chat_layout.count():
            item = self._chat_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

    def _handle_image(self, path: str):
        bubble = ChatBubble("user", IMAGE_PROMPT, image_path=path)
        self._add_bubble(bubble)

        b64 = self._preprocess_image(path)
        if b64 is None:
            self._on_error("Failed to load image: " + path)
            return

        msg = {"role": "user", "content": IMAGE_PROMPT, "images": [b64]}
        self._messages.append(msg)
        self._start_generation()

    @staticmethod
    def _preprocess_image(path: str) -> str | None:
        try:
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is None:
                return None

            h, w = img.shape[:2]
            MIN_DIM = 56
            if h < MIN_DIM or w < MIN_DIM:
                scale = max(MIN_DIM / h, MIN_DIM / w)
                img = cv2.resize(img, (max(MIN_DIM, int(w * scale)), max(MIN_DIM, int(h * scale))), interpolation=cv2.INTER_CUBIC)

            h, w = img.shape[:2]
            if w > 1280:
                scale = 1280.0 / w
                img = cv2.resize(img, (1280, int(h * scale)), interpolation=cv2.INTER_AREA)

            _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
            return base64.b64encode(buf.tobytes()).decode("utf-8")
        except Exception:
            return None

    def _handle_video(self, path: str):
        bubble = ChatBubble("user", f"🎬 Processing video…\n{os.path.basename(path)}")
        self._add_bubble(bubble)

        self._video_worker = VideoWorker(path)
        self._video_worker.frames_extracted.connect(self._on_frames_ready)
        self._video_worker.error_occurred.connect(self._on_error)
        self._video_worker.start()

    def _on_frames_ready(self, frames_b64: list[str]):
        msg = {"role": "user", "content": VIDEO_PROMPT, "images": frames_b64}
        self._messages.append(msg)
        self._start_generation()

    # ══════════════════════════════════════════════════════
    #  Chat send
    # ══════════════════════════════════════════════════════

    def _on_send(self):
        text = self._input.toPlainText().strip()
        if not text or not self._input_enabled:
            return

        self._input.clear()
        bubble = ChatBubble("user", text)
        self._add_bubble(bubble)

        self._messages.append({"role": "user", "content": text})
        self._start_generation()

    # ══════════════════════════════════════════════════════
    #  Generation (Ollama streaming)
    # ══════════════════════════════════════════════════════

    def set_options_provider(self, fn):
        self._get_options_fn = fn

    def _get_max_ctx(self) -> int:
        if self._get_options_fn:
            opts = self._get_options_fn()
            return opts.get("num_ctx", 2048)
        return 2048

    def _start_generation(self):
        self._set_input_enabled(False)
        self._loading_label.setVisible(True)
        self.model_state_changed.emit("Running")

        self._current_bubble = ChatBubble("assistant", "")
        self._last_assistant_bubble = self._current_bubble
        self._add_bubble(self._current_bubble)

        options = self._get_options_fn() if self._get_options_fn else {}
        model_name = self.get_selected_model()

        self._current_worker = OllamaWorker(model_name, self._messages, options=options)
        self._current_worker.token_received.connect(self._on_token)
        self._current_worker.speed_updated.connect(self._on_speed)
        self._current_worker.generation_complete.connect(self._on_complete)
        self._current_worker.error_occurred.connect(self._on_error)
        self._current_worker.start()

    def _on_token(self, token: str):
        if self._current_bubble:
            self._current_bubble.append_token(token)
            self._scroll_to_bottom()

    def _on_speed(self, tps: float):
        self._loading_label.setText(f"  ● ● ●  Generating…  ⚡ {tps:.1f} tok/s")
        self.speed_updated.emit(tps)

    def _on_complete(self, full_text: str, metrics: dict):
        self._loading_label.setVisible(False)
        self._loading_label.setText("  ● ● ●  Generating…")
        self.model_state_changed.emit("Idle")
        self.speed_updated.emit(0.0)

        self._messages.append({"role": "assistant", "content": full_text})

        # Append metrics bar to bubble
        if self._current_bubble:
            self._current_bubble.set_metrics_bar(metrics, self._debug_mode)

        # Update context bar
        total_tokens = metrics.get("prompt_tokens", 0) + metrics.get("output_tokens", 0)
        self._context_bar.update_context(total_tokens, self._get_max_ctx())

        # Record to analytics
        rec = RequestRecord(
            timestamp=time.time(),
            model=self.get_selected_model(),
            tps=metrics.get("tps", 0.0),
            total_time=metrics.get("total_time", 0.0),
            ttft=metrics.get("ttft", 0.0),
            output_tokens=metrics.get("output_tokens", 0),
            prompt_tokens=metrics.get("prompt_tokens", 0),
            load_time=metrics.get("load_duration", 0.0),
            stop_reason=metrics.get("stop_reason", ""),
            is_warm=metrics.get("is_warm", True),
            failed=False
        )
        SessionStats().add_request(rec)

        self._current_worker = None
        self._current_bubble = None
        self._set_input_enabled(True)

        if self._tts_enabled and full_text.strip():
            self._speak(full_text)

    # ══════════════════════════════════════════════════════
    #  Text-to-Speech
    # ══════════════════════════════════════════════════════

    def _toggle_tts(self):
        self._tts_enabled = not self._tts_enabled
        if self._tts_enabled:
            self._tts_btn.setText("🔊")
            self._tts_btn.setToolTip("Voice enabled (click to mute)")
            self._tts_btn.setStyleSheet(f"QPushButton {{ background: transparent; border: none; font-size: 20px; border-radius: 20px; color: {Colors.ACCENT}; }} QPushButton:hover {{ background: {Colors.BG_CARD}; }}")
        else:
            self._tts_btn.setText("🔇")
            self._tts_btn.setToolTip("Enable voice (text-to-speech)")
            self._tts_btn.setStyleSheet(f"QPushButton {{ background: transparent; border: none; font-size: 20px; border-radius: 20px; color: {Colors.TEXT_MUTED}; }} QPushButton:hover {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_PRIMARY}; }}")
            if self._tts_worker and self._tts_worker.isRunning():
                self._tts_worker.terminate()

    def _speak(self, text: str):
        if self._tts_worker and self._tts_worker.isRunning():
            self._tts_worker.terminate()
            self._tts_worker.wait(1000)

        self._tts_worker = TTSWorker(text)
        self._tts_worker.tts_complete.connect(self._on_tts_complete)
        self._tts_worker.start()

    def _on_tts_complete(self, metrics: dict):
        if self._last_assistant_bubble:
            self._last_assistant_bubble.set_tts_metrics(metrics)

    def _on_error(self, error: str):
        self._loading_label.setVisible(False)
        self.model_state_changed.emit("Error")
        self.speed_updated.emit(0.0)

        bubble = ChatBubble("assistant", f"⚠ Error: {error}")
        bubble._text_label.setStyleSheet(f"color: {Colors.ERROR}; font-size: 14px; background: transparent;")
        self._add_bubble(bubble)

        rec = RequestRecord(
            timestamp=time.time(), model=self.get_selected_model(),
            tps=0, total_time=0, ttft=0, output_tokens=0, prompt_tokens=0,
            load_time=0, stop_reason="error", is_warm=True, failed=True
        )
        SessionStats().add_request(rec)

        self._current_worker = None
        self._current_bubble = None
        self._set_input_enabled(True)

    # ══════════════════════════════════════════════════════
    #  Helpers
    # ══════════════════════════════════════════════════════

    def _add_bubble(self, bubble: ChatBubble):
        if self._chat_font_size != 14:
            bubble._text_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: {self._chat_font_size}px; line-height: 1.5; background: transparent;")
        self._chat_layout.addWidget(bubble)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(self._scroll.verticalScrollBar().maximum()))

    def _set_input_enabled(self, enabled: bool):
        self._input_enabled = enabled
        self._input.setEnabled(enabled)
        self._send_btn.setEnabled(enabled)
        if enabled:
            self._input.setPlaceholderText("Type a message…")
            self._input.setFocus()

    def toggle_terminal(self):
        self._terminal.toggle()

    # ══════════════════════════════════════════════════════
    #  Session Export / Import
    # ══════════════════════════════════════════════════════

    def export_session(self):
        if not self._messages: return
        default_name = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        default_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sessions")
        os.makedirs(default_dir, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(self, "Export Chat Session", os.path.join(default_dir, default_name), "JSON Files (*.json)")
        if not path: return

        export_messages = []
        for msg in self._messages:
            clean = {"role": msg["role"], "content": msg["content"]}
            if "images" in msg: clean["has_image"] = True
            export_messages.append(clean)

        data = {"model": self.get_selected_model(), "timestamp": datetime.now().isoformat(), "media_path": self._media_path or "", "messages": export_messages}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def import_session(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Chat Session", "", "JSON Files (*.json)")
        if not path: return

        try:
            with open(path, "r", encoding="utf-8") as f: data = json.load(f)
        except Exception as exc:
            self._on_error(f"Failed to load session: {exc}")
            return

        self._remove_upload_overlay()
        self._messages.clear()
        self._media_path = data.get("media_path", "")
        self._context_bar.reset()

        session_model = data.get("model", "")
        if session_model:
            idx = self._model_combo.findText(session_model)
            if idx >= 0: self._model_combo.setCurrentIndex(idx)

        messages = data.get("messages", [])
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            self._messages.append({"role": role, "content": content})
            image_path = None
            if msg.get("has_image") and role == "user" and self._media_path:
                image_path = self._media_path if os.path.exists(self._media_path) else None
            bubble = ChatBubble(role, content, image_path=image_path)
            self._add_bubble(bubble)

        self._set_input_enabled(True)
