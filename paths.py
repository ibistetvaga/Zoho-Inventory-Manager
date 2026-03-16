"""Centralized path management for the application."""

import os
import platform

APP_NAME = "InventoryManager"

def get_app_data_dir():
    """Return platform-specific application data directory."""
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(base, APP_NAME)
    elif system == "Darwin":  # macOS
        base = os.path.expanduser("~/Library/Application Support")
        return os.path.join(base, APP_NAME)
    else:  # Linux and others
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        return os.path.join(base, APP_NAME)

def ensure_app_dir():
    """Create the application data directory if it doesn't exist."""
    path = get_app_data_dir()
    os.makedirs(path, exist_ok=True)
    return path