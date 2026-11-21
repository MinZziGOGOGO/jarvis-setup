"""
Python→JS bridge using QWebEnginePage.runJavaScript().
One-way communication — no QWebChannel needed.
"""
from PyQt6.QtWebEngineWidgets import QWebEngineView


class OrbBridge:
    """Connects Python microphone/state updates to the Three.js orb."""

    def __init__(self, view: QWebEngineView):
        self._view = view
        self._ready = False
        self._queue = []

        view.page().loadFinished.connect(self._on_loaded)

    def _on_loaded(self, ok: bool):
        if not ok:
            return
        self._ready = True
        # Flush queued calls
        for js in self._queue:
            self._view.page().runJavaScript(js)
        self._queue.clear()

    def _call(self, js: str):
        """Run JavaScript now or queue for later."""
        if self._ready:
            self._view.page().runJavaScript(js)
        else:
            self._queue.append(js)

    VALID_STATES = ("idle", "listening", "thinking", "speaking")

    def update_state(self, state: str) -> None:
        """Set the orb's visual state. Valid: idle, listening, thinking, speaking."""
        if state in self.VALID_STATES:
            self._call(f"window.setState('{state}')")

    def update_mic_level(self, level: float) -> None:
        """Push microphone level 0.0-1.0 to the orb."""
        if not self._ready:
            return  # mic levels are only useful live, don't queue them
        self._call(f"window.setMicLevel({float(level):.3f})")
