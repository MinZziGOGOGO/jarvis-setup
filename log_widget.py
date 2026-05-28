"""
Floating log window with hacker-style typewriter text reveal.
"""
from PyQt6.QtWidgets import (
    QWidget, QTextEdit, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QPoint, QRect
from PyQt6.QtGui import QTextCharFormat, QColor, QFont, QFontDatabase

from config import (
    LOG_WIDGET_WIDTH, LOG_WIDGET_HEIGHT, CHAR_REVEAL_DELAY_MS,
    MAX_LOG_LINES, HACKER_FONT,
)


class LogWidget(QWidget):
    """Frameless draggable log window with typewriter reveal."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(LOG_WIDGET_WIDTH, LOG_WIDGET_HEIGHT)
        self.setStyleSheet("""
            LogWidget {
                background-color: #0a0009;
                border: 1px solid #9d00ff;
            }
        """)

        # ── Font ──
        font = QFont(HACKER_FONT, 10)
        font.setStyleHint(QFont.StyleHint.Monospace)

        self._title_font = QFont(HACKER_FONT, 12, QFont.Weight.Bold)
        self._title_font.setStyleHint(QFont.StyleHint.Monospace)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        # ── Title bar ──
        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("background-color: #0a0009;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(8, 0, 8, 0)

        self._title_label = QLabel("LOG")
        self._title_label.setFont(self._title_font)
        self._title_label.setStyleSheet("color: #00ffff; background: transparent;")

        self._minimize_btn = QPushButton("−")
        self._minimize_btn.setFixedSize(24, 24)
        self._minimize_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #00ffff; border: none;
                font-size: 16px; font-weight: bold;
            }
            QPushButton:hover { color: #ff2d9b; }
        """)
        self._minimize_btn.clicked.connect(self._toggle_minimize)

        title_layout.addWidget(self._title_label)
        title_layout.addStretch()
        title_layout.addWidget(self._minimize_btn)

        layout.addWidget(title_bar)

        # ── Log text area ──
        self._log_edit = QTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setFont(font)
        self._log_edit.setStyleSheet("""
            QTextEdit {
                background-color: #050005;
                color: #00ffff;
                border: none;
                padding: 4px;
            }
        """)
        layout.addWidget(self._log_edit)

        # ── Typewriter state ──
        self._line_queue = []
        self._active = False
        self._current_line = ""
        self._char_index = 0
        self._type_timer = QTimer()
        self._type_timer.timeout.connect(self._reveal_char)

        self._minimized = False
        self._normal_pos = None
        self._anim = None

        self._drag_offset = None

    # ── Dragging ──
    def mousePressEvent(self, event):
        if event.position().y() < 30:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self._drag_offset and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None

    # ── Minimize animation ──
    def _toggle_minimize(self):
        screen = self.screen().availableGeometry()
        if self._minimized:
            # Slide in
            target = QPoint(0, self._normal_pos.y() if self._normal_pos else 100)
            self._minimized = False
            self._minimize_btn.setText("−")
        else:
            # Slide out (left off-screen)
            self._normal_pos = self.pos()
            target = QPoint(-LOG_WIDGET_WIDTH, self._normal_pos.y())
            self._minimized = True
            self._minimize_btn.setText("+")
        self._animate_pos(target)

    def _animate_pos(self, target: QPoint):
        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(300)
        self._anim.setStartValue(self.pos())
        self._anim.setEndValue(target)
        self._anim.start()

    # ── Log line API ──
    def add_line(self, text: str):
        """Queue a line for typewriter reveal."""
        self._line_queue.append(text)
        if not self._active:
            self._process_next()

    def _process_next(self):
        if not self._line_queue:
            self._active = False
            return
        self._active = True
        self._current_line = self._line_queue.pop(0)
        self._char_index = 0
        self._type_timer.start(CHAR_REVEAL_DELAY_MS)

    def _reveal_char(self):
        if self._char_index < len(self._current_line):
            self._char_index += 1
            partial = self._current_line[:self._char_index]
            # Update the last block
            cursor = self._log_edit.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            # Remove last line if we overwrote it (replace ongoing line)
            doc = self._log_edit.document()
            if doc.blockCount() > 0:
                last_block = doc.findBlockByNumber(doc.blockCount() - 1)
                cursor.setPosition(last_block.position())
                cursor.movePosition(
                    cursor.MoveOperation.End, cursor.MoveMode.KeepAnchor
                )
                cursor.removeSelectedText()

            # Write with color
            fmt = self._color_for_line(self._current_line)
            cursor.insertText(partial, fmt)
        else:
            self._type_timer.stop()
            # Append complete line with newline
            fmt = self._color_for_line(self._current_line)
            self._log_edit.setCurrentCharFormat(fmt)
            self._log_edit.append(self._current_line)

            # Trim old lines
            doc = self._log_edit.document()
            while doc.blockCount() > MAX_LOG_LINES:
                first_block = doc.findBlockByNumber(0)
                cursor = self._log_edit.textCursor()
                cursor.setPosition(first_block.position())
                cursor.movePosition(
                    cursor.MoveOperation.NextBlock, cursor.MoveMode.KeepAnchor
                )
                cursor.removeSelectedText()

            self._process_next()

    def _color_for_line(self, line: str) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setFont(QFont(HACKER_FONT, 10))

        if "error" in line.lower():
            fmt.setForeground(QColor("#ef5350"))
        elif "Heard" in line:
            fmt.setForeground(QColor("#4fc3f7"))
        elif "Working on" in line:
            fmt.setForeground(QColor("#ffb74d"))
        elif "→" in line:
            fmt.setForeground(QColor("#ce93d8"))
        elif line.startswith("🤖"):
            fmt.setForeground(QColor("#81c784"))
        else:
            fmt.setForeground(QColor("#00ffff"))
        return fmt
