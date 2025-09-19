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
	cmd_base: List[str] = [
		"ffmpeg",
		"-y",
		"-hide_banner",
		"-stats",
		"-i",
		input_path,
	]

	video_args: List[str] = ["-c:v", s.video_codec]
	
	# For 2-pass encoding, only use bitrate (CRF is incompatible)
	if s.two_pass:
		if s.bitrate:
			video_args += ["-b:v", s.bitrate]
		else:
			# Default bitrate if none specified for 2-pass
			video_args += ["-b:v", "2M"]
	else:
		# For single pass, use appropriate quality setting
		if s.crf is not None:
			if s.video_codec.startswith("libx26"):
				# CPU codecs use CRF
				video_args += ["-crf", str(s.crf)]
			elif s.video_codec in ["h264_nvenc", "hevc_nvenc"]:
				# NVENC codecs use QP
				video_args += ["-qp", str(s.crf)]
		if s.bitrate:
			video_args += ["-b:v", s.bitrate]

	# Add tune parameter
	if s.tune and s.tune != "none":
		video_args += ["-tune", s.tune]

	# Handle low latency codecs
	if s.video_codec.endswith("_ll"):
		# Remove _ll suffix and add low latency settings
		base_codec = s.video_codec.replace("_ll", "")
		video_args = ["-c:v", base_codec]
		
		# Add low latency presets FIRST
		if "nvenc" in base_codec:
			video_args += ["-preset", "p1", "-tune", "ull"]
		elif base_codec in ["libx264", "libx265"]:
			video_args += ["-preset", "ultrafast", "-tune", "zerolatency"]
		
		# Then add quality settings (this will override preset defaults)
		if s.two_pass:
			if s.bitrate:
				video_args += ["-b:v", s.bitrate]
			else:
				video_args += ["-b:v", "2M"]
		else:
			# For single pass, use appropriate quality setting
			if s.crf is not None:
				if base_codec in ["libx264", "libx265"]:
					# CPU codecs use CRF
					video_args += ["-crf", str(s.crf)]
				elif base_codec in ["h264_nvenc", "hevc_nvenc"]:
					# NVENC codecs use QP (similar to CRF but different scale)
					# Convert CRF to QP: CRF 0-51 maps to QP 0-51 for NVENC
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

	misc_args: List[str] = []
	if s.max_filesize:
		misc_args += ["-fs", s.max_filesize]
	if s.extra_params:
		misc_args += s.extra_params.split()

	full = cmd_base + video_args + audio_args + misc_args + [output_path]

	if not s.two_pass:
		return [full]

	# Two pass: only for typical x264/x265 style
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
	second = cmd_base + video_args + audio_args + [
		"-pass", "2",
		"-passlogfile", pass_log,
	] + misc_args + [output_path]
	return [first, second]
