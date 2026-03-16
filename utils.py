"""Utility functions and constants."""

import os
from datetime import datetime
from paths import get_app_data_dir, ensure_app_dir

# Use absolute path so log file is always in the script directory
LOG_FILE = os.path.join(get_app_data_dir(), "activity.log")

# Color palettes
COOL_BG = "#f4f7f9"
COOL_CARD = "#ffffff"
COOL_TEXT = "#2c3e50"

WARM_BG = "#fff2e6"
WARM_CARD = "#ffffff"
WARM_TEXT = "#5e4b3c"

DARK_BG = "#1a252f"
DARK_CARD = "#243441"
DARK_TEXT = "#e1e8ed"

ACCENT_MINT = "#b2d8d8"
ACCENT_PEACH = "#ffd3b6"
ACCENT_SALMON = "#ffaaa5"
ACCENT_LAVENDER = "#c3bedd"

DARK_ACCENT_ACTIVE = "#3a6b5c"
DARK_ACCENT_INACTIVE = "#6b4f6f"
DARK_ACCENT_SELECT = "#2b5797"


def log_action(message: str):
    """Write a timestamped message to the log file."""
    ensure_app_dir()  # make sure directory exists
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"Error writing log: {e}")