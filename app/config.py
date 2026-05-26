"""
Application-wide configuration constants.
"""

# ── Application ───────────────────────────────────────────────
APP_NAME = "Vision Chat — Performance Workbench"

# ── Ollama Model ─────────────────────────────────────────────
DEFAULT_MODEL = "qwen2.5vl:3b"
OLLAMA_HOST = "http://localhost:11434"

# ── System Monitoring ─────────────────────────────────────────
STATS_POLL_INTERVAL_MS = 1000         # polling rate for CPU/GPU/RAM
STATS_BUFFER_SIZE = 60                # ~60 seconds of data at 1000ms

# ── Video Processing ─────────────────────────────────────────
MAX_VIDEO_FRAMES = 60               # max keyframes extracted
VIDEO_SAMPLE_RATE_SEC = 1.0           # one frame per second

# ── Supported File Extensions ────────────────────────────────
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")
VIDEO_EXTENSIONS = (".mp4", ".avi")
ALL_EXTENSIONS = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS

# ── Theme Colors ─────────────────────────────────────────────
class Colors:
    BG_DARKEST   = "#0D0D0D"
    BG_DARK      = "#141414"
    BG_PANEL     = "#171717"
    BG_CARD      = "#1E1E1E"
    BG_INPUT     = "#2A2A2A"
    BG_HOVER     = "#333333"

    ACCENT       = "#6C63FF"
    ACCENT_LIGHT = "#8B83FF"
    ACCENT_DIM   = "#4A42CC"

    USER_BUBBLE  = "#2A2A40"
    ASST_BUBBLE  = "#1A1A2E"

    TEXT_PRIMARY  = "#ECECEC"
    TEXT_SECONDARY = "#8E8E93"
    TEXT_MUTED    = "#555555"

    BORDER       = "#2A2A2A"
    BORDER_FOCUS = "#6C63FF"

    # Graph colors
    CPU_COLOR    = "#4FC3F7"
    GPU_COLOR    = "#AB47BC"
    RAM_COLOR    = "#66BB6A"
    VRAM_COLOR   = "#FF7043"

    # Performance / telemetry colors
    TPS_COLOR    = "#00E5FF"
    TTFT_COLOR   = "#69F0AE"
    LATENCY_COLOR = "#FFD740"
    TOKEN_COLOR  = "#B388FF"

    # Model state badge colors
    STATE_IDLE    = "#546E7A"
    STATE_LOADING = "#FF9800"
    STATE_RUNNING = "#4CAF50"
    STATE_ERROR   = "#EF5350"

    # Analytics chart colors
    CHART_TPS    = "#00E5FF"
    CHART_TIME   = "#FFD740"
    CHART_RAM    = "#66BB6A"
    CHART_VRAM   = "#FF7043"

    SUCCESS      = "#4CAF50"
    WARNING      = "#FF9800"
    ERROR        = "#EF5350"

# ── Window Geometry ──────────────────────────────────────────
MIN_WINDOW_WIDTH  = 1100
MIN_WINDOW_HEIGHT = 700
DEFAULT_STATS_WIDTH = 260
DEFAULT_MENU_WIDTH  = 56
MENU_EXPANDED_WIDTH = 320

# ── Terminal ─────────────────────────────────────────────────
TERMINAL_HEIGHT = 300

# ── Performance Overlay ──────────────────────────────────────
OVERLAY_OPACITY      = 0.88          # 0.0–1.0
OVERLAY_WIDTH        = 220
OVERLAY_HEIGHT       = 150

# ── TPS Gauge ────────────────────────────────────────────────
TPS_GAUGE_MAX        = 120.0         # tok/s upper limit for gauge scale

# ── Analytics / Session ──────────────────────────────────────
ANALYTICS_HISTORY    = 50            # max data points in analytics charts

# ── Context Bar ──────────────────────────────────────────────
CONTEXT_BAR_HEIGHT   = 14

# ── Auto-description Prompt ──────────────────────────────────
IMAGE_PROMPT = "Briefly describe this image in 2-3 sentences."
VIDEO_PROMPT = "These are keyframes extracted from a video. Briefly describe what is happening in the video in 2-3 sentences."
