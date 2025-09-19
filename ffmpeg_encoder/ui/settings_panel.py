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
		tabs.addTab(self._build_video_tab(), "Video")
		tabs.addTab(self._build_audio_tab(), "Audio")
		tabs.addTab(self._build_output_tab(), "Output")
		tabs.addTab(self._build_flamenco_tab(), "Flamenco")
		tabs.addTab(self._build_advanced_tab(), "Advanced")
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
		container_group = QGroupBox("컨테이너 형식")
		container_layout = QFormLayout(container_group)
		self.container_format = QComboBox()
		self.container_format.addItems(["mp4", "mkv", "mov", "avi", "webm"])
		container_layout.addRow("형식:", self.container_format)
		layout.addWidget(container_group)
		
		# Video codec selection
		codec_group = QGroupBox("비디오 코덱")
		codec_layout = QVBoxLayout(codec_group)
		
		self.video_codec = QComboBox()
		self.codec_description = QLabel("코덱을 선택하세요")
		self.codec_description.setWordWrap(True)
		self.codec_description.setStyleSheet("color: #666; font-size: 11px;")
		
		# Populate codecs
		self._populate_user_friendly_codecs()
		
		# Connect codec change to update description
		self.video_codec.currentTextChanged.connect(self._on_codec_changed)
		
		codec_layout.addWidget(QLabel("코덱:"))
		codec_layout.addWidget(self.video_codec)
		codec_layout.addWidget(self.codec_description)
		layout.addWidget(codec_group)
		
		# Quality settings
		quality_group = QGroupBox("품질 설정")
		quality_layout = QFormLayout(quality_group)
		
		self.crf = QSpinBox()
		self.crf.setRange(0, 51)
		self.crf.setValue(18)
		self.crf.setToolTip("0=무손실, 18=고품질, 23=기본, 28=저품질, 51=최저품질")
		
		self.bitrate = QLineEdit()
		self.bitrate.setPlaceholderText("예: 8M 또는 2000k")
		self.bitrate.setToolTip("비트레이트 (예: 8M, 2000k)")
		
		quality_layout.addRow("CRF (품질):", self.crf)
		quality_layout.addRow("비트레이트:", self.bitrate)
		layout.addWidget(quality_group)
		
		# Encoding options
		options_group = QGroupBox("인코딩 옵션")
		options_layout = QVBoxLayout(options_group)
		
		self.two_pass = QCheckBox("2패스 인코딩 (더 정확한 비트레이트 제어)")
		self.two_pass.setToolTip("첫 번째 패스에서 분석, 두 번째 패스에서 인코딩")
		self.two_pass.stateChanged.connect(self._on_two_pass_changed)
		
		options_layout.addWidget(self.two_pass)
		layout.addWidget(options_group)
		
		layout.addStretch()
		return w

	def _populate_user_friendly_codecs(self) -> None:
		"""Populate codec lists with user-friendly names."""
		try:
			from ..utils.ffmpeg_check import get_user_friendly_codecs
			codecs = get_user_friendly_codecs()
			
			# Store codec data for later use
			self.codec_data = {}
			
			# Add video codecs
			video_codecs = codecs.get("video", [])
			for codec in video_codecs:
				display_name = f"{codec['name']} - {codec['description']}"
				self.video_codec.addItem(display_name, codec['id'])
				self.codec_data[codec['id']] = codec
			
			# Set default selection
			if video_codecs:
				self.video_codec.setCurrentIndex(0)
				self._on_codec_changed()
				
		except Exception as e:
			print(f"Error populating codecs: {e}")
			# Fallback to basic codecs
			self.video_codec.addItem("H.264 (x264) - 고품질 H.264 인코딩 (CPU)", "libx264")
			self.video_codec.addItem("H.265/HEVC (x265) - 고품질 H.265 인코딩 (CPU)", "libx265")

	def _on_codec_changed(self) -> None:
		"""Handle codec selection change."""
		current_data = self.video_codec.currentData()
		if current_data and hasattr(self, 'codec_data') and current_data in self.codec_data:
			codec_info = self.codec_data[current_data]
			self.codec_description.setText(codec_info['description'])
		else:
			self.codec_description.setText("코덱을 선택하세요")
		
		# Check 2-pass compatibility only if two_pass is initialized
		if hasattr(self, 'two_pass'):
			self._check_two_pass_compatibility()
		
		# Update CRF visibility only if crf is initialized
		if hasattr(self, 'crf'):
			self._update_crf_visibility()
	
	def _on_two_pass_changed(self) -> None:
		"""Handle 2-pass checkbox change."""
		self._check_two_pass_compatibility()
	
	def _update_crf_visibility(self) -> None:
		"""Update CRF/QP visibility based on selected codec."""
		current_data = self.video_codec.currentData()
		if not current_data:
			return
		
		# Extract base codec name (remove _ll suffix for low latency)
		base_codec = current_data.replace("_ll", "")
		
		# CRF is only supported for libx264 and libx265
		supports_crf = base_codec in ["libx264", "libx265"]
		supports_qp = base_codec in ["h264_nvenc", "hevc_nvenc"]
		
		# Show/hide CRF control and its label
		self.crf.setVisible(supports_crf or supports_qp)
		# Find the CRF label in the quality group
		quality_group = self.crf.parent()
		if quality_group:
			layout = quality_group.layout()
			if layout:
				for i in range(layout.rowCount()):
					label_item = layout.itemAt(i, QFormLayout.LabelRole)  # Get label using correct signature
					if label_item and label_item.widget():
						label = label_item.widget()
						if isinstance(label, QLabel) and ("CRF" in label.text() or "QP" in label.text()):
							if supports_crf:
								label.setText("CRF (품질):")
								label.setVisible(True)
							elif supports_qp:
								label.setText("QP (품질):")
								label.setVisible(True)
							else:
								label.setVisible(False)
							break

	def _check_two_pass_compatibility(self) -> None:
		"""Check if current codec supports 2-pass encoding."""
		if not self.two_pass.isChecked():
			return
		
		current_data = self.video_codec.currentData()
		if not current_data:
			return
		
		# Get base codec (remove _ll suffix if present)
		base_codec = current_data.replace("_ll", "")
		
		# Check if codec supports 2-pass
		supports_two_pass = base_codec in ["libx264", "libx265", "h264_nvenc", "hevc_nvenc"]
		
		if not supports_two_pass:
			from PySide6.QtWidgets import QMessageBox
			QMessageBox.warning(
				self, 
				"2패스 인코딩 지원 안함", 
				f"선택한 코덱 '{current_data}'은 2패스 인코딩을 지원하지 않습니다.\n"
				f"2패스 인코딩은 libx264, libx265, h264_nvenc, hevc_nvenc에서만 사용 가능합니다."
			)
			self.two_pass.setChecked(False)

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

	def _build_audio_tab(self) -> QWidget:
		w = QWidget()
		form = QFormLayout(w)
		self.audio_codec = QComboBox()
		# Will be populated with available audio codecs
		self._populate_audio_codecs()
		self.audio_bitrate = QLineEdit()
		self.audio_bitrate.setPlaceholderText("e.g. 192k")
		form.addRow("Audio codec", self.audio_codec)
		form.addRow("Audio bitrate", self.audio_bitrate)
		return w

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

	def _build_output_tab(self) -> QWidget:
		w = QWidget()
		form = QFormLayout(w)
		
		# Output path settings
		self.output_mode = QComboBox()
		self.output_mode.addItems(["Global", "Individual"])
		self.output_mode.setCurrentText("Global")
		
		self.global_output_path = QLineEdit()
		self.global_output_path.setPlaceholderText("Select global output folder")
		self.browse_output_btn = QPushButton("Browse...")
		
		# Output filename pattern
		self.filename_pattern = QLineEdit()
		self.filename_pattern.setText("{name}_{codec}_{quality}")
		self.filename_pattern.setPlaceholderText("e.g., {name}_{codec}_{quality}")
		
		# Overwrite options
		self.overwrite_mode = QComboBox()
		self.overwrite_mode.addItems(["Ask", "Skip", "Overwrite", "Rename"])
		self.overwrite_mode.setCurrentText("Ask")
		
		# Connect browse button
		self.browse_output_btn.clicked.connect(self._browse_output_folder)
		
		form.addRow("Output Mode", self.output_mode)
		form.addRow("Global Output Path", self.global_output_path)
		form.addRow("", self.browse_output_btn)
		form.addRow("Filename Pattern", self.filename_pattern)
		form.addRow("If File Exists", self.overwrite_mode)
		
		return w

	def _browse_output_folder(self) -> None:
		folder = QFileDialog.getExistingDirectory(self, "Select output folder")
		if folder:
			self.global_output_path.setText(folder)

	def _build_flamenco_tab(self) -> QWidget:
		w = QWidget()
		form = QFormLayout(w)
		
		# Flamenco 경로 선택
		self.flamenco_path = QLineEdit()
		self.flamenco_path.setPlaceholderText("Flamenco 설치 경로를 선택하세요")
		self.browse_flamenco_btn = QPushButton("Flamenco 경로 선택")
		self.browse_flamenco_btn.clicked.connect(self._browse_flamenco_path)
		
		# 자동 설정 버튼
		self.auto_config_btn = QPushButton("자동 설정 불러오기")
		self.auto_config_btn.clicked.connect(self._auto_load_flamenco_config)
		self.auto_config_btn.setEnabled(False)
		
		# Flamenco 설정 버튼
		self.setup_flamenco_btn = QPushButton("Flamenco FFmpeg 호환 설정")
		self.setup_flamenco_btn.clicked.connect(self._setup_flamenco_for_ffmpeg)
		self.setup_flamenco_btn.setEnabled(False)
		
		# 수동 설정
		self.flamenco_base_url = QLineEdit()
		self.flamenco_base_url.setPlaceholderText("http://localhost:8080")
		self.flamenco_token = QLineEdit()
		self.flamenco_token.setPlaceholderText("API token")
		self.flamenco_token.setEchoMode(QLineEdit.Password)
		
		# 상태 표시
		self.flamenco_status = QLabel("Flamenco 경로를 선택하세요")
		self.flamenco_status.setStyleSheet("color: gray;")
		
		form.addRow("Flamenco 경로", self.flamenco_path)
		form.addRow("", self.browse_flamenco_btn)
		form.addRow("", self.auto_config_btn)
		form.addRow("", self.setup_flamenco_btn)
		form.addRow("", self.flamenco_status)
		form.addRow("", QLabel("또는 수동으로 설정:"))
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

	def _build_advanced_tab(self) -> QWidget:
		w = QWidget()
		form = QFormLayout(w)
		self.max_filesize = QLineEdit()
		self.max_filesize.setPlaceholderText("e.g. 700M")
		self.extra_params = QLineEdit()
		self.extra_params.setPlaceholderText("Additional FFmpeg params, e.g. -preset slow -tune film")
		form.addRow("Max file size", self.max_filesize)
		form.addRow("Extra params", self.extra_params)
		return w
