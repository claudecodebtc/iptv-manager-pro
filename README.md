# IPTV Manager Pro

Desktop application for downloading, editing, reviewing and playing M3U/IPTV playlists from a single interface.

## Highlights

- Download playlists directly from provider URLs
- Load and edit local `.m3u` files
- Remove channels or full groups before export
- Add PIN metadata to selected channels or entire groups
- Search channels live while browsing loaded data
- Detect duplicate channels across groups
- Import URLs from text files and classify M3U vs direct streams
- Save imported URLs as local M3U playlists
- Play direct streams or grouped playlists through VLC
- Built-in mini preview area plus VLC integration
- Multi-language UI: English, Romanian, German, Spanish

## Tech Stack

- Python 3.10+
- Tkinter GUI
- `requests`
- `python-vlc`
- VLC Media Player installed locally

## Quick Start

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python gui.py
```

### Linux or macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python gui.py
```

## Requirements

- Python 3.10 or newer
- VLC Media Player available on the system
- Internet connection for downloading remote playlists

## VLC Configuration

The app tries to auto-detect VLC in common install paths.

If detection fails, set the executable path manually through the `IPTV_MANAGER_VLC_PATH` environment variable.

Example on Windows PowerShell:

```powershell
$env:IPTV_MANAGER_VLC_PATH="C:\Program Files\VideoLAN\VLC\vlc.exe"
python gui.py
```

Example on Linux or macOS:

```bash
export IPTV_MANAGER_VLC_PATH=/path/to/vlc
python3 gui.py
```

## Main Workflows

### 1. Download a provider playlist

- Open the download section
- Paste the full provider URL
- Save the downloaded `.m3u` file locally

### 2. Edit an existing M3U file

- Load a local `.m3u` file
- Browse groups and channels
- Remove channels or groups you do not want
- Add PIN metadata where needed
- Export the updated file

### 3. Import URLs from text files

- Load a `.txt` file with one URL per line
- Review detected M3U playlist links and direct stream links
- Save the detected M3U URLs as local playlists
- Send a direct stream or grouped playlist to VLC

## Build a Windows Executable

The repository includes a PyInstaller spec file.

```powershell
pip install pyinstaller
python -m PyInstaller gui.spec --clean
```

The generated Windows executable is created at `dist/gui.exe`.

This build uses the bundled spec and opens as a normal desktop app without a console window.

To prepare a GitHub Release archive:

```powershell
Compress-Archive -Path dist\gui.exe -DestinationPath dist\IPTV-Manager-Pro-windows.zip -Force
```

## Releases

For GitHub Releases, attach either:

- `dist/gui.exe`
- `dist/IPTV-Manager-Pro-windows.zip`

Suggested first release title:

`IPTV Manager Pro v0.1.0`

Suggested release notes template:

- First public release
- M3U download, edit and export workflows
- URL import from text files
- Duplicate channel detection
- VLC playback integration
- Multi-language interface

## Screenshots

Recommended screenshots and naming guidance are documented in `docs/screenshots/README.md`.

## Project Structure

```text
gui.py             Main Tkinter application
config.py          Theme, fonts and VLC path detection
i18n.py            UI translations
m3u_utils.py       M3U loading, editing and export helpers
m3u_processor.py   M3U writing helpers
url_manager.py     URL import and export helpers
vlc_manager.py     VLC launch and playback integration
gui.spec           PyInstaller build configuration
docs/              GitHub/release support files
```

## Known Limitations

- VLC must be installed separately for full playback integration
- Some providers use formats or tags that may need custom handling
- Playback reliability depends on the remote stream and local VLC setup
- The packaged executable is Windows-oriented via the current `gui.spec`
- No credentials or provider-specific secrets should be committed to the repository

## Security and Privacy

- Do not commit provider usernames, passwords or private playlist URLs
- Use placeholder values in screenshots or demos
- Keep personal IPTV subscription data local to your machine

## Roadmap Ideas

- Prebuilt GitHub Releases for Windows
- Better validation for malformed playlists
- Drag-and-drop file loading
- More playlist cleanup and filtering tools
- Optional dark/light theme presets exposed in settings

## Support

If you want to support development of this project, you can use this BTC address:

`1H15oBFdpHZJggMYf9gsMcdXeFjkdT5QU6`

Support is optional and does not grant access to any IPTV service, playlist, subscription or private content.

## License

MIT. See [LICENSE](LICENSE).

## Disclaimer

This is a generic playlist manager and player. Use it only with content and services you are authorized to access.
