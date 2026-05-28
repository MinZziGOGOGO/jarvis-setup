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
from PyQt6.QtCore import Qt, QTimer, QUrl, QPoint, QRect
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWebEngineWidgets import QWebEngineView

import keyboard

from config import (
    WIDGET_SIZE, WIDGET_OFFSET, FULLSCREEN_ORB_SIZE, FULLSCREEN_HOTKEY,
    LOG_TOGGLE_KEY, SKYLINE_WIDTH,
)
from bridge import OrbBridge
from mic_listener import MicListener
from jarvis_process import JarvisProcess
from window_detector import WindowDetector
from log_widget import LogWidget


# ── Windows API for click-through ──
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080


class OrbWidget(QWidget):
    """Small transparent click-through orb — the widget mode."""

    def __init__(self, bridge: OrbBridge, view: QWebEngineView):
        super().__init__()
        self._view = view
        self._bridge = bridge
        screen = QApplication.primaryScreen().availableGeometry()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(WIDGET_SIZE, WIDGET_SIZE)
        self.move(WIDGET_OFFSET, WIDGET_OFFSET)

        # Click-through on Windows
        if os.name == "nt":
            hwnd = int(self.winId())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW
            )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        view.setFixedSize(WIDGET_SIZE, WIDGET_SIZE)
        view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        layout.addWidget(view)

    def make_clickthrough(self, enable: bool = True):
        if os.name != "nt":
            return
        hwnd = int(self.winId())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if enable:
            style |= WS_EX_TRANSPARENT | WS_EX_LAYERED
        else:
            style &= ~(WS_EX_TRANSPARENT | WS_EX_LAYERED)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)


class FullscreenWindow(QMainWindow):
    """Fullscreen mode — larger orb + HUD controls + skyline."""

    def __init__(
        self, bridge: OrbBridge, jarvis: JarvisProcess,
        log_widget: LogWidget, view: QWebEngineView,
    ):
        super().__init__()
        self._bridge = bridge
        self._jarvis = jarvis
        self._log_widget = log_widget
        self._view = view

        self.setWindowTitle("JarvisUI")
        self.showFullScreen()
        self.setStyleSheet("background-color: #08000f;")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── Orb (centered) ──
        orb_size = FULLSCREEN_ORB_SIZE
        view.setFixedSize(orb_size, orb_size)
        layout.addWidget(view, alignment=Qt.AlignmentFlag.AlignCenter)

        # ── Skyline (bottom) ──
        self._skyline_label = QLabel()
        self._skyline_label.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._skyline_label, alignment=Qt.AlignmentFlag.AlignBottom)

        # Skyline frame cycling
        self._skyline_frames = []
        assets = Path(__file__).parent / "assets"
        for i in range(1, 11):
            p = assets / f"city_skyline_{i:02d}.png"
            if p.exists():
                self._skyline_frames.append(str(p))
        if not self._skyline_frames:
            base = assets / "city_skyline.png"
            if base.exists():
                self._skyline_frames = [str(base)]

        if self._skyline_frames:
            self._skyline_timer = QTimer()
            self._skyline_timer.timeout.connect(self._cycle_skyline)
            self._skyline_timer.start(500)
            self._update_skyline()
        else:
            self._skyline_timer = None

        # ── Top-right HUD panel ──
        self._hud = QWidget(self)
        self._hud.setStyleSheet("background: rgba(10, 0, 15, 0.8); border: 1px solid #9d00ff; border-radius: 4px;")
        hud_layout = QHBoxLayout(self._hud)
        hud_layout.setContentsMargins(8, 4, 8, 4)

        self._power_btn = QPushButton("●")
        self._power_btn.setFixedSize(28, 28)
        self._power_btn.setStyleSheet("QPushButton { color: #4caf50; background: transparent; border: none; font-size: 18px; }")
        self._power_btn.clicked.connect(self._toggle_jarvis)

        self._min_full_btn = QPushButton("▼")
        self._min_full_btn.setFixedSize(28, 28)
        self._min_full_btn.setStyleSheet("QPushButton { color: #00ffff; background: transparent; border: none; font-size: 14px; }")
        self._min_full_btn.clicked.connect(self._to_widget)

        hud_layout.addWidget(self._power_btn)
        hud_layout.addWidget(self._min_full_btn)
        self._hud.show()

    def showEvent(self, event):
        super().showEvent(event)
        # Position HUD top-right
        screen = self.screen().availableGeometry()
        self._hud.move(screen.width() - 100, 10)

    def _cycle_skyline(self):
        if self._skyline_timer:
            self._skyline_timer.setInterval(random.randint(200, 2000))

    def _update_skyline(self):
        if self._skyline_frames:
            pixmap = QPixmap(random.choice(self._skyline_frames))
            scaled = pixmap.scaledToWidth(self.width(), Qt.TransformationMode.SmoothTransformation)
            self._skyline_label.setPixmap(scaled)

    def _toggle_jarvis(self):
        # Toggle start/stop
        if hasattr(self._jarvis, '_proc') and self._jarvis._proc:
            self._jarvis.stop()
            self._power_btn.setStyleSheet("QPushButton { color: #ef5350; background: transparent; border: none; font-size: 18px; }")
        else:
            self._jarvis.start()
            self._power_btn.setStyleSheet("QPushButton { color: #4caf50; background: transparent; border: none; font-size: 18px; }")

    def _to_widget(self):
        # Signal to main app to switch to widget mode
        app = QApplication.instance()
        if hasattr(app, '_switch_to_widget'):
            app._switch_to_widget()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_skyline()


class JarvisUIApp:
    """Main app controller — manages mode switching and connects components."""

    def __init__(self):
        self._app = QApplication.instance() or QApplication(sys.argv)

        # Shared QWebEngineView (moved between windows)
        self._view = QWebEngineView()
        self._bridge = OrbBridge(self._view)

        # Audio
        self._mic = MicListener()
        self._mic.set_callback(self._on_mic_level)

        # Jarvis process
        self._jarvis = JarvisProcess(
            state_callback=self._on_state_change,
            log_callback=self._on_log_line,
        )

        # Fullscreen detector
        self._detector = WindowDetector(callback=self._on_fullscreen_change)

        # Log widget (shared — only shown in fullscreen mode)
        self._log = LogWidget()

        # Current mode
        self._mode = None  # "widget" | "fullscreen"
        self._widget_win = None
        self._fullscreen_win = None

        # Hotkeys
        keyboard.add_hotkey(FULLSCREEN_HOTKEY, self._toggle_mode, suppress=False)

        # Start
        self._mic.start()
        self._jarvis.start()
        self._detector.start()
        self._switch_to_widget()

        # Show widget
        self._widget_win.show()

    def _on_mic_level(self, level: float):
        self._bridge.update_mic_level(level)

    def _on_state_change(self, state: str):
        self._bridge.update_state(state)

    def _on_log_line(self, line: str):
        self._log.add_line(line)

    def _on_fullscreen_change(self, is_fs: bool):
        if self._mode == "widget":
            if is_fs:
                self._widget_win.hide()
            else:
                self._widget_win.show()

    def _toggle_mode(self):
        if self._mode == "widget":
            self._switch_to_fullscreen()
        else:
            self._switch_to_widget()

    def _switch_to_widget(self):
        if self._fullscreen_win:
            self._fullscreen_win.hide()
            self._fullscreen_win.close()
            self._fullscreen_win = None
            self._log.hide()

        self._mode = "widget"
        self._view.setParent(None)

        self._widget_win = OrbWidget(self._bridge, self._view)
        self._widget_win.show()

    def _switch_to_fullscreen(self):
        if self._widget_win:
            self._widget_win.hide()
            self._widget_win.close()
            self._widget_win = None

        self._mode = "fullscreen"
        self._view.setParent(None)

        self._fullscreen_win = FullscreenWindow(
            self._bridge, self._jarvis, self._log, self._view,
        )

        # Show log widget
        log_key_handler = lambda: self._log.setVisible(not self._log.isVisible())
        keyboard.add_hotkey(LOG_TOGGLE_KEY, log_key_handler, suppress=False)

        self._fullscreen_win.show()

    def run(self):
        # Re-register on app instance for mode switch from fullscreen
        self._app._switch_to_widget = self._switch_to_widget
        sys.exit(self._app.exec())


def main():
    app = QApplication(sys.argv)
    # Must create QApplication before WebEngine
    ui = JarvisUIApp()
    ui.run()


if __name__ == "__main__":
    main()
