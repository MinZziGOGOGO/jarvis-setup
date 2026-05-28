# JarvisUI

A floating holographic orb desktop overlay for the [Jarvis AI assistant](https://github.com/isair/jarvis), built with PyQt6 + Three.js.

## What It Does

JarvisUI renders a glowing purple/pink point-cloud orb that reacts in real-time to Jarvis's state and your microphone:

- **idle** — slow drifting orb, dim glow
- **listening** — orb shrinks, waiting for speech
- **thinking** — points flicker randomly, processing
- **speaking** — orb expands with bloom-like radiance

The mic level directly affects point drift speed and connection brightness — quiet speech is subtle, loud speech is dramatic.

## How to Launch

### From Windows (autostart)
The app auto-starts with Windows via registry. Reboot and it's there.

### Manually
```
C:\tools\jarvis\start_jarvis_ui.bat
```
or
```
C:\tools\jarvis\.venv\Scripts\python.exe C:\tools\jarvis\jarvis_ui\main.py
```

## Hotkeys

| Key | Action |
|-----|--------|
| `Ctrl+Shift+J` | Toggle between widget mode and fullscreen mode |
| `L` | Toggle log panel in fullscreen mode |

## Modes

### Widget Mode (default)
A small 100×100px transparent orb in the top-left corner. Completely click-through — you can interact with anything behind it. Auto-hides when a fullscreen game is detected.

### Fullscreen Mode
The orb expands to fill the screen. Shows:
- **Power button** (green circle) — starts/stops Jarvis to free VRAM
- **Minimize button** (▼) — returns to widget mode
- **City skyline** — animated window lights at the bottom
- **Log panel** — toggle with `L` key

## Autostart

Registered at `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\JarvisUI`.

### To disable autostart:
```
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v JarvisUI /f
```

## Files

```
jarvis_ui/
  main.py              — Entry point, dual-mode app
  orb.html             — Three.js point cloud scene
  bridge.py            — Python→JS bridge (runJavaScript)
  mic_listener.py      — Real-time microphone levels
  jarvis_process.py    — Jarvis subprocess manager
  window_detector.py   — Fullscreen game detection
  log_widget.py        — Floating log with typewriter reveal
  config.py            — All constants and settings
  generate_skyline.py  — City skyline asset generator
  assets/              — Pre-rendered skyline PNGs
  start_jarvis_ui.bat  — Windows launcher
```
