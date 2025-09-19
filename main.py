#!/usr/bin/env python3
"""
Main entry point for FFmpeg Encoder - standalone script for PyInstaller.
"""

import sys
import platform
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from ffmpeg_encoder.ui.main_window import MainWindow
from ffmpeg_encoder.utils.env import ensure_ffmpeg_available
from ffmpeg_encoder.utils.ffmpeg_check import check_ffmpeg_installation


def main() -> None:
	app = QApplication(sys.argv)
	app.setApplicationName("FFmpeg Encoder")
	app.setOrganizationName("FFmpegEncoder")
	app.setApplicationVersion("0.0.1")

	# Check FFmpeg installation and show info
	try:
		ensure_ffmpeg_available()
		ffmpeg_info = check_ffmpeg_installation()
		print(f"FFmpeg version: {ffmpeg_info.get('version', 'Unknown')}")
		print(f"Available GPU encoders: {ffmpeg_info.get('gpu_encoders', [])}")
	except Exception as e:
		print(f"FFmpeg check failed: {e}")
		# Continue anyway, let the UI handle the error

	window = MainWindow()
	window.resize(1280, 720)
	window.show()

	sys.exit(app.exec())


if __name__ == "__main__":
	main()
