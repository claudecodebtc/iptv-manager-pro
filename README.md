# IPTV Manager Pro

Desktop application for downloading, editing, reviewing and playing M3U/IPTV playlists.

## Features

- Download IPTV playlists from a provider URL
- Load and edit local `.m3u` files
- Remove channels or whole groups
- Add PIN metadata to channels or groups
- Search channels live
- Detect duplicate channels across groups
- Import URLs from text files
- Save imported URLs as M3U playlists
- Embedded mini video player in the edit tab (via `python-vlc`)
- Multi-language UI: English, Romanian, German, Spanish

## Requirements

- Python 3.10+
- VLC Media Player installed locally
- Python packages from `requirements.txt`

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
python gui.py
```

## VLC Path

The app tries to auto-detect VLC.  
You can also override it with an environment variable:

```bash
IPTV_MANAGER_VLC_PATH=/path/to/vlc
```

Windows PowerShell:

```powershell
$env:IPTV_MANAGER_VLC_PATH="C:\Program Files\VideoLAN\VLC\vlc.exe"
python gui.py
```

## Building

If you want to build a Windows executable with PyInstaller:

```bash
pip install pyinstaller
pyinstaller gui.spec
```

## Open Source Notes

- No private IPTV credentials should be committed.
- Example placeholder values are used in the UI by default.
- Provider URLs, usernames and passwords should be entered locally by each user.

## Disclaimer

This project is a generic playlist manager/player.  
Use it only with content and services you are authorized to access.

## Donations

If you want to support the project, you can use this BTC address:

`1H15oBFdpHZJggMYf9gsMcdXeFjkdT5QU6`

## License

MIT
