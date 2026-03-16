"""Configuration manager for loading/saving settings."""

import os
import json
from browser_search import BrowserSearch
from utils import log_action
from paths import get_app_data_dir, ensure_app_dir

class ConfigManager:
    """Manages application configuration (search sources, theme)."""

    CONFIG_FILE = os.path.join(get_app_data_dir(), "config.json")

    @classmethod
    def load(cls):
        """Load config from JSON file. Returns dict with defaults."""
        default_sources = {source: (source == 'google') for source in BrowserSearch.get_source_names()}
        default = {
            "search_sources": default_sources,
            "theme": "dark"
        }
        ensure_app_dir()
        if os.path.exists(cls.CONFIG_FILE):
            try:
                with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if "search_sources" in loaded:
                        sources = default["search_sources"].copy()
                        sources.update(loaded["search_sources"])
                        loaded["search_sources"] = sources
                    else:
                        loaded["search_sources"] = default["search_sources"]
                    if "theme" not in loaded:
                        loaded["theme"] = default["theme"]
                    return loaded
            except Exception:
                return default
        return default

    @classmethod
    def save(cls, config):
        """Save config to JSON file."""
        ensure_app_dir()
        try:
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            log_action(f"Error saving config: {e}")