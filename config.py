import os
from pathlib import Path
from shutil import which


def _detect_vlc_path():
    env_path = os.getenv("IPTV_MANAGER_VLC_PATH", "").strip()
    if env_path:
        return env_path

    vlc_in_path = which("vlc")
    if vlc_in_path:
        return vlc_in_path

    candidates = [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        "/usr/bin/vlc",
        "/snap/bin/vlc",
        "/Applications/VLC.app/Contents/MacOS/VLC",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return ""


VLC_PATH = _detect_vlc_path()

THEME_PRESETS = {
    "Ocean": {
        "bg": "#0f1720",
        "fg": "#e9f2ef",
        "muted_fg": "#9eb7b0",
        "btn_bg": "#214039",
        "btn_active": "#2d7f6d",
        "tab_bg": "#18242e",
        "tree_bg": "#13202a",
        "title_bg": "#1b5e52",
    },
    "Graphite": {
        "bg": "#18181b",
        "fg": "#f4f4f5",
        "muted_fg": "#a1a1aa",
        "btn_bg": "#2a2a31",
        "btn_active": "#4b5563",
        "tab_bg": "#222228",
        "tree_bg": "#1f1f24",
        "title_bg": "#3f3f46",
    },
    "Sand": {
        "bg": "#f3efe6",
        "fg": "#2a241d",
        "muted_fg": "#6f675d",
        "btn_bg": "#d5c3a6",
        "btn_active": "#c6a57a",
        "tab_bg": "#e7ddcd",
        "tree_bg": "#e0d3bf",
        "title_bg": "#b68b59",
    },
}

ACTIVE_THEME = "Ocean"
THEME = THEME_PRESETS.get(ACTIVE_THEME, THEME_PRESETS["Ocean"]).copy()

FONTS = {
    "title": "Bahnschrift SemiBold",
    "ui": "Segoe UI",
    "mono": "Consolas",
}
