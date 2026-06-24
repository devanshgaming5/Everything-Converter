# OmniConvert

## Download

Download the ready-to-run Windows executable from this repository's
[Releases](https://github.com/devanshgaming5/Everything-Converter/releases).
No Python or FFmpeg installation is required.

## Build a standalone Windows executable

1. Put a Windows FFmpeg binary at `bin\ffmpeg.exe`.
2. Install the build dependencies:

   ```powershell
   python -m venv .venv-build
   .\.venv-build\Scripts\python.exe -m pip install -r requirements.txt
   ```

3. Build:

   ```powershell
   .\build_exe.ps1
   ```

The portable executable is created at `converter.exe` in the project root. Python, Pillow,
CustomTkinter, ffmpeg-python, yt-dlp, and FFmpeg are bundled into that file. Users do
not need to install those dependencies.

The YouTube downloader is intended for videos you own or have permission to
download. Availability can depend on YouTube changes, network access, and the
version of yt-dlp bundled into the executable.

Settings and conversion history are stored in
`%LOCALAPPDATA%\OmniConvert\omni_config.json`, so the executable can run from
read-only folders.

## Distribution note

FFmpeg has its own license obligations. Include the notices and corresponding
license/source information required by the particular FFmpeg build you choose
to distribute.
