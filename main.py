"""
JarvisUI — Hacker-style holographic orb desktop overlay for Jarvis AI.
Dual-mode: widget (click-through overlay) + fullscreen (dashboard).
"""
import sys
import os
import ctypes
import random
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton,
)
from PyQt6.QtCore import Qt, QTimer, QUrl, QObject, pyqtSignal
from PyQt6.QtGui import QPixmap, QShortcut, QKeySequence
from PyQt6.QtWebEngineWidgets import QWebEngineView

from config import (
    WIDGET_SIZE, WIDGET_OFFSET, FULLSCREEN_ORB_SIZE, FULLSCREEN_HOTKEY,
    LOG_TOGGLE_KEY,
)
from bridge import OrbBridge
from mic_listener import MicListener
from jarvis_process import JarvisProcess
from window_detector import WindowDetector
from log_widget import LogWidget

try:
    import keyboard  # global hotkeys (needs admin rights on Linux)
except ImportError:
    keyboard = None

HERE = Path(__file__).resolve().parent

# ── Windows API for click-through ──
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080


class UiSignals(QObject):
    """Mic, Jarvis process, window detector and hotkeys all report from background
    threads. Qt widgets may only be touched from the GUI thread, so every callback
    emits a signal; Qt delivers it to the connected slot on the GUI thread."""
    mic_level = pyqtSignal(float)
    state = pyqtSignal(str)
    log_line = pyqtSignal(str)
    fullscreen_app = pyqtSignal(bool)
    toggle_mode = pyqtSignal()


class OrbWidget(QWidget):
    """Small transparent click-through orb — the widget mode."""

    def __init__(self, view: QWebEngineView):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(WIDGET_SIZE, WIDGET_SIZE)
        self.move(WIDGET_OFFSET, WIDGET_OFFSET)
        self._set_clickthrough()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        view.setFixedSize(WIDGET_SIZE, WIDGET_SIZE)
        layout.addWidget(view)

    def _set_clickthrough(self):
        """Let mouse clicks pass through to the windows behind the orb (Windows only)."""
        if os.name != "nt":
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            return
        hwnd = int(self.winId())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(
            hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW
        )


class FullscreenWindow(QMainWindow):
    """Fullscreen mode — larger orb + HUD controls + skyline."""

    def __init__(self, jarvis: JarvisProcess, log_widget: LogWidget, view: QWebEngineView, on_minimize):
        super().__init__()
        self._jarvis = jarvis
        self._log_widget = log_widget

        self.setWindowTitle("JarvisUI")
        self.setStyleSheet("background-color: #08000f;")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── Orb (centered) ──
        view.setFixedSize(FULLSCREEN_ORB_SIZE, FULLSCREEN_ORB_SIZE)
        layout.addStretch()
        layout.addWidget(view, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        # ── Skyline (bottom) ──
        self._skyline_label = QLabel()
        self._skyline_label.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._skyline_label, alignment=Qt.AlignmentFlag.AlignBottom)

        assets = HERE / "assets"
        self._skyline_frames = [str(p) for p in sorted(assets.glob("city_skyline_??.png"))]
        if not self._skyline_frames and (assets / "city_skyline.png").exists():
            self._skyline_frames = [str(assets / "city_skyline.png")]
        self._skyline_pixmaps = {}

        self._skyline_timer = QTimer(self)
        self._skyline_timer.timeout.connect(self._cycle_skyline)
        if len(self._skyline_frames) > 1:
            self._skyline_timer.start(500)

        # ── Top-right HUD panel ──
        self._hud = QWidget(self)
        self._hud.setStyleSheet("background: rgba(10, 0, 15, 0.8); border: 1px solid #9d00ff; border-radius: 4px;")
        hud_layout = QHBoxLayout(self._hud)
        hud_layout.setContentsMargins(8, 4, 8, 4)

        self._power_btn = QPushButton("●")
        self._power_btn.setFixedSize(28, 28)
        self._power_btn.setToolTip("Start / stop Jarvis")
        self._power_btn.clicked.connect(self._toggle_jarvis)
        self._update_power_button()

        min_btn = QPushButton("▼")
        min_btn.setFixedSize(28, 28)
        min_btn.setToolTip("Back to widget mode")
        min_btn.setStyleSheet("QPushButton { color: #00ffff; background: transparent; border: none; font-size: 14px; }")
        min_btn.clicked.connect(on_minimize)

        quit_btn = QPushButton("✕")
        quit_btn.setFixedSize(28, 28)
        quit_btn.setToolTip("Quit JarvisUI (Ctrl+Q)")
        quit_btn.setStyleSheet("QPushButton { color: #ff2d9b; background: transparent; border: none; font-size: 14px; }")
        quit_btn.clicked.connect(QApplication.quit)

        hud_layout.addWidget(self._power_btn)
        hud_layout.addWidget(min_btn)
        hud_layout.addWidget(quit_btn)
        self._hud.adjustSize()

        # Log toggle only while this window has focus (not a system-wide hotkey)
        QShortcut(QKeySequence(LOG_TOGGLE_KEY.upper()), self, activated=self._toggle_log)
        QShortcut(QKeySequence("Escape"), self, activated=on_minimize)
        QShortcut(QKeySequence("Ctrl+Q"), self, activated=QApplication.quit)

        self.showFullScreen()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._hud.move(self.width() - self._hud.width() - 10, 10)
        self._update_skyline()

    def _cycle_skyline(self):
        # Flicker the window lights at a random pace
        self._skyline_timer.setInterval(random.randint(200, 2000))
        self._update_skyline()

    def _update_skyline(self):
        if not self._skyline_frames or self.width() <= 0:
            return
        path = random.choice(self._skyline_frames)
        key = (path, self.width())
        if key not in self._skyline_pixmaps:
            self._skyline_pixmaps[key] = QPixmap(path).scaledToWidth(
                self.width(), Qt.TransformationMode.SmoothTransformation
            )
        self._skyline_label.setPixmap(self._skyline_pixmaps[key])

    def _toggle_log(self):
        if self._log_widget.isVisible():
            self._log_widget.hide()
        else:
            self._log_widget.move(20, 60)
            self._log_widget.show()
            self._log_widget.raise_()

    def _toggle_jarvis(self):
        if self._jarvis.is_running:
            self._jarvis.stop()
        else:
            self._jarvis.start()
        self._update_power_button()

    def _update_power_button(self):
        color = "#4caf50" if self._jarvis.is_running else "#ef5350"
        self._power_btn.setStyleSheet(
            f"QPushButton {{ color: {color}; background: transparent; border: none; font-size: 18px; }}"
        )


class JarvisUIApp:
    """Main app controller — manages mode switching and connects components."""

    def __init__(self, app: QApplication):
        self._app = app
        self._signals = UiSignals()

        # Shared QWebEngineView (moved between windows)
        self._view = QWebEngineView()
        self._view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self._bridge = OrbBridge(self._view)
        self._view.load(QUrl.fromLocalFile(str(HERE / "orb.html")))

        self._log = LogWidget()

        # Background components report through thread-safe signals
        self._signals.mic_level.connect(self._bridge.update_mic_level)
        self._signals.state.connect(self._bridge.update_state)
        self._signals.log_line.connect(self._log.add_line)
        self._signals.fullscreen_app.connect(self._on_fullscreen_app)
        self._signals.toggle_mode.connect(self._toggle_mode)

        self._mic = MicListener()
        self._mic.set_callback(self._signals.mic_level.emit)
        self._jarvis = JarvisProcess(
            state_callback=self._signals.state.emit,
            log_callback=self._signals.log_line.emit,
        )
        self._detector = WindowDetector(callback=self._signals.fullscreen_app.emit)

        self._mode = None  # "widget" | "fullscreen"
        self._widget_win = None
        self._fullscreen_win = None

        self._register_hotkey()

        self._mic.start()
        self._jarvis.start()
        self._detector.start()
        self._switch_to_widget()
        app.aboutToQuit.connect(self._shutdown)

    def _register_hotkey(self):
        if keyboard is None:
            print("JarvisUI: 'keyboard' not installed, global hotkey disabled")
            return
        try:
            keyboard.add_hotkey(FULLSCREEN_HOTKEY, self._signals.toggle_mode.emit, suppress=False)
        except Exception as e:  # e.g. missing permissions on Linux
            print(f"JarvisUI: global hotkey unavailable ({e})")

    def _on_fullscreen_app(self, is_fs: bool):
        # Hide the widget while a fullscreen game is in front
        if self._mode == "widget" and self._widget_win:
            self._widget_win.setVisible(not is_fs)

    def _toggle_mode(self):
        if self._mode == "widget":
            self._switch_to_fullscreen()
        else:
            self._switch_to_widget()

    def _switch_to_widget(self):
        if self._fullscreen_win:
            self._view.setParent(None)
            self._fullscreen_win.close()
            self._fullscreen_win = None
            self._log.hide()

        self._mode = "widget"
        self._widget_win = OrbWidget(self._view)
        self._widget_win.show()

    def _switch_to_fullscreen(self):
        if self._widget_win:
            self._view.setParent(None)
            self._widget_win.close()
            self._widget_win = None

        self._mode = "fullscreen"
        self._fullscreen_win = FullscreenWindow(
            self._jarvis, self._log, self._view, on_minimize=self._switch_to_widget,
        )

    def _shutdown(self):
        self._mic.stop()
        self._detector.stop()
        self._jarvis.stop()

    def run(self):
        sys.exit(self._app.exec())


def main():
    # QApplication must exist before any QWebEngineView is created
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    JarvisUIApp(app).run()


if __name__ == "__main__":
    main()
