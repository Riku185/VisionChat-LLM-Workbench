"""
VideoWorker — background thread that extracts keyframes from a video file.
Returns a list of base64-encoded JPEG strings.
"""

import base64
import cv2
from PyQt6.QtCore import QThread, pyqtSignal

from app.config import MAX_VIDEO_FRAMES, VIDEO_SAMPLE_RATE_SEC


class VideoWorker(QThread):
    """Extracts keyframes from a video and emits them as base64 strings."""

    frames_extracted = pyqtSignal(list)          # list[str] of base64
    progress_updated = pyqtSignal(int, int)      # (current, total)
    error_occurred = pyqtSignal(str)

    def __init__(self, video_path: str, parent=None):
        super().__init__(parent)
        self._video_path = video_path

    # ── Thread entry point ───────────────────────────────
    def run(self):
        try:
            cap = cv2.VideoCapture(self._video_path)
            if not cap.isOpened():
                self.error_occurred.emit(
                    f"Cannot open video: {self._video_path}"
                )
                return

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration_sec = total_frames / fps
            sample_interval = int(fps * VIDEO_SAMPLE_RATE_SEC)

            # Decide how many frames to extract
            num_samples = min(
                int(duration_sec / VIDEO_SAMPLE_RATE_SEC),
                MAX_VIDEO_FRAMES,
            )
            if num_samples < 1:
                num_samples = 1

            frames_b64: list[str] = []
            frame_idx = 0
            extracted = 0

            while extracted < num_samples:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret:
                    break

                # Resize for efficiency (max 720p)
                h, w = frame.shape[:2]
                if w > 1280:
                    scale = 1280.0 / w
                    frame = cv2.resize(
                        frame, (1280, int(h * scale)),
                        interpolation=cv2.INTER_AREA,
                    )

                # Encode to JPEG bytes → base64
                _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                b64_str = base64.b64encode(buf.tobytes()).decode("utf-8")
                frames_b64.append(b64_str)

                extracted += 1
                self.progress_updated.emit(extracted, num_samples)
                frame_idx += sample_interval

            cap.release()
            self.frames_extracted.emit(frames_b64)

        except Exception as exc:
            self.error_occurred.emit(f"Video processing failed: {exc}")
