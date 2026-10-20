# pyspine

A tiny webcam app that watches your posture and yells at you when you slouch.

It looks at your nose and shoulders through MediaPipe, remembers what "sitting up straight" looks like, and pings you with a desktop notification if you start sinking into your chair.

## Setup

```bash
uv sync
```

## Run it

```bash
uv run spine.py
```

A window opens with your camera feed. If you haven't calibrated yet, it'll tell you to press `c`.

## Keys

| Key | What it does                               |
| --- | ------------------------------------------ |
| `c` | Calibrate — sit up straight for ~2 seconds |
| `q` | Quit                                       |

## How it works

- It measures the vertical gap between your nose and the midpoint of your shoulders.
- Press `c`, sit up straight, and it averages a couple seconds of frames into your baseline. That baseline is saved to `baseline.json`, so next launch it already knows your good posture.
- If your nose gets 5% closer to your shoulders than the baseline, that counts as slouching.
- Slouch for 10 seconds straight and you get a notification. After that it stays quiet for a minute so it doesn't spam you.
- Sitting up (or leaving the frame) resets the slouch timer.

Want it more or less aggressive? Tweak the constants at the top of `spine.py`:

```python
TOLERANCE = 0.05          # smaller = stricter posture
BAD_SECONDS = 10          # how long you can slouch before the alert
NOTIFY_COOLDOWN = 60      # seconds between alerts
CALIBRATION_SECONDS = 2   # calibration duration

```
