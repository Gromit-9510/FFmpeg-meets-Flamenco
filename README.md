# FFmpeg Encoder v2.0

**Author:** Insoo Chang (insu9510@gmail.com)  
**GitHub:** https://github.com/Gromit-9510/FFmpeg-meets-Flamenco  
**License:** LGPL 3.0+ (Non-commercial use only)

A powerful Windows desktop FFmpeg encoding tool with queue management, presets, logging, and Flamenco distributed processing integration.

# I don’t understand a single line of the code I created

## Features

### 🎥 Video Encoding
- **Multiple Codecs**: H.264, H.265, VP9, AV1, ProRes, DNxHD
- **GPU Acceleration**: NVENC, QSV, AMF, VAAPI support
- **Low Latency**: Optimized encoding for streaming
- **Quality Control**: CRF, QP, bitrate settings
- **2-Pass Encoding**: For optimal quality/size ratio

### 📁 Queue Management
- Add single files, folders, or multiple files
- Real-time progress monitoring
- Remove items from queue
- Batch processing support

### ⚙️ Advanced Features
- **Preset System**: Save/load encoding presets
- **Batch Renaming**: Pattern-based and Excel mapping
- **Flamenco Integration**: Distributed encoding across multiple machines
- **Live Logging**: Real-time FFmpeg command preview and progress
- **Auto-save Settings**: Flamenco configuration persistence

### 🎵 Audio & Subtitles
- Multiple audio codecs (AAC, MP3, Opus, etc.)
- Subtitle processing and embedding
- Custom FFmpeg parameters

## Dev Requirements
- Python 3.10+
- FFmpeg available on PATH (the app also checks and can use a configured path)

## Run
```bash
python -m ffmpeg_encoder.app
```

## Build (Windows EXE)
We use PyInstaller with a spec file for better control.
```bash
# Install dependencies
py -m pip install -U pip
py -m pip install -e .
py -m pip install pyinstaller

# Build using spec file
py -m PyInstaller build.spec
```
The executable will be `dist/FFmpegEncoder_v2.exe` (~51MB).

### Build Configuration
The `build.spec` file contains all PyInstaller configuration:
- Includes all necessary data files and dependencies
- Optimized for single-file executable
- Includes FFmpeg integration files
- Configured for Windows platform

## Quick Start
```bash
# Run from Python
python -m ffmpeg_encoder.app

# Or run executable
dist\FFmpegEncoder_v2.exe

# Or use launcher
run_ffmpeg_encoder.bat
```

## Packaging
- Project metadata is in `pyproject.toml`.
- App entrypoint: `ffmpeg_encoder/app.py:main`.

## Installation

### Pre-built Executable (Recommended)
1. Download the latest release from [GitHub Releases](https://github.com/Gromit-9510/FFmpeg-meets-Flamenco/releases)
2. Extract and run `FFmpegEncoder_v2.exe`
3. Ensure FFmpeg is installed and available on your system PATH

### From Source
```bash
git clone https://github.com/Gromit-9510/FFmpeg-meets-Flamenco.git
cd FFmpeg-meets-Flamenco
pip install -e .
python -m ffmpeg_encoder.app
```

## Usage

1. **Add Files**: Use "Add Files/Folders" or drag & drop video files
2. **Configure Settings**: Choose codec, quality, and other encoding options
3. **Save Presets**: Save frequently used settings as presets
4. **Flamenco Setup**: Configure Flamenco for distributed encoding
5. **Start Encoding**: Click "Start Encoding" for local processing or "Submit to Flamenco" for distributed processing

## Flamenco Integration

This application integrates with [Flamenco](https://flamenco.blender.org/) for distributed video encoding:

1. Install and configure Flamenco Manager
2. Set up Flamenco Workers on your network
3. Configure Flamenco settings in the app
4. Submit encoding jobs to be processed across multiple machines

## License

This project is licensed under the GNU Lesser General Public License v3.0 or later with commercial use restrictions. See [LICENSE](LICENSE) for details.

**Commercial Use**: This software is free for non-commercial use. Commercial use requires explicit permission from the author. Contact: insu9510@gmail.com

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## Support

For support, feature requests, or bug reports, please open an issue on GitHub or contact the author at insu9510@gmail.com.

## Acknowledgments

- Built with [PySide6](https://doc.qt.io/qtforpython/) for the GUI
- Uses [FFmpeg](https://ffmpeg.org/) for video processing
- Integrates with [Flamenco](https://flamenco.blender.org/) for distributed processing
