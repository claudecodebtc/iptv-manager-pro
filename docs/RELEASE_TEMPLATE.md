# Release Template

## Suggested Tag

`v0.1.0`

## Suggested Title

`IPTV Manager Pro v0.1.0`

## Release Notes

First public release of IPTV Manager Pro.

Included in this release:

- Download playlists from provider URLs
- Load, inspect and edit local M3U files
- Remove channels or groups before export
- Apply PIN metadata to channels or groups
- Import URLs from text files
- Detect duplicate channels across groups
- Launch direct streams and playlists through VLC
- Multi-language interface: English, Romanian, German, Spanish

## Assets to Upload

- `dist/gui.exe`

## Pre-Publish Checklist

- Confirm `gui.exe` starts on a clean Windows machine
- Confirm VLC path detection works or document the environment variable override
- Confirm the README reflects the current feature set
- Confirm no private playlist URLs or credentials are included anywhere in the repository
