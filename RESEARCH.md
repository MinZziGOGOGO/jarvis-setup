# JarvisUI Research Findings

> Generated: 2026-05-29
> Purpose: Foundation research for JarvisUI — a hacker-style desktop overlay

---

## 1. Hacker-Style Monospace Font Recommendation

**Definitive pick: `Hack`**

CSS font-family: `"Hack", "Consolas", monospace`

### Why Hack

Hack is purpose-built for source code and terminal use. It stems from DejaVu Sans Mono / Bitstream Vera lineages — the same roots as many classic terminal typefaces — but with deliberate modifications that give it a sharper, more "hacker" character. Key traits:

- **Google Fonts availability**: yes — `@import url('https://fonts.googleapis.com/css2?family=Hack&display=swap')`
- **Zero dotted** (slashed zero) by default — iconic terminal aesthetic
- Distinctive glyphs: the lowercase `i`, `l`, `0`, and `g` are all intentionally differentiated for code readability
- Slightly condensed feel without sacrificing legibility
- Ships with multiple weights (Regular, Bold, Italic, Bold Italic)
- Native on Nerd Fonts patcher if icons are needed later

### Comparison with alternatives

| Font | Google Fonts | Hacker Vibe | Ligatures | Verdict |
|---|---|---|---|---|
| Hack | Yes | ★★★★★ | No (pure) | **Winner** |
| JetBrains Mono | Yes | ★★★★☆ | Yes | Too polished, "IDE" feel |
| Fira Code | Yes | ★★★☆☆ | Yes | Too friendly/modern |
| Source Code Pro | Yes | ★★★☆☆ | No | Bland, Adobe corporate |
| Cascadia Code | Yes | ★★★☆☆ | Yes | Microsoft corporate |
| Consolas | System | ★★★★☆ | No | Classic but Windows-only, no Google Fonts |

**Final CSS snippet:**

```css
@import url('https://fonts.googleapis.com/css2?family=Hack&display=swap');

body, .terminal, .console-output {
    font-family: "Hack", "Consolas", monospace;
    font-size: 14px;
    line-height: 1.4;
    color: #00ff00;
    background: #0a0a0a;
}
```

---

## 2. PyQt6 QWebEngineView + Three.js (runJavaScript, No QWebChannel)

### Architecture

- PyQt6 window hosts a `QWebEngineView`
- `QWebEngineView` loads a local HTML file containing the Three.js scene
- Python calls JavaScript functions via `QWebEnginePage.runJavaScript()`
- One-way communication (Python → JS) — no QWebChannel, no async callback overhead

### Approach

**Step 1: HTML template (scene.html)**

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { margin: 0; overflow: hidden; background: #000; }
        canvas { display: block; }
    </style>
</head>
<body>
    <script type="importmap">
    {
        "imports": {
            "three": "https://unpkg.com/three@0.160.0/build/three.module.js"
        }
    }
    </script>

    <script type="module">
        import * as THREE from 'three';

        // --- Global scene setup ---
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setPixelRatio(window.devicePixelRatio);
        document.body.appendChild(renderer.domElement);

        // Lights
        const ambient = new THREE.AmbientLight(0x404040);
        scene.add(ambient);
        const point = new THREE.PointLight(0x00ff88, 1, 100);
        point.position.set(10, 10, 10);
        scene.add(point);

        // A wireframe icosahedron — iconic hacker aesthetic
        const geometry = new THREE.IcosahedronGeometry(2, 1);
        const material = new THREE.MeshBasicMaterial({
            color: 0x00ff88,
            wireframe: true,
            transparent: true,
            opacity: 0.7,
        });
        const mesh = new THREE.Mesh(geometry, material);
        scene.add(mesh);

        camera.position.z = 5;

        // Resize handler
        function resize() {
            const rect = renderer.domElement.parentElement.getBoundingClientRect();
            renderer.setSize(rect.width, rect.height);
            camera.aspect = rect.width / (rect.height || 1);
            camera.updateProjectionMatrix();
        }
        window.addEventListener('resize', resize);
        resize();

        // Animation loop
        function animate() {
            requestAnimationFrame(animate);
            mesh.rotation.x += 0.005;
            mesh.rotation.y += 0.01;
            renderer.render(scene, camera);
        }
        animate();

        // --- Functions callable from Python via runJavaScript() ---
        // Each is exposed on window so runJavaScript can invoke it.

        window.updateRotation = function(xSpeed, ySpeed) {
            mesh.rotation.x += xSpeed || 0.005;
            mesh.rotation.y += ySpeed || 0.01;
        };

        window.setColor = function(hexColor) {
            material.color.set(hexColor);
            point.color.set(hexColor);
        };

        window.setWireframe = function(enabled) {
            material.wireframe = !!enabled;
        };

        window.setOpacity = function(value) {
            material.opacity = value;
        };

        window.getStatus = function() {
            return JSON.stringify({
                rotation: { x: mesh.rotation.x, y: mesh.rotation.y },
                color: '#' + material.color.getHexString(),
                wireframe: material.wireframe,
            });
        };

        console.log('[Three.js] Scene ready. Python can now call window.* functions.');
    </script>
</body>
</html>
```

**Step 2: Python code (main.py)**

```python
import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, QTimer


class HackerOverlay(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JarvisUI")
        self.resize(800, 600)

        # Central widget + layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # QWebEngineView
        self.webview = QWebEngineView()
        layout.addWidget(self.webview)

        # Load local HTML
        scene_path = Path(__file__).parent / "scene.html"
        self.webview.setUrl(QUrl.fromLocalFile(str(scene_path)))

        # --- Once loaded, call JS functions ---
        self.webview.loadFinished.connect(self._on_scene_ready)

    def _on_scene_ready(self, ok: bool):
        if not ok:
            print("ERROR: Failed to load scene.html")
            return

        print("[Python] Scene loaded. Calling JavaScript functions...")

        page = self.webview.page()

        # Call window functions — no QWebChannel needed
        page.runJavaScript("window.setColor('#ff3366');")
        page.runJavaScript("window.setWireframe(false);")
        page.runJavaScript("window.setOpacity(0.9);")

        # Read state back from JS
        page.runJavaScript("window.getStatus();", self._on_status_received)

        # Periodic updates from Python side
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)  # ~60 fps

    def _tick(self):
        """Called every ~16ms — drive JS updates from Python."""
        page = self.webview.page()
        # Vary rotation speed based on something (e.g., audio levels)
        page.runJavaScript("window.updateRotation(0.003, 0.008);")

    def _on_status_received(self, result):
        """Callback for runJavaScript return values."""
        print(f"[Python] Scene status: {result}")

    def apply_audio_intensity(self, level: float):
        """Example: map microphone level to visual properties."""
        page = self.webview.page()
        # Map 0.0–1.0 audio level to rotation speed
        page.runJavaScript(f"window.updateRotation({level * 0.02}, {level * 0.04});")
        # Map to color intensity
        g = int(100 + level * 155)  # 0x64–0xFF
        page.runJavaScript(f"window.setColor('#00{g:02x}00');")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HackerOverlay()
    window.show()
    sys.exit(app.exec())
```

**Key points:**

- `QWebEnginePage.runJavaScript(js_code, callback)` — the callback receives the JS return value as a Python string/None
- No QWebChannel needed because we only push data Python→JS (fire-and-forget calls)
- For return values, the optional `callback` parameter receives the `JSON.stringify()` result
- Must wait for `loadFinished` before calling `runJavaScript()`, or the JS globals won't exist yet
- Three.js loaded via ES module import map — no bundler needed

---

## 3. Real-Time Microphone Audio Levels with sounddevice (Non-Blocking)

### Approach

Use `sounddevice.InputStream` with a callback that computes RMS (root mean square) amplitude in a background thread. The callback is invoked by the PortAudio C library from a separate thread, so it never blocks the Python main/GUI thread.

```python
import sounddevice as sd
import numpy as np
from collections import deque


class AudioLevelMeter:
    """Non-blocking microphone level meter using sounddevice.InputStream.

    The callback runs in a PortAudio background thread — zero overhead
    on the main/PyQt thread.  Read `self.current_level` from your GUI
    timer or animation loop.
    """

    def __init__(
        self,
        device: int | None = None,
        sample_rate: int = 44100,
        block_size: int = 1024,
    ):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.device = device  # None = system default input

        # Current level (0.0–1.0), updated by callback, read by main thread
        self.current_level: float = 0.0

        # Smoothing buffer (rolling RMS over ~200ms at 44.1kHz)
        self._buffer = deque(maxlen=10)

        self._stream: sd.InputStream | None = None

    def _audio_callback(self, indata, frames, time_info, status):
        """Called by PortAudio from a background thread."""
        if status:
            print(f"[Audio] Warning: {status}")

        # Compute RMS amplitude for this block
        rms = np.sqrt(np.mean(indata**2))

        # Normalize to 0.0–1.0 range
        # (RMS of a full-scale sine wave is ~0.707, so scale accordingly)
        normalized = min(rms / 0.707, 1.0)

        # Rolling average for smoothness
        self._buffer.append(normalized)
        self.current_level = sum(self._buffer) / len(self._buffer)

    def start(self):
        """Start listening. Non-blocking — returns immediately."""
        self._stream = sd.InputStream(
            device=self.device,
            channels=1,               # Mono is sufficient for level metering
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self):
        """Stop the stream."""
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


# ---- Usage in PyQt6 ----

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.audio = AudioLevelMeter()
        self.audio.start()

        # Read level in a GUI timer (16ms = ~60fps)
        self._timer = QTimer()
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(16)

    def _on_tick(self):
        level = self.audio.current_level
        # level is ~0.0 (silence) to ~1.0 (loud)
        # Feed it to the Three.js scene or update a UI widget
        self.webview.apply_audio_intensity(level)  # from section 2

    def closeEvent(self, event):
        self.audio.stop()
        super().closeEvent(event)
```

### Alternative: PyAudio

If sounddevice is unavailable, the equivalent with pyaudio:

```python
import pyaudio
import numpy as np
import threading

class AudioLevelMeterPyAudio:
    def __init__(self, sample_rate=44100, chunk=1024):
        self.current_level = 0.0
        self._running = False
        self._thread = None
        self._chunk = chunk
        self._sample_rate = sample_rate

    def _loop(self):
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self._sample_rate,
            input=True,
            frames_per_buffer=self._chunk,
        )
        while self._running:
            data = np.frombuffer(stream.read(self._chunk, exception_on_overflow=False), dtype=np.int16)
            rms = np.sqrt(np.mean(data.astype(np.float64)**2))
            self.current_level = min(rms / 32768.0, 1.0)
        stream.close()
        p.terminate()

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
```

### Dependencies

```
pip install sounddevice numpy
# OR
pip install pyaudio numpy
```

On Linux: `sudo apt install portaudio19-dev` (for PyAudio) or `libportaudio2` (for sounddevice).

---

## 4. Detecting Fullscreen Exclusive vs Windowed/Borderless on Windows

### The Algorithm

1. Get the foreground window handle via `GetForegroundWindow()`
2. Get that window's rectangle via `GetWindowRect()` — this is the window bounds *including* title bar/borders
3. Get the primary monitor resolution via `GetSystemMetrics(SM_CXSCREEN)` and `SM_CYSCREEN`
4. Compare: if the window rect exactly matches (0, 0, screen_width, screen_height), the game is in **fullscreen exclusive** mode
5. If the window rect covers the full screen but `GetWindowLong(hwnd, GWL_STYLE)` still has `WS_CAPTION` | `WS_THICKFRAME` (border styles), it's **borderless windowed** mode

### Python Implementation (ctypes — no win32api dependency)

```python
import ctypes
from ctypes import wintypes

# --- Windows API bindings ---
user32 = ctypes.windll.user32

# Function signatures
GetForegroundWindow = user32.GetForegroundWindow
GetForegroundWindow.restype = wintypes.HWND

GetWindowRect = user32.GetWindowRect
GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
GetWindowRect.restype = wintypes.BOOL

GetSystemMetrics = user32.GetSystemMetrics
GetSystemMetrics.argtypes = [ctypes.c_int]
GetSystemMetrics.restype = ctypes.c_int

GetWindowLongW = user32.GetWindowLongW
GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
GetWindowLongW.restype = ctypes.c_long

IsIconic = user32.IsIconic
IsIconic.argtypes = [wintypes.HWND]
IsIconic.restype = wintypes.BOOL

# Constants
SM_CXSCREEN = 0
SM_CYSCREEN = 1
GWL_STYLE = -16

WS_CAPTION     = 0x00C00000
WS_THICKFRAME  = 0x00040000
WS_BORDER      = 0x00800000
WS_MAXIMIZEBOX = 0x00010000
WS_MINIMIZEBOX = 0x00020000

# Window style mask for "has window chrome"
WINDOWED_STYLE_MASK = WS_CAPTION | WS_THICKFRAME


class wintypes.RECT(ctypes.Structure):
    _fields_ = [
        ("left",   wintypes.LONG),
        ("top",    wintypes.LONG),
        ("right",  wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


def get_display_mode(hwnd: int | None = None) -> str:
    """
    Determine the display mode of a window.

    Returns one of:
        "fullscreen_exclusive"  — true fullscreen (exclusive mode)
        "borderless_windowed"   — borderless/borderless-windowed fullscreen
        "windowed"              — normal windowed
        "minimized"             — window is minimized
        "unknown"               — couldn't determine
    """
    if hwnd is None:
        hwnd = GetForegroundWindow()

    if hwnd == 0:
        return "unknown"

    # Skip minimized windows
    if IsIconic(hwnd):
        return "minimized"

    # Get window rectangle (includes title bar and borders if present)
    rect = wintypes.RECT()
    if not GetWindowRect(hwnd, ctypes.byref(rect)):
        return "unknown"

    win_left   = rect.left
    win_top    = rect.top
    win_right  = rect.right
    win_bottom = rect.bottom

    win_w = win_right - win_left
    win_h = win_bottom - win_top

    # Get primary monitor resolution
    screen_w = GetSystemMetrics(SM_CXSCREEN)
    screen_h = GetSystemMetrics(SM_CYSCREEN)

    # Check if window covers entire screen from (0,0)
    covers_fullscreen = (
        win_left == 0
        and win_top == 0
        and win_w == screen_w
        and win_h == screen_h
    )

    if not covers_fullscreen:
        return "windowed"

    # Covers full screen — check style to distinguish exclusive vs borderless
    style = GetWindowLongW(hwnd, GWL_STYLE)

    has_window_chrome = bool(style & WINDOWED_STYLE_MASK)

    if has_window_chrome:
        return "borderless_windowed"
    else:
        return "fullscreen_exclusive"


# ---- Usage ----

if __name__ == "__main__":
    import time

    while True:
        mode = get_display_mode()
        hwnd = GetForegroundWindow()
        print(f"Foreground window 0x{hwnd:X}: {mode}")
        time.sleep(1)
```

### Alternative with win32api (simpler API)

```python
import win32api
import win32gui
import win32con

def get_display_mode_win32(hwnd=None):
    if hwnd is None:
        hwnd = win32gui.GetForegroundWindow()

    if win32gui.IsIconic(hwnd):
        return "minimized"

    rect = win32gui.GetWindowRect(hwnd)  # (left, top, right, bottom)
    win_w = rect[2] - rect[0]
    win_h = rect[3] - rect[1]

    screen_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    screen_h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)

    covers = (rect[0] == 0 and rect[1] == 0
              and win_w == screen_w and win_h == screen_h)

    if not covers:
        return "windowed"

    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    if style & (win32con.WS_CAPTION | win32con.WS_THICKFRAME):
        return "borderless_windowed"
    else:
        return "fullscreen_exclusive"
```

### How It Works

- **Fullscreen exclusive**: The game takes over the display adapter. `GetWindowRect` returns exactly (0, 0, screen_w, screen_h) and the window style lacks `WS_CAPTION`, `WS_THICKFRAME`, etc.
- **Borderless windowed**: The window fills the screen but still has the desktop compositor (DWM) managing it. Window style retains `WS_CAPTION`/`WS_THICKFRAME` but the title bar is hidden via other means (often `WS_POPUP` style).
- **Windowed**: The window rect is smaller than the screen.

### Caveats

- Multi-monitor setups: this only checks the *primary* monitor. For multi-monitor, enumerate monitors with `EnumDisplayMonitors` and compare against each.
- Some games fake it: a few engines draw a fullscreen borderless window and hide chrome, making it hard to distinguish. The style check handles most engines (Unity, Unreal, Source) correctly.

> **Dependencies for win32api approach**: `pip install pywin32`

---

## 5. PyQt6 Click-Through Window (WS_EX_TRANSPARENT + WS_EX_LAYERED)

### Approach

Use Windows API `SetWindowLong` to add `WS_EX_TRANSPARENT` and `WS_EX_LAYERED` extended styles to the PyQt6 window's native HWND handle. Combined with `WS_EX_TOOLWINDOW` (hide from taskbar) and `WS_EX_TOPMOST`.

### Complete Implementation

```python
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt6.QtCore import Qt
import ctypes
from ctypes import wintypes

# --- Windows API bindings ---
user32 = ctypes.windll.user32

GetWindowLongW = user32.GetWindowLongW
GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
GetWindowLongW.restype = ctypes.c_long

SetWindowLongW = user32.SetWindowLongW
SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
SetWindowLongW.restype = ctypes.c_long

SetWindowPos = user32.SetWindowPos
SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.c_uint,
]
SetWindowPos.restype = wintypes.BOOL

SetLayeredWindowAttributes = user32.SetLayeredWindowAttributes
SetLayeredWindowAttributes.argtypes = [
    wintypes.HWND, wintypes.COLORREF, wintypes.BYTE, wintypes.DWORD,
]
SetLayeredWindowAttributes.restype = wintypes.BOOL

# Constants
GWL_EXSTYLE = -20

WS_EX_LAYERED     = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST     = 0x00000008
WS_EX_TOOLWINDOW  = 0x00000080
WS_EX_NOACTIVATE  = 0x08000000

HWND_TOPMOST = -1
SWP_NOMOVE   = 0x0002
SWP_NOSIZE   = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040

LWA_ALPHA    = 0x00000002
LWA_COLORKEY = 0x00000001


def make_click_through(hwnd: int, opacity: float = 1.0):
    """
    Make a window click-through (mouse events pass through to windows below).

    hwnd: Native window handle (int). Get via int(winId()) in PyQt.
    opacity: 0.0 (fully transparent) to 1.0 (fully opaque).
             At 0.0 the window is invisible; typical overlay opacity is 0.8–1.0.
    """
    # Read current extended style
    ex_style = GetWindowLongW(hwnd, GWL_EXSTYLE)

    # Add click-through + layered + topmost + tool window styles
    new_ex_style = ex_style | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE

    # Apply
    SetWindowLongW(hwnd, GWL_EXSTYLE, new_ex_style)

    # Set opacity via layered window attributes
    alpha = int(opacity * 255)
    SetLayeredWindowAttributes(hwnd, 0, alpha, LWA_ALPHA)

    # Ensure window stays on top
    SetWindowPos(
        hwnd, HWND_TOPMOST,
        0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
    )


def remove_click_through(hwnd: int):
    """Restore normal behavior (for interactivity when needed)."""
    ex_style = GetWindowLongW(hwnd, GWL_EXSTYLE)
    new_ex_style = ex_style & ~(WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE)
    SetWindowLongW(hwnd, GWL_EXSTYLE, new_ex_style)
    SetWindowPos(
        hwnd, 0, 0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
    )
    # Note: removes WS_EX_TOPMOST as a convenience; adjust if needed


class ClickThroughOverlay(QMainWindow):
    """A PyQt6 window that is completely click-through."""

    def __init__(self):
        super().__init__()

        # Transparent background (Qt-level)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        # Fullscreen: cover entire primary monitor
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

        # Example content
        label = QLabel("SYSTEM ONLINE // CLICK-THROUGH ACTIVE")
        label.setStyleSheet(
            "color: #00ff88; font-family: Hack, Consolas, monospace; "
            "font-size: 12px; background: transparent;"
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(label)

    def showEvent(self, event):
        """After window is shown, apply Windows-level click-through."""
        super().showEvent(event)
        hwnd = int(self.winId())
        make_click_through(hwnd, opacity=0.85)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ClickThroughOverlay()
    window.show()
    sys.exit(app.exec())
```

### Key Details

| Style Flag | Purpose |
|---|---|
| `WS_EX_TRANSPARENT` | Mouse clicks pass through to windows below |
| `WS_EX_LAYERED` | Required for per-pixel alpha / `SetLayeredWindowAttributes` |
| `WS_EX_TOPMOST` | Window stays above all non-topmost windows |
| `WS_EX_TOOLWINDOW` | Hides from taskbar and Alt+Tab |
| `WS_EX_NOACTIVATE` | Window never takes focus |

Combined with Qt's:
- `WA_TranslucentBackground` — enables per-pixel transparency at the Qt level
- `FramelessWindowHint` — removes Qt-drawn title bar
- `WindowStaysOnTopHint` — Qt-level topmost (reinforced by WS_EX_TOPMOST)

### Pitfalls

- **Interaction toggle**: You can't interact with click-through windows at all. To add interactive elements (buttons, sliders), you must temporarily call `remove_click_through()` and re-apply it after.
- **Performance**: WS_EX_LAYERED forces software rendering through DWM. For a simple overlay it's fine; for high-fps Three.js content, test performance on target hardware.
- **Linux/macOS**: This is Windows-only. On X11, use `XShapeCombineRectangles`; on Wayland, click-through requires compositor-specific protocols that PyQt doesn't expose. The research scope specified Windows, so this is correct.

---

## Dependency Summary

```bash
pip install PyQt6 PyQt6-WebEngine sounddevice numpy three
# Optional: pywin32 (alternative to ctypes for sections 4–5)
```

System-level (Linux):
```bash
sudo apt install portaudio19-dev  # for sounddevice/PyAudio
```

---

*End of research. All five sections complete with concrete code and definitive recommendations.*
