"""
Detects fullscreen games/exclusive apps on Windows using ctypes + user32.dll.
"""
import ctypes
import threading
import os
from ctypes import wintypes

from config import FULLSCREEN_CHECK_INTERVAL_SEC


# ── Windows API bindings ──
user32 = ctypes.windll.user32

# RECT struct
class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


# System metrics
SM_CXSCREEN = 0
SM_CYSCREEN = 1

# Window long flags
GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000


def _is_fullscreen_exclusive() -> bool:
    """Check if the foreground window is fullscreen exclusive."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return False

    # Get our own PID so we can exclude JarvisUI windows
    # (simplified: skip tiny windows)
    rect = RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return False

    screen_w = user32.GetSystemMetrics(SM_CXSCREEN)
    screen_h = user32.GetSystemMetrics(SM_CYSCREEN)

    win_w = rect.right - rect.left
    win_h = rect.bottom - rect.top

    # Must cover the full screen
    if win_w < screen_w or win_h < screen_h:
        return False
    if rect.left != 0 or rect.top != 0:
        return False

    # Check window style — true exclusive fullscreen has no chrome
    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
    has_chrome = bool(style & (WS_CAPTION | WS_THICKFRAME))

    # Fullscreen exclusive = covers screen AND has no window chrome
    return not has_chrome


class WindowDetector:
    """Background daemon that watches for fullscreen apps."""

    def __init__(self, callback=None):
        self._callback = callback or (lambda state: None)
        self._was_fullscreen = False
        self._running = False
        self._thread = None

    def _loop(self):
        while self._running:
            try:
                is_fs = _is_fullscreen_exclusive()
            except Exception:
                is_fs = False

            if is_fs != self._was_fullscreen:
                self._was_fullscreen = is_fs
                self._callback(is_fs)

            threading.Event().wait(FULLSCREEN_CHECK_INTERVAL_SEC)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    @property
    def is_fullscreen(self) -> bool:
        return self._was_fullscreen
