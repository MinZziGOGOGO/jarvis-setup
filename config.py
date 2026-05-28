"""
JarvisUI Configuration Constants

Generated from T3 task specification.
Font choice (HACKER_FONT) based on T1 research — see RESEARCH.md.
"""

# ---- Microphone ----
MIC_DEVICE_INDEX = 1
MIC_MAX_RMS = 0.3

# ---- Jarvis Process Paths (Windows) ----
JARVIS_PATH = "C:\\tools\\jarvis"
PYTHON_EXE = "C:\\tools\\jarvis\\.venv\\Scripts\\python.exe"

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
# Font chosen via T1 research (RESEARCH.md): Hack — purpose-built for terminals,
# slashed zero, sharp hacker aesthetic, available on Google Fonts.
HACKER_FONT = "Hack"
