#!/usr/bin/env bash
cd "$(dirname "${BASH_SOURCE[0]}")"
source .venv/bin/activate
python video_player_vlc.py
