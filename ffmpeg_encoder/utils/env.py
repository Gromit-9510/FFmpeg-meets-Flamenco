from __future__ import annotations

import os
import shutil
import platform
from pathlib import Path


class FFmpegNotFoundError(RuntimeError):
	pass


def get_submitter_platform() -> str:
	plt = platform.system().lower()
	if "windows" in plt:
		return "Windows"
	if "linux" in plt:
		return "Linux"
	if "darwin" in plt or "mac" in plt:
		return "Darwin"
	return platform.system()


def which_ffmpeg() -> str | None:
	custom = os.environ.get("FFMPEG_BINARY")
	if custom and Path(custom).exists():
		return custom
	return shutil.which("ffmpeg")


def which_ffprobe() -> str | None:
	custom = os.environ.get("FFPROBE_BINARY")
	if custom and Path(custom).exists():
		return custom
	return shutil.which("ffprobe")


def ensure_ffmpeg_available() -> None:
	if not which_ffmpeg():
		raise FFmpegNotFoundError(
			"FFmpeg not found. Please install FFmpeg and ensure it's on PATH or set FFMPEG_BINARY env var."
		)
	if not which_ffprobe():
		raise FFmpegNotFoundError(
			"FFprobe not found. Please install FFmpeg (includes ffprobe) or set FFPROBE_BINARY env var."
		)
