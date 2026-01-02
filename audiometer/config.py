"""Simple preferences persistence for Audiometer UI.

Stores a small JSON file with keys like 'theme', 'win_focus', 'high_contrast'.
The configuration directory can be overridden via the environment variable
`AUDIO_METER_CONFIG_DIR` for testing or portability.
"""
from pathlib import Path
import json
import os

DEFAULT_PREFS = {
    "theme": "darkly",
    "win_focus": True,
    "high_contrast": False,
}

_CONFIG_FILENAME = "config.json"


def get_config_dir() -> Path:
    env = os.environ.get('AUDIO_METER_CONFIG_DIR')
    if env:
        return Path(env)
    if os.name == 'nt':
        appdata = os.environ.get('APPDATA') or Path.home()
        return Path(appdata) / 'audiometer'
    else:
        return Path.home() / '.config' / 'audiometer'


def get_config_path() -> Path:
    d = get_config_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / _CONFIG_FILENAME


def load_prefs() -> dict:
    path = get_config_path()
    if not path.exists():
        return dict(DEFAULT_PREFS)
    try:
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)
            # Merge with defaults for missing keys
            prefs = dict(DEFAULT_PREFS)
            prefs.update(data or {})
            return prefs
    except Exception:
        # If corrupt or unreadable, return defaults
        return dict(DEFAULT_PREFS)


def save_prefs(prefs: dict) -> None:
    path = get_config_path()
    with path.open('w', encoding='utf-8') as f:
        json.dump(prefs, f, indent=2)
