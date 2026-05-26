"""
TTSWorker — background thread that speaks text via pyttsx3.

Emits tts_complete(metrics) after speech is produced, where metrics
contains timing and voice information for display in the UI.
"""

import time

from PyQt6.QtCore import QThread, pyqtSignal


class TTSWorker(QThread):
    """Speaks text using pyttsx3 in a background thread."""

    tts_complete   = pyqtSignal(dict)   # {gen_time, playback_est, voice}
    error_occurred = pyqtSignal(str)

    # Estimated words per minute for duration calculation
    _WPM = 150

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._text = text

    def run(self):
        t0 = time.perf_counter()
        voice_name = "default"
        try:
            import pyttsx3
            engine = pyttsx3.init()

            # Capture voice name
            try:
                voices = engine.getProperty("voices")
                if voices:
                    voice_name = voices[0].name
            except Exception:
                pass

            gen_start = time.perf_counter()
            engine.say(self._text)
            engine.runAndWait()
            gen_time = time.perf_counter() - gen_start

            # Estimate playback duration from word count
            word_count = len(self._text.split())
            playback_est = (word_count / self._WPM) * 60.0  # seconds

            self.tts_complete.emit({
                "gen_time":     round(gen_time, 2),
                "playback_est": round(playback_est, 1),
                "voice":        voice_name,
                "total_time":   round(time.perf_counter() - t0, 2),
            })

        except ImportError:
            self.error_occurred.emit("pyttsx3 not installed")
        except Exception as exc:
            self.error_occurred.emit(f"TTS error: {exc}")
