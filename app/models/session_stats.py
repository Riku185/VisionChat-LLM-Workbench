"""
SessionStats — thread-safe singleton accumulating per-session telemetry.

RequestRecord stores per-inference metrics. SessionStats is the top-level
container updated by ChatPanel after each generation_complete signal.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import List

from app.config import ANALYTICS_HISTORY


# ── Per-inference record ─────────────────────────────────────────────────────

@dataclass
class RequestRecord:
    timestamp: float          # time.time()
    model: str
    tps: float                # tokens per second
    total_time: float         # wall-clock seconds
    ttft: float               # time-to-first-token (seconds)
    output_tokens: int
    prompt_tokens: int
    load_time: float          # model load_duration in seconds
    stop_reason: str          # e.g. "stop", "length", ""
    is_warm: bool             # True if model was already loaded
    failed: bool = False      # True if request errored


# ── Session-level container ──────────────────────────────────────────────────

class SessionStats:
    """Thread-safe singleton accumulating analytics data for the session."""

    _instance: "SessionStats | None" = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "SessionStats":
        with cls._lock:
            if cls._instance is None:
                obj = super().__new__(cls)
                obj._init()
                cls._instance = obj
        return cls._instance

    def _init(self) -> None:
        self._requests: List[RequestRecord] = []
        self._peak_ram: float = 0.0
        self._peak_vram: float = 0.0
        self._peak_vram_gb: float = 0.0
        self._timeout_events: int = 0
        self._retry_attempts: int = 0
        self._session_start: float = time.time()
        self._rlock = threading.RLock()

    # ── Mutations ────────────────────────────────────────────────────────────

    def add_request(self, record: RequestRecord) -> None:
        with self._rlock:
            self._requests.append(record)
            # Trim to history limit (keep newest)
            if len(self._requests) > ANALYTICS_HISTORY:
                self._requests = self._requests[-ANALYTICS_HISTORY:]

    def update_peak_ram(self, ram_pct: float) -> None:
        with self._rlock:
            self._peak_ram = max(self._peak_ram, ram_pct)

    def update_peak_vram(self, vram_pct: float, vram_gb: float = 0.0) -> None:
        with self._rlock:
            self._peak_vram = max(self._peak_vram, vram_pct)
            self._peak_vram_gb = max(self._peak_vram_gb, vram_gb)

    def record_timeout(self) -> None:
        with self._rlock:
            self._timeout_events += 1

    def record_retry(self) -> None:
        with self._rlock:
            self._retry_attempts += 1

    # ── Computed properties ──────────────────────────────────────────────────

    @property
    def requests(self) -> List[RequestRecord]:
        with self._rlock:
            return list(self._requests)

    @property
    def total_requests(self) -> int:
        with self._rlock:
            return len(self._requests)

    @property
    def failed_requests(self) -> int:
        with self._rlock:
            return sum(1 for r in self._requests if r.failed)

    @property
    def total_tokens(self) -> int:
        with self._rlock:
            return sum(r.output_tokens + r.prompt_tokens for r in self._requests)

    @property
    def avg_tps(self) -> float:
        with self._rlock:
            valid = [r.tps for r in self._requests if r.tps > 0 and not r.failed]
            return sum(valid) / len(valid) if valid else 0.0

    @property
    def avg_response_time(self) -> float:
        with self._rlock:
            valid = [r.total_time for r in self._requests if not r.failed]
            return sum(valid) / len(valid) if valid else 0.0

    @property
    def peak_ram(self) -> float:
        return self._peak_ram

    @property
    def peak_vram(self) -> float:
        return self._peak_vram

    @property
    def peak_vram_gb(self) -> float:
        return self._peak_vram_gb

    @property
    def timeout_events(self) -> int:
        return self._timeout_events

    @property
    def retry_attempts(self) -> int:
        return self._retry_attempts

    @property
    def session_duration(self) -> float:
        return time.time() - self._session_start

    def tps_history(self) -> List[float]:
        with self._rlock:
            return [r.tps for r in self._requests]

    def response_time_history(self) -> List[float]:
        with self._rlock:
            return [r.total_time for r in self._requests]

    def reset(self) -> None:
        with self._rlock:
            self._init()
