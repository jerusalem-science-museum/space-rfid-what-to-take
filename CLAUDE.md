# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A science museum interactive exhibit ("What to Take to Space?"). Visitors scan physical RFID-tagged pucks; the system plays a corresponding video, then loops back to a welcome/idle video. Deployed on a Raspberry Pi.

## Setup & Running

```bash
# First-time setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run (development)
source .venv/bin/activate
python video_player_vlc.py
```

Production uses `run.sh`, which activates the venv and launches the script. The RPi autostart uses tmux via `~/.bashrc` (see `useful commands.txt` for the exact snippet).

## Runtime Commands (typed into the running terminal)

- Any numeric RFID code (e.g., `751`) → plays associated video
- `new` → enters calibration mode to register a new puck
- `exit` → gracefully shuts down VLC and exits

## Architecture

Hardware-software pipeline:

```
[RFID Puck]
     ↓ physical scan
[Arduino (MFRC522 reader)]
     ↓ USB HID keyboard emulation — sends "<numeric_NUID>\n"
[Raspberry Pi — video_player_vlc.py]
     ↓ reads stdin, looks up code in config.json, drives VLC
[Fullscreen display / TV]
```

The Arduino acts as a USB keyboard — no custom serial driver needed. The Python script reads stdin line-by-line; an RFID scan is indistinguishable from an operator typing the code.

## Key Files

- **`video_player_vlc.py`** — entire Python application (~137 lines). Manages VLC lifecycle, maps RFID codes to videos, handles calibration flow.
- **`config.json`** — runtime config: `data_folder`, `inactivity_timeout` (currently unused), `welcome_video` filename, and RFID-code-to-video-filename mappings. Mutated in-place by the `new` calibration flow.
- **`code arduino/ReadNUID_Amir_kb_3/ReadNUID_Amir_kb_3.ino`** — Arduino firmware using MFRC522 library. Converts 4-byte UID to a `uint32_t` decimal string and sends it via `Keyboard.println()`. Buzzer on pin 7, RST=9, SS=10, SPI on pins 11/12/13.

## config.json Structure

```json
{
    "metadata": { "data_folder": "data", "inactivity_timeout": 2 },
    "welcome_video": "welcome.mp4",
    "<rfid_code>": "<VideoFilename>.mp4"
}
```

Each physical puck has two sides → two RFID codes mapping to the same video is the expected pattern.

## VLC Playback Design

- Welcome video loops infinitely via VLC's `input-repeat=-1` option.
- When an exhibit video ends, a `MediaPlayerEndReached` event fires and schedules `_play_welcome_loop()` via a 50ms `threading.Timer` (VLC callbacks cannot call VLC directly).
- VLC runs fullscreen with no window title bar.

## Deployment Notes

- Video assets live in `data/` (gitignored, ~2.2 GB). Must be copied manually to each deployment.
- No test suite exists.
- `inactivity_timeout` in `config.json` is loaded but not currently used in the Python code.
