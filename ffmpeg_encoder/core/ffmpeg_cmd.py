from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class VideoSettings:
	container: str = "mp4"
	video_codec: str = "libx264"
	crf: Optional[int] = 18
	bitrate: Optional[str] = None
	two_pass: bool = False
	gpu_enable: bool = False
	low_latency: bool = False
	tune: str = "none"
	audio_codec: str = "aac"
	audio_bitrate: Optional[str] = "192k"
	max_filesize: Optional[str] = None
	extra_params: Optional[str] = None

	def output_extension(self) -> str:
		return self.container


def build_ffmpeg_commands(input_path: str, output_path: str, s: VideoSettings) -> List[List[str]]:
	"""Build FFmpeg command(s) for the given settings."""
	try:
		print(f"[DEBUG] build_ffmpeg_commands called with:")
		print(f"  input_path: {input_path}")
		print(f"  output_path: {output_path}")
		print(f"  video_codec: {s.video_codec}")
		print(f"  container: {s.container}")
		print(f"  crf: {s.crf}")
		print(f"  extra_params: {s.extra_params}")
		
		# Validate input
		if not input_path or not output_path:
			raise ValueError("Input and output paths are required")
		
		if not isinstance(s, VideoSettings):
			raise ValueError("Invalid VideoSettings object")
		
		cmd_base: List[str] = [
			"ffmpeg",
			"-y",
			"-hide_banner",
			"-stats",
			"-loglevel", "info",
			"-i",
			input_path,
		]

		# Map user-friendly codec names to actual FFmpeg codec names
		codec_mapping = {
			"h264_nvenc": "h264_nvenc",
			"h264_nvenc_ll": "h264_nvenc",
			"hevc_nvenc": "hevc_nvenc", 
			"hevc_nvenc_ll": "hevc_nvenc",
			"libx264": "libx264",
			"libx264_ll": "libx264",
			"libx264_2pass": "libx264",
			"libx265": "libx265",
			"libx265_ll": "libx265",
			"libx265_2pass": "libx265",
			"libvpx-vp9": "libvpx-vp9",
			"libaom-av1": "libaom-av1",
		}
		
		actual_codec = codec_mapping.get(s.video_codec, s.video_codec)
		print(f"[DEBUG] Codec mapping: {s.video_codec} -> {actual_codec}")
		video_args: List[str] = ["-c:v", actual_codec]
		
		# Check if this is a 2-pass codec
		is_2pass_codec = isinstance(s.video_codec, str) and s.video_codec.endswith("_2pass")
		
		# For 2-pass encoding, only use bitrate (CRF is incompatible)
		# Note: GPU 2-pass codecs have been removed from UI, only CPU codecs support 2-pass
		if s.two_pass or is_2pass_codec:
			# CPU codecs: Use traditional 2-pass
			if s.bitrate:
				video_args += ["-b:v", s.bitrate]
			else:
				video_args += ["-b:v", "2M"]
		else:
			# For single pass, use appropriate quality setting
			# Always add quality setting if crf is provided (including 0)
			if s.crf is not None and s.crf >= 0:
				# Use actual_codec for proper detection
				if actual_codec.startswith("libx26") or actual_codec in ["libvpx-vp9", "libaom-av1"]:
					# CPU codecs use CRF
					video_args += ["-crf", str(s.crf)]
				elif "nvenc" in actual_codec:
					# NVENC: Use -qp with -rc constqp (set later)
					video_args += ["-qp", str(s.crf)]
				elif "qsv" in actual_codec:
					video_args += ["-global_quality", str(s.crf)]
				elif "vaapi" in actual_codec:
					video_args += ["-global_quality", str(s.crf)]
				elif "amf" in actual_codec:
					video_args += ["-qp", str(s.crf)]
				else:
					# Fallback to CRF for other codecs
					video_args += ["-crf", str(s.crf)]
			if s.bitrate:
				video_args += ["-b:v", s.bitrate]

		# Add tune parameter for CPU codecs
		if s.tune and s.tune != "none" and isinstance(s.video_codec, str) and not any(gpu in s.video_codec for gpu in ["nvenc", "qsv", "amf", "vaapi"]):
			video_args += ["-tune", s.tune]
		
		# Add GPU-specific settings with better compatibility
		if "nvenc" in actual_codec:
			# NVENC specific settings - simplified for better compatibility
			# Only add preset if not already specified in extra_params
			extra_params_str = str(s.extra_params) if s.extra_params is not None else ""
			try:
				extra_parts = extra_params_str.split()
				has_preset = any("-preset" in part for part in extra_parts)
				if not has_preset:
					video_args += ["-preset", "p4"]  # Balanced preset
			except Exception as e:
				print(f"[DEBUG] Error processing extra_params: {e}")
				video_args += ["-preset", "p4"]  # Default preset
			# Add pixel format conversion for NVENC compatibility
			video_args += ["-pix_fmt", "yuv420p"]  # Convert to 8-bit YUV420P
			# For NVENC, -qp is sufficient without -rc constqp for better compatibility
		elif "qsv" in actual_codec:
			# QSV specific settings
			video_args += ["-preset", "medium"]
			video_args += ["-pix_fmt", "yuv420p"]  # Convert to 8-bit YUV420P
			# Quality is already set above with -global_quality
		elif "amf" in actual_codec:
			# AMF specific settings
			video_args += ["-quality", "balanced"]
			video_args += ["-pix_fmt", "yuv420p"]  # Convert to 8-bit YUV420P
			# Quality is already set above with -qp
		elif "vaapi" in actual_codec:
			# VAAPI specific settings
			video_args += ["-compression_level", "1"]
			video_args += ["-pix_fmt", "yuv420p"]  # Convert to 8-bit YUV420P
			# Quality is already set above with -global_quality

		# Handle low latency codecs
		if isinstance(s.video_codec, str) and s.video_codec.endswith("_ll"):
			# Remove _ll suffix and add low latency settings
			base_codec = s.video_codec.replace("_ll", "")
			actual_base_codec = codec_mapping.get(base_codec, base_codec)
			video_args = ["-c:v", actual_base_codec]
			
			# Add low latency presets
			if "nvenc" in actual_base_codec:
				video_args += ["-preset", "p1"]  # Fastest preset
				video_args += ["-tune", "ull"]   # Ultra low latency
				video_args += ["-pix_fmt", "yuv420p"]  # Convert to 8-bit YUV420P
			elif "qsv" in actual_base_codec:
				video_args += ["-preset", "fast"]
				video_args += ["-pix_fmt", "yuv420p"]  # Convert to 8-bit YUV420P
			elif "amf" in actual_base_codec:
				video_args += ["-quality", "speed"]
				video_args += ["-pix_fmt", "yuv420p"]  # Convert to 8-bit YUV420P
			elif actual_base_codec in ["libx264", "libx265"]:
				video_args += ["-preset", "ultrafast", "-tune", "zerolatency"]
			
			# Then add quality settings for low latency
			if s.two_pass or is_2pass_codec:  # Also check for _2pass suffix
				if any(gpu in actual_base_codec for gpu in ["nvenc", "qsv", "amf", "vaapi"]):
					# GPU codecs: Use VBR mode instead of 2-pass
					if s.bitrate:
						video_args += ["-b:v", s.bitrate]
					else:
						video_args += ["-b:v", "2M"]
					video_args += ["-rc", "vbr"]
				else:
					# CPU codecs: Use traditional 2-pass
					if s.bitrate:
						video_args += ["-b:v", s.bitrate]
					else:
						video_args += ["-b:v", "2M"]
			else:
				# For single pass, use appropriate quality setting
				if s.crf is not None and s.crf >= 0:
					if actual_base_codec in ["libx264", "libx265"]:
						# CPU codecs use CRF
						video_args += ["-crf", str(s.crf)]
					elif any(gpu in actual_base_codec for gpu in ["nvenc", "qsv", "amf", "vaapi"]):
						# GPU codecs use different quality parameters
						if "qsv" in actual_base_codec:
							video_args += ["-global_quality", str(s.crf)]
						elif "vaapi" in actual_base_codec:
							video_args += ["-global_quality", str(s.crf)]
						else:
							video_args += ["-qp", str(s.crf)]
				if s.bitrate:
					video_args += ["-b:v", s.bitrate]

		if s.gpu_enable:
			# Rely on chosen codec (e.g., h264_nvenc) rather than auto
			pass

		audio_args: List[str] = []
		if s.audio_codec:
			audio_args += ["-c:a", s.audio_codec]
			if s.audio_bitrate:
				audio_args += ["-b:a", s.audio_bitrate]

		# Add container format specification for proper MOV > MP4 conversion
		container_args: List[str] = []
		if s.container:
			container_args += ["-f", s.container]

		misc_args: List[str] = []
		if s.max_filesize:
			misc_args += ["-fs", s.max_filesize]
		if s.extra_params and isinstance(s.extra_params, str):
			# Parse extra_params and avoid duplicates with existing settings
			extra_parts = s.extra_params.split()
			existing_params = set()
			
			# Collect existing parameter names to avoid duplicates
			for i in range(0, len(video_args), 2):
				if i + 1 < len(video_args) and video_args[i].startswith('-'):
					existing_params.add(video_args[i])
			
			# Also check audio_args and container_args for conflicts
			for i in range(0, len(audio_args), 2):
				if i + 1 < len(audio_args) and audio_args[i].startswith('-'):
					existing_params.add(audio_args[i])
			
			for i in range(0, len(container_args), 2):
				if i + 1 < len(container_args) and container_args[i].startswith('-'):
					existing_params.add(container_args[i])
			
			# Add extra parameters that don't conflict
			i = 0
			while i < len(extra_parts):
				if extra_parts[i].startswith('-'):
					param_name = extra_parts[i]
					if param_name not in existing_params:
						misc_args.append(param_name)
						if i + 1 < len(extra_parts) and not extra_parts[i + 1].startswith('-'):
							misc_args.append(extra_parts[i + 1])
							i += 1
				i += 1

		full = cmd_base + video_args + audio_args + container_args + misc_args + [output_path]
		print(f"[DEBUG] Generated command: {' '.join(full)}")

		# Check if this should use 2-pass encoding
		# Only CPU codecs (libx264, libx265) support 2-pass encoding
		if s.two_pass or is_2pass_codec:
			# Two pass: only for CPU codecs (libx264, libx265)
			import tempfile
			import os
			
			# Create a temporary directory for pass files
			temp_dir = tempfile.gettempdir()
			pass_log = os.path.join(temp_dir, f"ffmpeg2pass-{os.getpid()}.log")
			
			first = cmd_base + video_args + [
				"-pass", "1",
				"-passlogfile", pass_log,
				"-an",
				"-f", "null",
				"NUL" if os.name == 'nt' else "/dev/null",
			]
			second = cmd_base + video_args + audio_args + container_args + [
				"-pass", "2",
				"-passlogfile", pass_log,
			] + misc_args + [output_path]
			return [first, second]
		
		# Single pass encoding
		print(f"[DEBUG] Returning single pass command")
		return [full]
		
	except Exception as e:
		print(f"[ERROR] Error in build_ffmpeg_commands: {e}")
		print(f"[ERROR] Exception type: {type(e).__name__}")
		import traceback
		print(f"[ERROR] Traceback: {traceback.format_exc()}")
		return []
