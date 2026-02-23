# RFID Space Exhibit

A science museum interactive exhibit — "What to Take to Space?". Visitors scan physical RFID-tagged pucks (each representing an object like a sleeping bag, tortilla, or dumbbell) and the system plays a corresponding video explaining whether that object would be useful in space. After each video, a welcome/idle video loops automatically.

## How It Works

```
[RFID Puck]
     ↓ physical scan
[Arduino (MFRC522 reader)]
     ↓ USB HID keyboard emulation — sends "<numeric_NUID>\n"
[Raspberry Pi — video_player_vlc.py]
     ↓ reads stdin, looks up code in config.json, drives VLC
[Fullscreen display / TV]
```

The Arduino acts as a USB keyboard — no custom serial driver needed. The Python script reads stdin line-by-line and plays the corresponding video via VLC. After each video ends, the welcome/idle video resumes looping automatically.

Each physical puck has two scannable sides, so two RFID codes map to the same video.

## Fresh Raspberry Pi Setup

```bash
git clone https://github.com/jerusalem-science-museum/space-rfid-what-to-take.git
cd space-rfid-what-to-take
chmod +x setup.sh && ./setup.sh
```

The script installs system packages (Python, VLC, tmux), AnyDesk for remote access, creates the Python virtual environment, configures desktop auto-login, and registers the app to launch on boot.

After setup:
1. Set an AnyDesk unattended access password (open AnyDesk GUI → Security)
2. Reboot: `sudo reboot`

> **Note:** Video assets are not included in the repo (~2.2 GB). Copy the `data/` folder manually to the Pi before running. videos located [here](https://madaorgil-my.sharepoint.com/:f:/g/personal/ariels_mada_org_il/IgCJxbOUHLhDS7f8qEWn9AwRAbty9A36By976UAfQD9xBAA?e=UdKcoN)

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python video_player_vlc.py
```

## Runtime Commands

While the app is running, type directly into the terminal:

| Input | Action |
|-------|--------|
| Any RFID numeric code (e.g. `751`) | Plays the associated video |
| `new` | Calibration mode — register a new puck |
| `exit` | Gracefully shut down VLC and exit |

## Registering a New Puck

1. Type `new` and press Enter
2. Scan the puck — the RFID code is captured automatically
3. Choose the corresponding video file from the list
4. Optionally register the other side of the puck
5. Optionally add another puck

The mapping is saved to `config.json` immediately.

## config.json

Maps RFID codes to video filenames. Edit this file to change mappings or add new ones manually.

```json
{
    "metadata": { "data_folder": "data" },
    "welcome_video": "welcome.mp4",
    "751": "05-Tortilla.mp4",
    "4294956014": "03-Velcro roll.mp4"
}
```

- `data_folder` — folder containing the video files (relative to the repo root)
- `welcome_video` — the idle/looping video shown between scans
- All other keys are RFID codes pointing to video filenames

## Arduino

The firmware lives in `code arduino/ReadNUID_Amir_kb_3/`. It uses the MFRC522 library to read RFID tags over SPI and sends the UID as a decimal string via USB keyboard emulation (`Keyboard.println()`). A buzzer on pin 7 beeps for 200ms on each successful scan.

Wiring reference: see `doc/schematics/`.
