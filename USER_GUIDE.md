# FFmpeg Encoder - User Guide

## 🚀 Quick Start

### Running the Application
```bash
# Install dependencies (if not already done)
py -m pip install -e .

# Run the application
python -m ffmpeg_encoder.app
```

### Building Windows EXE
```bash
# Build executable
python build_exe.py

# The executable will be in dist/FFmpegEncoder/
```

## 📋 Features Overview

### 1. **Queue Management**
- **Add Files**: Click "Add Files" to select individual video files
- **Add Folder**: Click "Add Folder" to add all video files from a directory
- **Remove**: Select items and click "Remove Selected"
- **Batch Rename**: Click "Batch Rename" for advanced renaming options

### 2. **Encoding Settings**

#### Video Tab
- **Container**: Choose output format (MP4, MKV, MOV, AVI, WebM)
- **Video Codec**: Select from available encoders (auto-detected)
- **CRF**: Constant Rate Factor (0-51, lower = better quality)
- **Bitrate**: Target bitrate (e.g., "8M", "2000k")
- **Two-pass**: Enable for better quality encoding
- **GPU**: Use hardware acceleration when available

#### Audio Tab
- **Audio Codec**: Select audio encoder (AAC, MP3, Opus, etc.)
- **Audio Bitrate**: Target audio bitrate (e.g., "192k")

#### Advanced Tab
- **Max File Size**: Limit output file size (e.g., "700M")
- **Extra Params**: Additional FFmpeg parameters

### 3. **Preset Management**
- **Save Preset**: Enter name and click "Save Preset"
- **Load Preset**: Enter name and click "Load Preset"
- **Import/Export**: Use File menu for JSON preset sharing

### 4. **Batch Renaming**

#### Pattern Renaming
- Use patterns like `episode_{n:03d}.mp4` for numbered files
- `{n:03d}` creates zero-padded numbers (001, 002, 003...)

#### Find & Replace
- Simple text replacement
- Enable regex for advanced patterns

#### Excel Mapping
- Create Excel file with "source" and "target" columns
- Load mapping to rename files based on spreadsheet

### 5. **Flamenco Integration**
- Click "Submit to Flamenco" to send jobs to render farm
- Configure server URL and API token
- Jobs will be distributed to available workers

## 🎯 Common Use Cases

### High Quality H.264 Encoding
1. Add your video files to queue
2. Set Video Codec to "libx264"
3. Set CRF to 18 (or lower for better quality)
4. Enable "Two-pass encoding"
5. Set Audio Codec to "aac" with 192k bitrate
6. Click "Encode with FFmpeg"

### GPU Accelerated Encoding
1. Ensure you have NVENC/QSV/AMF support
2. Set Video Codec to "h264_nvenc" or "hevc_nvenc"
3. Enable "Use GPU" checkbox
4. Set appropriate bitrate or CRF

### Batch Processing with Renaming
1. Add multiple files to queue
2. Click "Batch Rename"
3. Use pattern like `project_{n:03d}.mp4`
4. Preview changes before applying
5. Configure encoding settings
6. Process all files

### Flamenco Render Farm
1. Set up Flamenco server
2. Configure server URL and token
3. Add files to queue
4. Configure encoding settings
5. Click "Submit to Flamenco"
6. Monitor job progress on Flamenco dashboard

## ⚙️ Advanced Configuration

### FFmpeg Parameters
Use the "Extra params" field for advanced FFmpeg options:
- `-preset slow -tune film` for high quality
- `-movflags +faststart` for web streaming
- `-vf "scale=1920:1080"` for resolution scaling
- `-af "volume=0.5"` for audio volume adjustment

### GPU Encoders
Available GPU encoders (auto-detected):
- **NVENC**: h264_nvenc, hevc_nvenc, av1_nvenc
- **QSV**: h264_qsv, hevc_qsv, av1_qsv
- **AMF**: h264_amf, hevc_amf, av1_amf
- **VAAPI**: h264_vaapi, hevc_vaapi, av1_vaapi

### Preset Examples
```json
{
  "name": "web_optimized",
  "container": "mp4",
  "video_codec": "libx264",
  "crf": 23,
  "bitrate": "2M",
  "audio_codec": "aac",
  "audio_bitrate": "128k",
  "additional_params": "-preset fast -movflags +faststart"
}
```

## 🔧 Troubleshooting

### FFmpeg Not Found
- Install FFmpeg from https://ffmpeg.org/download.html
- Add FFmpeg to your system PATH
- Or set FFMPEG_BINARY environment variable

### GPU Not Working
- Ensure you have compatible GPU drivers
- Check that FFmpeg was compiled with GPU support
- Try different GPU encoders (NVENC, QSV, AMF)

### Flamenco Connection Issues
- Verify server URL and port
- Check API token validity
- Ensure Flamenco server is running
- Check network connectivity

### Large File Processing
- Use two-pass encoding for better quality
- Set appropriate bitrate limits
- Consider using faster presets for large files
- Monitor disk space during processing

## 📁 File Structure
```
ffmpeg_encoder/
├── app.py                 # Main application
├── core/                  # Core functionality
├── ui/                    # User interface
├── integrations/          # External integrations
├── utils/                 # Utilities
├── build.spec            # PyInstaller config
├── build_exe.py          # Build script
└── requirements.txt      # Dependencies
```

## 🆘 Support

For issues or questions:
1. Check the console output for error messages
2. Verify FFmpeg installation with `python test_ffmpeg.py`
3. Test basic functionality with `python demo_usage.py`
4. Check the logs in the application's log panel

## 📝 License

This project is provided as-is for educational and personal use.
