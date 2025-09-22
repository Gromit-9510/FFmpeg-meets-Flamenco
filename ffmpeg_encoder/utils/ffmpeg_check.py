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
	
	try:
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
				# Get encoders
				proc = subprocess.run([ffmpeg_path, "-encoders"], capture_output=True, text=True, timeout=10)
				if proc.returncode == 0:
					encoders = []
					for line in proc.stdout.split('\n'):
						if 'V' in line or 'A' in line:  # Video or Audio
							parts = line.split()
							if len(parts) >= 2:
								encoder_name = parts[1]
								# Skip if it's a description line
								if not encoder_name.startswith('libav') and not encoder_name.startswith('libsw'):
									encoders.append(encoder_name)
					result["encoders"] = encoders
				
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
						if 'V' in line or 'A' in line:  # Video or Audio
							parts = line.split()
							if len(parts) >= 2:
								encoder_name = parts[1]
								# Skip if it's a description line
								if not encoder_name.startswith('libav') and not encoder_name.startswith('libsw'):
									encoders.append(encoder_name)
					result["encoders"] = encoders
					
					# Filter GPU encoders
					gpu_encoders = [enc for enc in encoders if any(gpu in enc.lower() for gpu in ['nvenc', 'qsv', 'amf', 'vaapi', 'videotoolbox'])]
					result["gpu_encoders"] = gpu_encoders
					
			except Exception:
				pass
	
	except Exception as e:
		print(f"Error checking FFmpeg installation: {e}")
		# Return the result with default values
	
	return result


def get_gpu_encoders() -> List[str]:
	"""Get list of available GPU encoders."""
	try:
		info = check_ffmpeg_installation()
		return info.get("gpu_encoders", [])
	except Exception:
		# Fallback: return common GPU encoders if detection fails
		return ["h264_nvenc", "hevc_nvenc", "h264_qsv", "hevc_qsv", "h264_amf", "hevc_amf"]


def test_gpu_encoder_compatibility(encoder: str) -> bool:
	"""Test if a GPU encoder is actually compatible with current drivers."""
	ffmpeg_path = which_ffmpeg()
	if not ffmpeg_path:
		return False
	
	try:
		# Create a simple test command to check encoder compatibility
		# Use a minimal test that should work if the encoder is available
		test_cmd = [
			ffmpeg_path, "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1",
			"-c:v", encoder, "-t", "0.1", "-f", "null", "-"
		]
		
		proc = subprocess.run(
			test_cmd, 
			capture_output=True, 
			text=True, 
			timeout=10,
			encoding='utf-8',
			errors='replace'
		)
		
		# Check for specific NVENC compatibility issues
		error_output = proc.stderr.lower()
		if any(msg in error_output for msg in [
			"driver does not support",
			"required nvidia driver",
			"encoder not found",
			"no such encoder",
			"required nvenc api version",
			"minimum required nvidia driver",
			"error while opening encoder"
		]):
			return False
		
		# If it succeeds or fails with a non-encoder related error, consider it compatible
		return True
		
	except Exception:
		return False


def check_nvenc_driver_version() -> bool:
	"""Check if NVENC driver version is compatible."""
	ffmpeg_path = which_ffmpeg()
	if not ffmpeg_path:
		return False
	
	try:
		# Test with a very simple NVENC command
		test_cmd = [
			ffmpeg_path, "-f", "lavfi", "-i", "testsrc=duration=0.1:size=64x64:rate=1",
			"-c:v", "h264_nvenc", "-t", "0.05", "-f", "null", "-"
		]
		
		proc = subprocess.run(
			test_cmd, 
			capture_output=True, 
			text=True, 
			timeout=5,
			encoding='utf-8',
			errors='replace'
		)
		
		# Check for driver version issues
		error_output = proc.stderr.lower()
		if any(msg in error_output for msg in [
			"driver does not support",
			"required nvidia driver",
			"required nvenc api version",
			"minimum required nvidia driver",
			"error while opening encoder"
		]):
			return False
		
		return True
		
	except Exception:
		return False


def get_compatible_gpu_encoders() -> List[str]:
	"""Get list of GPU encoders that are actually compatible with current system."""
	all_gpu_encoders = get_gpu_encoders()
	compatible_encoders = []
	
	# Special check for NVENC
	nvenc_compatible = check_nvenc_driver_version()
	
	for encoder in all_gpu_encoders:
		# Skip NVENC encoders if driver is incompatible
		if "nvenc" in encoder and not nvenc_compatible:
			continue
		
		# Test other GPU encoders
		if "nvenc" not in encoder:
			if test_gpu_encoder_compatibility(encoder):
				compatible_encoders.append(encoder)
		else:
			# NVENC encoders - only add if driver is compatible
			if nvenc_compatible:
				compatible_encoders.append(encoder)
	
	return compatible_encoders


def is_gpu_available() -> bool:
	"""Check if any GPU encoders are available."""
	return len(get_gpu_encoders()) > 0


def get_user_friendly_codecs(container: str = None) -> Dict[str, List[Dict[str, str]]]:
	"""Get user-friendly codec names with descriptions."""
	info = check_ffmpeg_installation()
	encoders = info.get("encoders", [])
	
	# Container compatibility mapping
	container_codecs = {
		"mp4": ["libx264", "libx265", "h264_nvenc", "hevc_nvenc", "libx264_ll", "libx265_ll", "h264_nvenc_ll", "hevc_nvenc_ll"],
		"avi": ["libx264", "libx265", "h264_nvenc", "hevc_nvenc", "libx264_ll", "libx265_ll", "h264_nvenc_ll", "hevc_nvenc_ll", "dnxhd"],
		"mov": ["libx264", "libx265", "h264_nvenc", "hevc_nvenc", "libx264_ll", "libx265_ll", "h264_nvenc_ll", "hevc_nvenc_ll", "prores_ks"],
		"mkv": ["libx264", "libx265", "h264_nvenc", "hevc_nvenc", "libx264_ll", "libx265_ll", "h264_nvenc_ll", "hevc_nvenc_ll", "libvpx-vp9", "libaom-av1"],
		"webm": ["libvpx-vp9", "libaom-av1"],
		"flv": ["libx264", "h264_nvenc", "libx264_ll", "h264_nvenc_ll"],
		"wmv": ["libx264", "h264_nvenc", "libx264_ll", "h264_nvenc_ll"],
		"m4v": ["libx264", "libx265", "h264_nvenc", "hevc_nvenc", "libx264_ll", "libx265_ll", "h264_nvenc_ll", "hevc_nvenc_ll"]
	}
	
	# User-friendly codec definitions
	codec_definitions = {
		"video": [
			# H.264 Group
			{"id": "libx264", "name": "libx264 (CPU)", "description": "", "gpu": False},
			{"id": "libx264_ll", "name": "libx264 (CPU) Low Latency", "description": "low latency", "gpu": False},
			{"id": "h264_nvenc", "name": "H.264 (GPU)", "description": "", "gpu": True},
			{"id": "h264_nvenc_ll", "name": "H.264 (GPU) Low Latency", "description": "low latency", "gpu": True},
			{"id": "separator1", "name": "─────────────────────────", "description": "", "gpu": False, "separator": True},
			
			# H.265 Group
			{"id": "libx265", "name": "libx265 (CPU)", "description": "", "gpu": False},
			{"id": "libx265_ll", "name": "libx265 (CPU) Low Latency", "description": "low latency", "gpu": False},
			{"id": "hevc_nvenc", "name": "H.265 (GPU)", "description": "", "gpu": True},
			{"id": "hevc_nvenc_ll", "name": "H.265 (GPU) Low Latency", "description": "low latency", "gpu": True},
			{"id": "separator2", "name": "─────────────────────────", "description": "", "gpu": False, "separator": True},
			
			# Other Codecs
			{"id": "libvpx-vp9", "name": "libvpx-vp9 (CPU)", "description": "", "gpu": False},
			{"id": "libaom-av1", "name": "libaom-av1 (CPU)", "description": "", "gpu": False},
			{"id": "prores_ks", "name": "prores_ks (CPU)", "description": "", "gpu": False},
			{"id": "dnxhd", "name": "dnxhd (CPU)", "description": "", "gpu": False},
		],
		"audio": [
			{"id": "aac", "name": "AAC", "description": "High quality audio (recommended)", "gpu": False},
			{"id": "libmp3lame", "name": "MP3", "description": "MP3 audio", "gpu": False},
			{"id": "libopus", "name": "Opus", "description": "High quality low latency audio", "gpu": False},
			{"id": "libvorbis", "name": "Vorbis", "description": "Open source audio", "gpu": False},
			{"id": "ac3", "name": "AC-3", "description": "Dolby Digital", "gpu": False},
			{"id": "flac", "name": "FLAC", "description": "Lossless compression", "gpu": False},
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
					# Check container compatibility for video codecs
					if category == "video" and container and container in container_codecs:
						if codec["id"] not in container_codecs[container]:
							continue
					available[category].append(codec)
			elif codec["id"] in encoders:
				# Check container compatibility for video codecs
				if category == "video" and container and container in container_codecs:
					if codec["id"] not in container_codecs[container]:
						continue
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
