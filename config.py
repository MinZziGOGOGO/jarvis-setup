"""
JarvisUI configuration.

Paths can be overridden with environment variables so the UI works with any
Jarvis checkout: JARVIS_PATH (the Jarvis repository) and JARVIS_PYTHON
(the Python interpreter of its virtual environment).
"""
import os
import sys

# ---- Microphone ----
# None = system default input device; set an index from `python -m sounddevice`
MIC_DEVICE_INDEX = int(os.environ["JARVIS_MIC_DEVICE"]) if os.environ.get("JARVIS_MIC_DEVICE") else None
MIC_MAX_RMS = 0.3

# ---- Jarvis process ----
# By default JarvisUI expects to live in a "jarvis_ui" folder inside the Jarvis repository
JARVIS_PATH = os.environ.get("JARVIS_PATH", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_venv_python = os.path.join(JARVIS_PATH, ".venv", "Scripts" if os.name == "nt" else "bin",
                            "python.exe" if os.name == "nt" else "python")
PYTHON_EXE = os.environ.get("JARVIS_PYTHON", _venv_python if os.path.exists(_venv_python) else sys.executable)

# ---- Widget Geometry ----
WIDGET_SIZE = 100
WIDGET_OFFSET = 20
WIDGET_POSITION = "top-left"

# ---- Fullscreen Orb ----
FULLSCREEN_ORB_SIZE = 300
FULLSCREEN_HOTKEY = "ctrl+shift+j"
FULLSCREEN_CHECK_INTERVAL_SEC = 2

# ---- Log Widget ----
LOG_WIDGET_WIDTH = 380
LOG_WIDGET_HEIGHT = 500
MAX_LOG_LINES = 150
CHAR_REVEAL_DELAY_MS = 15

# ---- State Timing ----
STATE_SPEAKING_DURATION_SEC = 4
RESTART_DELAY_SEC = 5

# ---- Orb Rendering (Three.js) ----
ORB_RADIUS = 1.0
ORB_POINT_COUNT = 400
ORB_POINT_DEVIATION = 0.15
ORB_CONNECTION_RADIUS = 0.35

# ---- Log Toggle ----
LOG_TOGGLE_KEY = "l"

# ---- Skyline Dimensions ----
SKYLINE_WIDTH = 1920
SKYLINE_HEIGHT = 300

# ---- Typography ----
# Hack: a terminal font with a slashed zero (falls back to any monospace font)
HACKER_FONT = "Hack"
