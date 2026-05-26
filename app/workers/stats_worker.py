"""
StatsWorker — background thread that polls CPU, GPU, RAM, and VRAM usage.

Emits stats_updated with both percentage values and absolute VRAM GB.
"""

import psutil
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal

try:
    import GPUtil
    _GPU_AVAILABLE = True
except ImportError:
    _GPU_AVAILABLE = False

from app.config import STATS_POLL_INTERVAL_MS


class StatsWorker(QThread):
    """Polls system metrics and emits them periodically."""

    # (cpu%, gpu%, ram%, vram%, vram_used_gb, vram_total_gb, temp_c, power_w)
    stats_updated = pyqtSignal(float, float, float, float, float, float, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

    # ── Thread loop ──────────────────────────────────────────────────────────
    def run(self):
        # Prime psutil so the first reading isn't 0
        psutil.cpu_percent(interval=None)

        while self._running:
            cpu         = psutil.cpu_percent(interval=None)
            mem         = psutil.virtual_memory()
            ram_mb      = mem.used / (1024 * 1024)
            ram_total_mb= mem.total / (1024 * 1024)
            gpu         = self._get_gpu_usage()
            vram_mb     = self._get_gpu_vram_used_mb()
            vram_total_mb = self._get_gpu_vram_total_mb()
            temp_c, power_w = self._get_gpu_temp_power()
            self.stats_updated.emit(cpu, gpu, ram_mb, vram_mb, vram_total_mb, ram_total_mb, temp_c, power_w)
            self.msleep(STATS_POLL_INTERVAL_MS)

    # ── GPU helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _get_gpu_usage() -> float:
        if not _GPU_AVAILABLE:
            return -1.0
        try:
            gpus = GPUtil.getGPUs()
            return gpus[0].load * 100.0 if gpus else -1.0
        except Exception:
            return -1.0

    @staticmethod
    def _get_gpu_vram_used_mb() -> float:
        if not _GPU_AVAILABLE:
            return 0.0
        try:
            gpus = GPUtil.getGPUs()
            return float(gpus[0].memoryUsed) if gpus else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _get_gpu_vram_total_mb() -> float:
        if not _GPU_AVAILABLE:
            return 0.0
        try:
            gpus = GPUtil.getGPUs()
            return float(gpus[0].memoryTotal) if gpus else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _get_gpu_temp_power() -> tuple[float, float]:
        if not _GPU_AVAILABLE:
            return 0.0, 0.0
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=temperature.gpu,power.draw", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, check=True
            )
            lines = result.stdout.strip().split('\n')
            if lines:
                parts = lines[0].split(',')
                if len(parts) >= 2:
                    return float(parts[0].strip()), float(parts[1].strip())
        except Exception:
            pass
        return 0.0, 0.0

    # ── Clean shutdown ───────────────────────────────────────────────────────
    def stop(self):
        self._running = False
        self.wait(2000)
