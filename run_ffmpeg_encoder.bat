@echo off
echo Starting FFmpeg Encoder...
cd /d "%~dp0"

echo Checking for executable...
if exist "dist\FFmpegEncoder.exe" (
    echo Found executable: dist\FFmpegEncoder.exe
    echo Starting application...
    dist\FFmpegEncoder.exe
    if %ERRORLEVEL% neq 0 (
        echo.
        echo Executable failed, trying Python version...
        python -m ffmpeg_encoder.app
    )
) else (
    echo Executable not found, running from Python...
    python -m ffmpeg_encoder.app
)

echo.
echo Application closed.
pause
