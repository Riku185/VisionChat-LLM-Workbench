"""
OllamaWorker — background thread that streams chat responses from Ollama.

Emits token_received for each streamed token.
Emits generation_complete(full_text, metrics_dict) when done.
Emits speed_updated(tps) periodically during generation.

metrics_dict keys:
  tps            – tokens/sec (Ollama eval_count / eval_duration)
  total_time     – wall-clock seconds
  ttft           – time-to-first-token (seconds)
  output_tokens  – eval_count
  prompt_tokens  – prompt_eval_count
  load_duration  – model load_duration in seconds
  stop_reason    – done_reason string
  raw_response   – full final chunk dict (for debug mode)
  is_warm        – True if load_duration was negligible (< 0.5 s)
"""

import time

import ollama
from PyQt6.QtCore import QThread, pyqtSignal


class OllamaWorker(QThread):
    """Sends messages to Ollama and streams the response back."""

    token_received    = pyqtSignal(str)         # each streamed token
    generation_complete = pyqtSignal(str, dict)  # (full_text, metrics)
    speed_updated     = pyqtSignal(float)        # live tok/s estimate
    error_occurred    = pyqtSignal(str)          # error message

    def __init__(
        self,
        model_name: str,
        messages: list,
        options: dict | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._model_name = model_name
        self._messages   = messages
        self._options    = options or {}

    # ── Thread entry point ───────────────────────────────────────────────────
    def run(self):
        full_response = ""
        token_count   = 0
        ttft          = 0.0
        first_token   = False
        start_time    = time.perf_counter()
        last_speed_upd = start_time

        try:
            kwargs = dict(
                model=self._model_name,
                messages=self._messages,
                stream=True,
            )
            if self._options:
                kwargs["options"] = self._options

            final_chunk = None
            stream = ollama.chat(**kwargs)

            for chunk in stream:
                final_chunk = chunk

                # Detect first token for TTFT
                token = chunk.get("message", {}).get("content", "")
                if token:
                    if not first_token:
                        ttft = time.perf_counter() - start_time
                        first_token = True

                    full_response += token
                    token_count  += 1
                    self.token_received.emit(token)

                    # Emit live speed estimate every ~0.4 s
                    now = time.perf_counter()
                    if now - last_speed_upd >= 0.4:
                        elapsed = now - start_time
                        if elapsed > 0:
                            self.speed_updated.emit(token_count / elapsed)
                        last_speed_upd = now

            total_time = time.perf_counter() - start_time

            # ── Build metrics from Ollama's own fields ────────────────────
            metrics: dict = {
                "tps":           0.0,
                "total_time":    total_time,
                "ttft":          ttft,
                "output_tokens": 0,
                "prompt_tokens": 0,
                "load_duration": 0.0,
                "stop_reason":   "",
                "raw_response":  {},
                "is_warm":       True,
            }

            if final_chunk:
                raw = {}
                try:
                    raw = dict(final_chunk)
                except Exception:
                    pass

                eval_count        = final_chunk.get("eval_count", 0) or 0
                eval_duration     = final_chunk.get("eval_duration", 0) or 0   # ns
                prompt_eval_count = final_chunk.get("prompt_eval_count", 0) or 0
                load_duration_ns  = final_chunk.get("load_duration", 0) or 0   # ns

                tps = 0.0
                if eval_count and eval_duration:
                    tps = eval_count / (eval_duration / 1_000_000_000)

                # Fallback to our own measurement
                if tps == 0.0 and token_count and total_time:
                    tps = token_count / total_time

                load_secs = load_duration_ns / 1_000_000_000
                is_warm   = load_secs < 0.5   # heuristic: <0.5s means already loaded

                metrics.update({
                    "tps":           round(tps, 2),
                    "output_tokens": eval_count,
                    "prompt_tokens": prompt_eval_count,
                    "load_duration": round(load_secs, 3),
                    "stop_reason":   final_chunk.get("done_reason", ""),
                    "raw_response":  raw,
                    "is_warm":       is_warm,
                })

            self.generation_complete.emit(full_response, metrics)

        except ollama.ResponseError as exc:
            self.error_occurred.emit(f"Ollama error: {exc}")
        except Exception as exc:
            self.error_occurred.emit(
                f"Connection failed — is Ollama running?\n{exc}"
            )


# ── ModelListWorker ──────────────────────────────────────────────────────────

class ModelListWorker(QThread):
    """Fetches the list of locally available Ollama models, with size/quant info."""

    models_loaded   = pyqtSignal(list, list, dict)  # (all_names, vision_names, model_info)
    error_occurred  = pyqtSignal(str)

    # Families that indicate vision/multimodal capability
    VISION_FAMILIES  = {"clip"}
    VISION_KEYWORDS  = {"vl", "vision", "llava", "bakllava", "moondream"}

    def run(self):
        try:
            response  = ollama.list()
            all_names: list[str] = []
            vision_names: list[str] = []
            model_info: dict[str, dict] = {}   # name → {size_gb, quant}

            for m in response.models:
                name = m.model
                if not name:
                    continue
                all_names.append(name)

                # Detect vision capability
                families = set(m.details.families or [])
                is_vision = bool(families & self.VISION_FAMILIES)
                if not is_vision:
                    for kw in self.VISION_KEYWORDS:
                        if kw in name.lower():
                            is_vision = True
                            break
                if is_vision:
                    vision_names.append(name)

                # Extract size & quantization
                size_bytes = getattr(m, "size", 0) or 0
                size_gb    = round(size_bytes / 1_073_741_824, 2) if size_bytes else 0.0
                quant      = getattr(m.details, "quantization_level", "") or ""
                model_info[name] = {"size_gb": size_gb, "quant": quant}

            all_names.sort()
            self.models_loaded.emit(all_names, vision_names, model_info)
        except Exception as exc:
            self.error_occurred.emit(f"Failed to fetch models: {exc}")


# ── ModelLoadWorker ──────────────────────────────────────────────────────────

class ModelLoadWorker(QThread):
    """Preloads a model into Ollama's memory with given options."""

    progress_updated = pyqtSignal(str)
    load_complete    = pyqtSignal(str, float, bool)   # (model_name, load_time_s, is_warm)
    error_occurred   = pyqtSignal(str)

    def __init__(self, model_name: str, options: dict | None = None, parent=None):
        super().__init__(parent)
        self._model_name = model_name
        self._options    = options or {}

    def run(self):
        try:
            self.progress_updated.emit(f"Loading '{self._model_name}'…")
            t0 = time.perf_counter()

            kwargs = dict(
                model=self._model_name,
                prompt="",
                keep_alive="10m",
            )
            if self._options:
                kwargs["options"] = self._options

            result = ollama.generate(**kwargs)
            elapsed = time.perf_counter() - t0

            # Inspect load_duration from result if available
            load_ns = 0
            try:
                load_ns = result.get("load_duration", 0) or 0
            except Exception:
                pass
            load_secs = load_ns / 1_000_000_000 if load_ns else elapsed
            is_warm   = load_secs < 0.5

            self.progress_updated.emit(f"Model '{self._model_name}' loaded!")
            self.load_complete.emit(self._model_name, round(load_secs, 3), is_warm)

        except Exception as exc:
            self.error_occurred.emit(f"Failed to load model: {exc}")


# ── ModelStopWorker ──────────────────────────────────────────────────────────

class ModelStopWorker(QThread):
    """Unloads a model from Ollama's memory."""

    stop_complete  = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, model_name: str, parent=None):
        super().__init__(parent)
        self._model_name = model_name

    def run(self):
        try:
            ollama.generate(
                model=self._model_name,
                prompt="",
                keep_alive="0",
            )
            self.stop_complete.emit(self._model_name)
        except Exception as exc:
            self.error_occurred.emit(f"Failed to stop model: {exc}")
