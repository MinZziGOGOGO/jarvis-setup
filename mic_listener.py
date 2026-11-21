"""
Real-time microphone level meter using sounddevice.
Non-blocking — uses PortAudio callback thread.
"""
import threading
import time
import numpy as np
import sounddevice as sd
import warnings

from config import MIC_DEVICE_INDEX, MIC_MAX_RMS


class MicListener:
    """Reads mic RMS level in background, emits smoothed 0.0-1.0 via callback."""

    def __init__(self):
        self._stream = None
        self._running = False
        self._callback_fn = lambda level: None
        self._smoothed = 0.0
        self._emit_timer = None
        self._emit_interval = 0.05  # 50ms
        self._lock = threading.Lock()
        self._device_index = MIC_DEVICE_INDEX

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            warnings.warn(f"MicListener status: {status}")
        try:
            rms = float(np.sqrt(np.mean(indata ** 2)))
            with self._lock:
                self._smoothed = 0.8 * self._smoothed + 0.2 * rms
        except Exception:
            pass

    def _emit_level(self):
        while self._running:
            with self._lock:
                raw = self._smoothed
            normalized = min(raw / MIC_MAX_RMS, 1.0)
            try:
                self._callback_fn(normalized)
            except Exception:
                pass
            time.sleep(self._emit_interval)

    def start(self):
        """Start mic capture. Non-blocking."""
        if self._running:
            return
        self._running = True
        try:
            self._stream = sd.InputStream(
                device=self._device_index,
                channels=1,
                samplerate=44100,
                blocksize=2048,
                callback=self._audio_callback,
            )
            self._stream.start()
        except Exception as e:
            warnings.warn(f"MicListener: failed to open device {self._device_index}: {e}. Using default.")
            try:
                self._stream = sd.InputStream(
                    channels=1,
                    samplerate=44100,
                    blocksize=2048,
                    callback=self._audio_callback,
                )
                self._stream.start()
            except Exception as e2:
                warnings.warn(f"MicListener: completely failed: {e2}")
                self._running = False
                return

        self._emit_timer = threading.Thread(target=self._emit_level, daemon=True)
        self._emit_timer.start()

    def stop(self):
        self._running = False
        self._smoothed = 0.0
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def set_callback(self, fn):
        """Set the function called with float 0.0-1.0 level."""
        self._callback_fn = fn
