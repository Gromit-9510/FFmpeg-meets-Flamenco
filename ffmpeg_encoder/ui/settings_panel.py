from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
	QWidget,
	QVBoxLayout,
	QFormLayout,
	QComboBox,
	QLineEdit,
	QSpinBox,
	QCheckBox,
	QPushButton,
	QTabWidget,
	QHBoxLayout,
	QFileDialog,
	QLabel,
	QGroupBox,
)
import os
import json
from pathlib import Path
from ..utils.ffmpeg_check import get_compatible_gpu_encoders


class SettingsPanel(QWidget):
	save_preset_clicked = Signal()
	load_preset_clicked = Signal()

	def __init__(self) -> None:
		super().__init__()
		layout = QVBoxLayout(self)
		
		# Flamenco 설정 파일 경로
		self.flamenco_config_path = Path.home() / ".ffmpeg_encoder" / "flamenco_config.json"
		self.flamenco_config_path.parent.mkdir(exist_ok=True)

		tabs = QTabWidget()
		tabs.addTab(self._build_video_tab(), "Settings")
		tabs.addTab(self._build_flamenco_tab(), "Flamenco")
		layout.addWidget(tabs)

		preset_row = QHBoxLayout()
		self.preset_name = QLineEdit()
		self.preset_name.setPlaceholderText("Preset name")
		self.save_preset_btn = QPushButton("Save Preset")
		self.load_preset_btn = QPushButton("Load Preset")
		preset_row.addWidget(self.preset_name)
		preset_row.addWidget(self.save_preset_btn)
		preset_row.addWidget(self.load_preset_btn)
		layout.addLayout(preset_row)

		self.encode_btn = QPushButton("Encode with FFmpeg")
		self.submit_flamenco_btn = QPushButton("Submit to Flamenco")
		layout.addWidget(self.encode_btn)
		layout.addWidget(self.submit_flamenco_btn)
		layout.addStretch(1)

		self.save_preset_btn.clicked.connect(self.save_preset_clicked.emit)
		self.load_preset_btn.clicked.connect(self.load_preset_clicked.emit)

	def _build_video_tab(self) -> QWidget:
		w = QWidget()
		layout = QVBoxLayout(w)
		
		# Container format
		container_group = QGroupBox("Container Format")
		container_layout = QFormLayout(container_group)
		self.container_format = QComboBox()
		self.container_format.addItems(["mp4", "mkv", "mov", "avi", "webm"])
		self.container_format.currentTextChanged.connect(self._on_container_changed)
		container_layout.addRow("Format:", self.container_format)
		layout.addWidget(container_group)
		
		# Video codec selection
		codec_group = QGroupBox("Settings")
		codec_layout = QVBoxLayout(codec_group)
		
		self.video_codec = QComboBox()
		self.codec_description = QLabel("Select a codec")
		self.codec_description.setWordWrap(True)
		self.codec_description.setStyleSheet("color: #666; font-size: 11px;")
		
		# Populate codecs
		container = self.container_format.currentText()
		self._populate_user_friendly_codecs(container)
		
		# Connect codec change to update description
		self.video_codec.currentTextChanged.connect(self._on_codec_changed)
		
		codec_layout.addWidget(QLabel("Codec:"))
		codec_layout.addWidget(self.video_codec)
		codec_layout.addWidget(self.codec_description)
		layout.addWidget(codec_group)
		
		# Quality settings
		quality_group = QGroupBox("Quality Settings")
		quality_layout = QFormLayout(quality_group)
		
		# Quality control type (CRF/QP)
		self.crf_label = QLabel("CRF (Quality):")
		self.crf = QSpinBox()
		self.crf.setRange(0, 51)
		self.crf.setValue(18)
		self.crf.setToolTip("Constant Rate Factor: 0=무손실, 18=고품질, 23=기본값, 28=저품질, 51=최저품질")
		self.crf.valueChanged.connect(self._on_crf_changed)
		
		# Bitrate
		self.bitrate = QLineEdit()
		self.bitrate.setPlaceholderText("예: 8M 또는 2000k")
		self.bitrate.setToolTip("비트레이트: 초당 데이터량 (예: 8M, 2000k)")
		
		quality_layout.addRow(self.crf_label, self.crf)
		quality_layout.addRow("Bitrate:", self.bitrate)
		layout.addWidget(quality_group)
		
		# Advanced codec settings
		advanced_group = QGroupBox("Advanced Codec Settings")
		advanced_layout = QFormLayout(advanced_group)
		
		# Preset
		self.preset = QComboBox()
		self.preset.addItems([
			"ultrafast", "superfast", "veryfast", "faster", "fast", 
			"medium", "slow", "slower", "veryslow", "placebo"
		])
		self.preset.setCurrentText("medium")
		self.preset.setToolTip("인코딩 속도 vs 압축률: ultrafast(빠름) → placebo(느림, 고압축)")
		
		# Tune
		self.tune = QComboBox()
		self.tune.addItems([
			"none", "film", "animation", "grain", "stillimage", 
			"fastdecode", "zerolatency", "psnr", "ssim"
		])
		self.tune.setCurrentText("none")
		self.tune.setToolTip("최적화 타입: film(영화), animation(애니메이션), grain(노이즈), zerolatency(실시간)")
		
		# Profile (for H.264/H.265)
		self.profile = QComboBox()
		self.profile.addItems(["auto", "baseline", "main", "high", "high10", "high422", "high444"])
		self.profile.setCurrentText("auto")
		self.profile.setToolTip("프로파일: baseline(호환성), main(기본), high(고품질), auto(자동선택)")
		
		# Level (for H.264/H.265)
		self.level = QComboBox()
		self.level.addItems(["auto", "3.0", "3.1", "3.2", "4.0", "4.1", "4.2", "5.0", "5.1", "5.2"])
		self.level.setCurrentText("auto")
		self.level.setToolTip("레벨: 디코더 호환성 (auto=자동선택)")
		
		# 2-pass encoding
		self.two_pass = QCheckBox("2-Pass Encoding")
		self.two_pass.setToolTip("2단계 인코딩: 더 정확한 비트레이트 제어 (CPU 코덱만 지원)")
		
		advanced_layout.addRow("Preset:", self.preset)
		advanced_layout.addRow("Tune:", self.tune)
		advanced_layout.addRow("Profile:", self.profile)
		advanced_layout.addRow("Level:", self.level)
		advanced_layout.addRow("", self.two_pass)
		layout.addWidget(advanced_group)
		
		
		# Audio settings
		audio_group = QGroupBox("Audio Settings")
		audio_layout = QFormLayout(audio_group)
		
		self.audio_codec = QComboBox()
		self._populate_audio_codecs()
		self.audio_bitrate = QLineEdit()
		self.audio_bitrate.setPlaceholderText("e.g. 192k")
		self.audio_bitrate.setText("192k")  # Set default value
		audio_layout.addRow("Audio codec:", self.audio_codec)
		audio_layout.addRow("Audio bitrate:", self.audio_bitrate)
		layout.addWidget(audio_group)
		
		# Advanced options
		advanced_group = QGroupBox("Advanced Options")
		advanced_layout = QFormLayout(advanced_group)
		
		self.max_filesize = QLineEdit()
		self.max_filesize.setPlaceholderText("e.g. 700M")
		self.max_filesize.setToolTip("Maximum file size (e.g. 700M, 1G)")
		
		advanced_layout.addRow("Max File Size:", self.max_filesize)
		layout.addWidget(advanced_group)
		
		layout.addStretch()
		return w

	def _populate_user_friendly_codecs(self, container: str = None) -> None:
		"""Populate codec lists with user-friendly names."""
		# Store codec data for later use
		self.codec_data = {}
		
		# Clear existing codecs
		self.video_codec.clear()
		
		# 단순화된 코덱 목록 (종류만 선택)
		fallback_codecs = [
			{"id": "libx264", "name": "H.264 (CPU)", "description": "libx264 - 소프트웨어 인코딩"},
			{"id": "h264_nvenc", "name": "H.264 (GPU)", "description": "NVENC - 하드웨어 가속"},
			{"id": "separator1", "name": "─────────────────────────", "description": "", "separator": True},
			{"id": "libx265", "name": "H.265 (CPU)", "description": "libx265 - 소프트웨어 인코딩"},
			{"id": "hevc_nvenc", "name": "H.265 (GPU)", "description": "NVENC - 하드웨어 가속"},
			{"id": "separator2", "name": "─────────────────────────", "description": "", "separator": True},
			{"id": "libvpx-vp9", "name": "VP9 (CPU)", "description": "Google VP9 - 웹 최적화"},
			{"id": "libaom-av1", "name": "AV1 (CPU)", "description": "AOMedia AV1 - 차세대 코덱"},
		]
		
		for codec in fallback_codecs:
			if codec.get("separator", False):
				display_name = codec['name']
			else:
				display_name = f"{codec['name']} {codec['description']}".strip()
			self.video_codec.addItem(display_name, codec['id'])
			self.codec_data[codec['id']] = codec
		
		# Set default selection
		self.video_codec.setCurrentIndex(0)
		self._on_codec_changed()
		
		# Try to load additional codecs from FFmpeg (optional)
		try:
			from ..utils.ffmpeg_check import get_user_friendly_codecs
			codecs = get_user_friendly_codecs(container)
			
			# Only add if we get more codecs than fallback
			video_codecs = codecs.get("video", [])
			if len(video_codecs) > len(fallback_codecs):
				# Clear and reload with all codecs
				self.video_codec.clear()
				self.codec_data = {}
				
				for codec in video_codecs:
					if codec.get("separator", False):
						display_name = codec['name']
					else:
						display_name = f"{codec['name']} {codec['description']}".strip()
					self.video_codec.addItem(display_name, codec['id'])
					self.codec_data[codec['id']] = codec
				
				# Set default selection
				if video_codecs:
					self.video_codec.setCurrentIndex(0)
					self._on_codec_changed()
				
		except Exception as e:
			import traceback
			print(f"Error loading additional codecs: {e}")
			print(f"Traceback: {traceback.format_exc()}")
			# Keep fallback codecs that were already added

	def _on_codec_changed(self) -> None:
		"""Handle codec selection change."""
		current_data = self.video_codec.currentData()
		if current_data and hasattr(self, 'codec_data') and current_data in self.codec_data:
			codec_info = self.codec_data[current_data]
			self.codec_description.setText(codec_info['description'])
		else:
			self.codec_description.setText("코덱을 선택하세요")
		
		# Update UI based on selected codec
		if hasattr(self, 'crf_label'):
			self._update_crf_visibility()
		if hasattr(self, 'preset'):
			self._update_advanced_settings()
	
	
	def _update_crf_visibility(self) -> None:
		"""Update CRF/QP visibility based on selected codec."""
		current_data = self.video_codec.currentData()
		if not current_data:
			return
		
		# Extract base codec name (remove _ll suffix for low latency)
		base_codec = current_data.replace("_ll", "")
		
		# Determine quality control type based on codec
		is_cpu_codec = current_data.startswith("libx") or current_data in ["libvpx-vp9", "libaom-av1"]
		is_gpu_codec = "nvenc" in current_data
		
		# Update label
		if is_cpu_codec:
			self.crf_label.setText("CRF (Quality):")
		elif is_gpu_codec:
			self.crf_label.setText("QP (Quality):")
		else:
			self.crf_label.setText("Quality:")

	def _update_advanced_settings(self) -> None:
		"""Update advanced settings based on selected codec."""
		current_data = self.video_codec.currentData()
		if not current_data:
			return
		
		# Enable/disable settings based on codec capabilities
		is_cpu_codec = current_data.startswith("libx")
		is_gpu_codec = "nvenc" in current_data
		
		# 2-pass encoding only for CPU codecs
		self.two_pass.setEnabled(is_cpu_codec)
		if not is_cpu_codec:
			self.two_pass.setChecked(False)
		
		# Update preset options based on codec
		if is_gpu_codec:
			# GPU codecs have different presets
			self.preset.clear()
			self.preset.addItems(["p1", "p2", "p3", "p4", "p5", "p6", "p7"])
			self.preset.setCurrentText("p4")
			self.preset.setToolTip("NVENC 프리셋: p1(최고속도) → p7(최고품질)")
		else:
			# CPU codecs use standard presets
			self.preset.clear()
			self.preset.addItems([
				"ultrafast", "superfast", "veryfast", "faster", "fast", 
				"medium", "slow", "slower", "veryslow", "placebo"
			])
			self.preset.setCurrentText("medium")
			self.preset.setToolTip("인코딩 속도 vs 압축률: ultrafast(빠름) → placebo(느림, 고압축)")
		
		# Update tune options based on codec
		if is_gpu_codec:
			# GPU codecs have limited tune options
			self.tune.clear()
			self.tune.addItems(["none", "hq", "ll", "ull"])
			self.tune.setCurrentText("none")
			self.tune.setToolTip("NVENC 튠: hq(고품질), ll(저지연), ull(초저지연)")
		else:
			# CPU codecs have full tune options
			self.tune.clear()
			self.tune.addItems([
				"none", "film", "animation", "grain", "stillimage", 
				"fastdecode", "zerolatency", "psnr", "ssim"
			])
			self.tune.setCurrentText("none")
			self.tune.setToolTip("최적화 타입: film(영화), animation(애니메이션), grain(노이즈), zerolatency(실시간)")

	def _populate_codecs(self) -> None:
		"""Populate codec lists with available encoders."""
		try:
			from ..utils.ffmpeg_check import get_recommended_codecs
			codecs = get_recommended_codecs()
			
			# Add video codecs
			video_codecs = codecs.get("video", [])
			if video_codecs:
				self.video_codec.clear()
				self.video_codec.addItems(video_codecs)
			else:
				# Fallback to common codecs
				self.video_codec.addItems(["libx264", "libx265", "libvpx-vp9", "libaom-av1", "prores_ks", "dnxhd", "h264_nvenc", "hevc_nvenc", "h264_qsv", "hevc_qsv"])
		except Exception:
			# Fallback to common codecs
			self.video_codec.addItems(["libx264", "libx265", "libvpx-vp9", "libaom-av1", "prores_ks", "dnxhd", "h264_nvenc", "hevc_nvenc", "h264_qsv", "hevc_qsv"])


	def _populate_audio_codecs(self) -> None:
		"""Populate audio codec list with available encoders."""
		try:
			from ..utils.ffmpeg_check import get_recommended_codecs
			codecs = get_recommended_codecs()
			
			# Add audio codecs
			audio_codecs = codecs.get("audio", [])
			if audio_codecs:
				self.audio_codec.clear()
				self.audio_codec.addItems(audio_codecs)
			else:
				# Fallback to common codecs
				self.audio_codec.addItems(["aac", "libmp3lame", "libopus", "libvorbis", "ac3", "flac", "pcm_s16le"])
		except Exception:
			# Fallback to common codecs
			self.audio_codec.addItems(["aac", "libmp3lame", "libopus", "libvorbis", "ac3", "flac", "pcm_s16le"])


	def _build_flamenco_tab(self) -> QWidget:
		w = QWidget()
		form = QFormLayout(w)
		
		# Flamenco path selection
		self.flamenco_path = QLineEdit()
		self.flamenco_path.setPlaceholderText("Select Flamenco installation path")
		self.browse_flamenco_btn = QPushButton("Browse Flamenco Path")
		self.browse_flamenco_btn.clicked.connect(self._browse_flamenco_path)
		
		# Auto config button
		self.auto_config_btn = QPushButton("Auto Load Config")
		self.auto_config_btn.clicked.connect(self._auto_load_flamenco_config)
		self.auto_config_btn.setEnabled(False)
		
		# Flamenco setup button
		self.setup_flamenco_btn = QPushButton("Setup Flamenco for FFmpeg")
		self.setup_flamenco_btn.clicked.connect(self._setup_flamenco_for_ffmpeg)
		self.setup_flamenco_btn.setEnabled(False)
		
		# Manual settings
		self.flamenco_base_url = QLineEdit()
		self.flamenco_base_url.setPlaceholderText("http://localhost:8080")
		self.flamenco_token = QLineEdit()
		self.flamenco_token.setPlaceholderText("API token")
		self.flamenco_token.setEchoMode(QLineEdit.Password)
		
		# Status display
		self.flamenco_status = QLabel("Select Flamenco path")
		self.flamenco_status.setStyleSheet("color: gray;")
		
		form.addRow("Flamenco Path", self.flamenco_path)
		form.addRow("", self.browse_flamenco_btn)
		form.addRow("", self.auto_config_btn)
		form.addRow("", self.setup_flamenco_btn)
		form.addRow("", self.flamenco_status)
		form.addRow("", QLabel("Or configure manually:"))
		form.addRow("Base URL", self.flamenco_base_url)
		form.addRow("API Token", self.flamenco_token)
		
		# 경로 변경 시 자동 설정 버튼 활성화
		self.flamenco_path.textChanged.connect(self._on_flamenco_path_changed)
		
		# 설정 변경 시 자동 저장
		self.flamenco_base_url.textChanged.connect(self._save_flamenco_config)
		self.flamenco_token.textChanged.connect(self._save_flamenco_config)
		self.flamenco_path.textChanged.connect(self._save_flamenco_config)
		
		# 초기 설정 불러오기
		self._load_flamenco_config()
		
		return w

	def _browse_flamenco_path(self) -> None:
		"""Flamenco 설치 경로를 선택합니다."""
		folder = QFileDialog.getExistingDirectory(self, "Flamenco 설치 경로 선택")
		if folder:
			self.flamenco_path.setText(folder)
			self._on_flamenco_path_changed()

	def _on_flamenco_path_changed(self) -> None:
		"""Flamenco 경로가 변경되었을 때 호출됩니다."""
		path = self.flamenco_path.text().strip()
		if path and os.path.exists(path):
			self.auto_config_btn.setEnabled(True)
			self.setup_flamenco_btn.setEnabled(True)
			self.flamenco_status.setText("경로가 선택되었습니다. '자동 설정 불러오기' 또는 'Flamenco FFmpeg 호환 설정'을 클릭하세요.")
			self.flamenco_status.setStyleSheet("color: blue;")
		else:
			self.auto_config_btn.setEnabled(False)
			self.setup_flamenco_btn.setEnabled(False)
			if path:
				self.flamenco_status.setText("경로가 존재하지 않습니다.")
				self.flamenco_status.setStyleSheet("color: red;")
			else:
				self.flamenco_status.setText("Flamenco 경로를 선택하세요")
				self.flamenco_status.setStyleSheet("color: gray;")

	def _auto_load_flamenco_config(self) -> None:
		"""Flamenco 설정을 자동으로 불러옵니다."""
		path = self.flamenco_path.text().strip()
		if not path:
			return
		
		try:
			from ..integrations.flamenco_client import load_flamenco_config
			config = load_flamenco_config(path)
			
			if config.success:
				self.flamenco_base_url.setText(config.base_url)
				self.flamenco_token.setText(config.token)
				self.flamenco_status.setText(f"✅ 설정 완료: {config.manager_name} (포트: {config.listen_port})")
				self.flamenco_status.setStyleSheet("color: green;")
			else:
				self.flamenco_status.setText(f"❌ 오류: {config.error_message}")
				self.flamenco_status.setStyleSheet("color: red;")
				
		except Exception as e:
			self.flamenco_status.setText(f"❌ 오류: {str(e)}")
			self.flamenco_status.setStyleSheet("color: red;")

	def _setup_flamenco_for_ffmpeg(self) -> None:
		"""Flamenco를 FFmpeg Encoder와 호환되도록 설정합니다."""
		path = self.flamenco_path.text().strip()
		if not path:
			return
		
		try:
			from ..integrations.flamenco_client import setup_flamenco_for_ffmpeg
			config = setup_flamenco_for_ffmpeg(path)
			
			if config.success:
				# 설정도 자동으로 불러오기
				self.flamenco_base_url.setText(config.base_url)
				self.flamenco_token.setText(config.token)
				self.flamenco_status.setText(f"✅ Flamenco FFmpeg 호환 설정 완료! {config.manager_name} (포트: {config.listen_port})")
				self.flamenco_status.setStyleSheet("color: green;")
			else:
				self.flamenco_status.setText(f"❌ 설정 오류: {config.error_message}")
				self.flamenco_status.setStyleSheet("color: red;")
				
		except Exception as e:
			self.flamenco_status.setText(f"❌ 오류: {str(e)}")
			self.flamenco_status.setStyleSheet("color: red;")

	def _save_flamenco_config(self) -> None:
		"""Flamenco 설정을 자동으로 저장합니다."""
		try:
			config = {
				"flamenco_path": self.flamenco_path.text(),
				"base_url": self.flamenco_base_url.text(),
				"token": self.flamenco_token.text()
			}
			
			with open(self.flamenco_config_path, 'w', encoding='utf-8') as f:
				json.dump(config, f, indent=2, ensure_ascii=False)
				
		except Exception as e:
			print(f"Flamenco 설정 저장 오류: {e}")

	def _load_flamenco_config(self) -> None:
		"""Flamenco 설정을 자동으로 불러옵니다."""
		try:
			if self.flamenco_config_path.exists():
				with open(self.flamenco_config_path, 'r', encoding='utf-8') as f:
					config = json.load(f)
				
				# 설정 복원
				if "flamenco_path" in config:
					self.flamenco_path.setText(config["flamenco_path"])
				if "base_url" in config:
					self.flamenco_base_url.setText(config["base_url"])
				if "token" in config:
					self.flamenco_token.setText(config["token"])
				
				# 상태 업데이트
				if config.get("base_url") and config.get("token"):
					self.flamenco_status.setText("✅ 저장된 설정이 복원되었습니다")
					self.flamenco_status.setStyleSheet("color: green;")
				else:
					self.flamenco_status.setText("Flamenco 경로를 선택하세요")
					self.flamenco_status.setStyleSheet("color: gray;")
					
		except Exception as e:
			print(f"Flamenco 설정 불러오기 오류: {e}")
			self.flamenco_status.setText("Flamenco 경로를 선택하세요")
			self.flamenco_status.setStyleSheet("color: gray;")

	def _on_crf_changed(self) -> None:
		"""Handle CRF value change - disable bitrate when CRF is used."""
		crf_value = self.crf.value()
		# CRF 0-51 is valid range, disable bitrate when CRF is used
		if 0 <= crf_value <= 51:
			self.bitrate.setEnabled(False)
			self.bitrate.setPlaceholderText("Bitrate disabled when using CRF")
		else:
			self.bitrate.setEnabled(True)
			self.bitrate.setPlaceholderText("e.g. 8M or 2000k")

	def _on_container_changed(self) -> None:
		"""Handle container format change - update available codecs."""
		container = self.container_format.currentText()
		self._populate_user_friendly_codecs(container)

