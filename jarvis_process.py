"""
isair / jarvis subprocess manager.

Starts the external isair or jarvis CLI process, streams its stdout/stderr,
and parses structured output (e.g. transcribed speech, command results)
for display in the UI and log widget.
"""

import os
import subprocess
import threading
import time

from config import (
    JARVIS_PATH,
    PYTHON_EXE,
    RESTART_DELAY_SEC,
    STATE_SPEAKING_DURATION_SEC,
)

# Robot emoji bytes: UTF-8 encoding of U+1F916
_ROBOT_EMOJI_BYTES = "\U0001f916".encode("utf-8")


class JarvisProcess:
    """Manages an isair/jarvis subprocess — starts, monitors stdout for state
    changes, emits parsed states and raw log lines via callbacks, and auto-
    restarts on unexpected exit."""

    def __init__(self, state_callback, log_callback):
        """*state_callback* receives state strings (listening / thinking /
        speaking / idle / crashed).  *log_callback* receives raw log lines."""
        self._state_callback = state_callback
        self._log_callback = log_callback
        self._proc = None          # subprocess.Popen handle
        self._reader_thread = None # background stdout reader
        self._speaking_timer = None
        self._running = False      # True while start() has been called
        self._restart_count = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        """True between start() and stop() (including automatic restarts)."""
        return self._running

    def start(self):
        """Launch the subprocess and begin reading its stdout.

        Safe to call multiple times — subsequent calls are no-ops if the
        process is already alive."""
        if self._running:
            return
        self._running = True
        self._launch()

    def stop(self):
        """Kill the subprocess tree cleanly and stop the reader thread.

        Does not trigger auto-restart (clean shutdown)."""
        self._running = False
        self._cancel_timers()
        p = self._proc
        if p is not None and p.poll() is None:
            try:
                p.terminate()
            except OSError:
                pass
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    p.kill()
                    p.wait(timeout=5)
                except (OSError, subprocess.TimeoutExpired):
                    pass
        self._proc = None
        self._set_state("idle")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _launch(self):
        """Start the subprocess and the stdout reader thread."""
        cmd = [PYTHON_EXE, "-m", "src.jarvis.main"]
        env = {**os.environ, "PYTHONPATH": os.path.join(JARVIS_PATH, "src")}
        try:
            self._proc = subprocess.Popen(
                cmd,
                cwd=JARVIS_PATH,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except Exception as e:
            self._log_callback(f"error: could not start Jarvis ({e})")
            self._schedule_restart()
            return

        self._reader_thread = threading.Thread(
            target=self._read_loop, daemon=True
        )
        self._reader_thread.start()

    def _read_loop(self):
        """Read stdout line by line, emit callbacks, detect exit."""
        try:
            for line in self._proc.stdout:
                line = line.rstrip("\n\r")
                self._log_callback(line)
                self._parse_state(line)
        except Exception:
            pass  # stream closed / encoding error
        finally:
            # Process exited — check if unexpected
            if self._running and self._proc is not None:
                self._proc.wait()
                self._cancel_timers()
                self._schedule_restart()

    def _parse_state(self, line: str):
        """Inspect a single line and emit state changes via state_callback."""
        # Order matters: "Heard:" / "Working on" / "Listening!" are simple
        # substrings; robot emoji is checked by raw bytes on the encoded line.
        if "Heard:" in line:
            self._set_state("listening")
        elif "Working on" in line:
            self._set_state("thinking")
        elif line.encode("utf-8").startswith(_ROBOT_EMOJI_BYTES) or "Jarvis:" in line:
            self._set_state("speaking")
            self._schedule_speaking_timeout()
        elif "Listening!" in line:
            self._set_state("idle")

    def _set_state(self, state: str):
        """Emit a state change through the callback."""
        try:
            self._state_callback(state)
        except Exception:
            pass

    def _cancel_timers(self):
        if self._speaking_timer is not None:
            self._speaking_timer.cancel()
            self._speaking_timer = None

    def _schedule_speaking_timeout(self):
        self._cancel_timers()
        self._speaking_timer = threading.Timer(
            STATE_SPEAKING_DURATION_SEC, lambda: self._set_state("idle")
        )
        self._speaking_timer.daemon = True
        self._speaking_timer.start()

    def _schedule_restart(self):
        """Auto-restart after RESTART_DELAY_SEC if still supposed to be running."""
        if not self._running:
            return
        self._restart_count += 1
        self._set_state("crashed")
        t = threading.Thread(target=self._delayed_restart, daemon=True)
        t.start()

    def _delayed_restart(self):
        time.sleep(RESTART_DELAY_SEC)
        if self._running:
            self._launch()
