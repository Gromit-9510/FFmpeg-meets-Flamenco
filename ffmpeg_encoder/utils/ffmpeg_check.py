from __future__ import annotations

import subprocess
import shutil
from typing import List, Optional, Dict, Any
from .env import which_ffmpeg, which_ffprobe


def check_ffmpeg_installation() -> Dict[str, Any]:
	"""Check FFmpeg installation and return detailed info."""
	result = {
		"ffmpeg_available": False,
		"ffprobe_available": False,
		"ffmpeg_path": None,
		"ffprobe_path": None,
		"version": None,
		"codecs": [],
		"formats": [],
		"encoders": [],
		"gpu_encoders": [],
	}
	
	# Check FFmpeg
	ffmpeg_path = which_ffmpeg()
	if ffmpeg_path:
		result["ffmpeg_available"] = True
		result["ffmpeg_path"] = ffmpeg_path
		
		# Get version
		try:
			proc = subprocess.run([ffmpeg_path, "-version"], capture_output=True, text=True, timeout=10)
			if proc.returncode == 0:
				version_line = proc.stdout.split('\n')[0]
				result["version"] = version_line
		except Exception:
			pass
	
	# Check FFprobe
	ffprobe_path = which_ffprobe()
	if ffprobe_path:
		result["ffprobe_available"] = True
		result["ffprobe_path"] = ffprobe_path
	
	# Get codecs and formats
	if ffmpeg_path:
		try:
			# Get codecs
			proc = subprocess.run([ffmpeg_path, "-codecs"], capture_output=True, text=True, timeout=10)
			if proc.returncode == 0:
				codecs = []
				for line in proc.stdout.split('\n'):
					if 'D' in line and 'E' in line:  # Decode and Encode
						parts = line.split()
						if len(parts) >= 3:
							codec_name = parts[2]
							codecs.append(codec_name)
				result["codecs"] = codecs
			
			# Get formats
			proc = subprocess.run([ffmpeg_path, "-formats"], capture_output=True, text=True, timeout=10)
			if proc.returncode == 0:
				formats = []
				for line in proc.stdout.split('\n'):
					if 'D' in line and 'E' in line:  # Demux and Mux
						parts = line.split()
						if len(parts) >= 2:
							format_name = parts[1]
							formats.append(format_name)
				result["formats"] = formats
			
			# Get encoders
			proc = subprocess.run([ffmpeg_path, "-encoders"], capture_output=True, text=True, timeout=10)
			if proc.returncode == 0:
				encoders = []
				for line in proc.stdout.split('\n'):
					if 'V' in line and 'A' in line:  # Video and Audio
						parts = line.split()
						if len(parts) >= 2:
							encoder_name = parts[1]
							encoders.append(encoder_name)
				result["encoders"] = encoders
				
				# Filter GPU encoders
				gpu_encoders = [enc for enc in encoders if any(gpu in enc.lower() for gpu in ['nvenc', 'qsv', 'amf', 'vaapi', 'videotoolbox'])]
				result["gpu_encoders"] = gpu_encoders
				
		except Exception:
			pass
	
	return result


def get_gpu_encoders() -> List[str]:
	"""Get list of available GPU encoders."""
	info = check_ffmpeg_installation()
	return info.get("gpu_encoders", [])


def is_gpu_available() -> bool:
	"""Check if any GPU encoders are available."""
	return len(get_gpu_encoders()) > 0


def get_user_friendly_codecs() -> Dict[str, List[Dict[str, str]]]:
	"""Get user-friendly codec names with descriptions."""
	info = check_ffmpeg_installation()
	encoders = info.get("encoders", [])
	
	# User-friendly codec definitions
	codec_definitions = {
		"video": [
			# H.264 일반
			{"id": "libx264", "name": "H.264 CPU", "description": "고품질 H.264 인코딩 (CPU)", "gpu": False},
			{"id": "h264_nvenc", "name": "H.264 GPU", "description": "NVIDIA GPU 가속 H.264", "gpu": True},
			{"id": "separator1", "name": "─────────────────────────", "description": "", "gpu": False, "separator": True},
			
			# H.265 일반
			{"id": "libx265", "name": "H.265 CPU", "description": "고품질 H.265 인코딩 (CPU)", "gpu": False},
			{"id": "hevc_nvenc", "name": "H.265 GPU", "description": "NVIDIA GPU 가속 H.265", "gpu": True},
			{"id": "separator2", "name": "─────────────────────────", "description": "", "gpu": False, "separator": True},
			
			# H.264 저지연
			{"id": "libx264_ll", "name": "저지연 H.264 CPU", "description": "H.264 저지연 인코딩 (zerolatency 옵션)", "gpu": False},
			{"id": "h264_nvenc_ll", "name": "저지연 H.264 GPU", "description": "NVIDIA GPU 가속 H.264 저지연", "gpu": True},
			{"id": "separator3", "name": "─────────────────────────", "description": "", "gpu": False, "separator": True},
			
			# H.265 저지연
			{"id": "libx265_ll", "name": "저지연 H.265 CPU", "description": "H.265 저지연 인코딩 (zerolatency 옵션)", "gpu": False},
			{"id": "hevc_nvenc_ll", "name": "저지연 H.265 GPU", "description": "NVIDIA GPU 가속 H.265 저지연", "gpu": True},
			{"id": "separator4", "name": "─────────────────────────", "description": "", "gpu": False, "separator": True},
			
			# 기타 코덱들
			{"id": "libvpx-vp9", "name": "VP9", "description": "Google VP9 코덱 (CPU)", "gpu": False},
			{"id": "libaom-av1", "name": "AV1", "description": "최신 AV1 코덱 (CPU)", "gpu": False},
			{"id": "prores_ks", "name": "ProRes", "description": "Apple ProRes (고품질)", "gpu": False},
			{"id": "dnxhd", "name": "DNxHD", "description": "Avid DNxHD (방송용)", "gpu": False},
		],
		"audio": [
			{"id": "aac", "name": "AAC", "description": "고품질 오디오 (권장)", "gpu": False},
			{"id": "libmp3lame", "name": "MP3", "description": "MP3 오디오", "gpu": False},
			{"id": "libopus", "name": "Opus", "description": "고품질 저지연 오디오", "gpu": False},
			{"id": "libvorbis", "name": "Vorbis", "description": "오픈소스 오디오", "gpu": False},
			{"id": "ac3", "name": "AC-3", "description": "Dolby Digital", "gpu": False},
			{"id": "flac", "name": "FLAC", "description": "무손실 압축", "gpu": False},
		]
	}
	
	# Filter available codecs
	available = {"video": [], "audio": []}
	
	for category in ["video", "audio"]:
		for codec in codec_definitions[category]:
			# Handle separators
			if codec.get("separator", False):
				available[category].append(codec)
			# Special handling for low-latency codecs
			elif codec["id"].endswith("_ll"):
				base_codec_id = codec["id"].replace("_ll", "")
				if base_codec_id in encoders:
					available[category].append(codec)
			elif codec["id"] in encoders:
				available[category].append(codec)
	
	return available




def get_recommended_codecs() -> Dict[str, List[str]]:
	"""Get recommended codecs based on available encoders."""
	info = check_ffmpeg_installation()
	encoders = info.get("encoders", [])
	
	recommended = {
		"video": [],
		"audio": [],
	}
	
	# Video codecs
	video_codecs = [
		"libx264", "libx265", "libvpx-vp9", "libaom-av1",
		"h264_nvenc", "hevc_nvenc", "h264_qsv", "hevc_qsv",
		"h264_amf", "hevc_amf", "prores_ks", "dnxhd"
	]
	
	for codec in video_codecs:
		if codec in encoders:
			recommended["video"].append(codec)
	
	# Audio codecs
	audio_codecs = [
		"aac", "libmp3lame", "libopus", "libvorbis",
		"ac3", "flac", "pcm_s16le", "pcm_s24le"
	]
	
	for codec in audio_codecs:
		if codec in encoders:
			recommended["audio"].append(codec)
	
	return recommended
