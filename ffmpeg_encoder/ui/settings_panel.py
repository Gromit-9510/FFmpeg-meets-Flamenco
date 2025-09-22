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
	QListWidget,
	QListWidgetItem,
	QMessageBox,
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
		tabs.addTab(self._build_video_tab(), "Settings")
		tabs.addTab(self._build_flamenco_tab(), "Flamenco")
		tabs.addTab(self._build_guide_tab(), "Guide")
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
		self.multi_encode_btn = QPushButton("Multi-Encode")
		self.submit_flamenco_btn = QPushButton("Submit to Flamenco")
		layout.addWidget(self.encode_btn)
		layout.addWidget(self.multi_encode_btn)
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
		
		self.crf = QSpinBox()
		self.crf.setRange(0, 51)
		self.crf.setValue(18)
		self.crf.setToolTip("0=lossless, 18=high quality, 23=default, 28=low quality, 51=lowest quality")
		self.crf.valueChanged.connect(self._on_crf_changed)
		
		self.bitrate = QLineEdit()
		self.bitrate.setPlaceholderText("e.g. 8M or 2000k")
		self.bitrate.setToolTip("Bitrate (e.g. 8M, 2000k)")
		
		quality_layout.addRow("CRF (Quality):", self.crf)
		quality_layout.addRow("Bitrate:", self.bitrate)
		layout.addWidget(quality_group)
		
		
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
		
		self.extra_params = QLineEdit()
		self.extra_params.setPlaceholderText("Additional FFmpeg params, e.g. -preset slow -tune film")
		self.extra_params.setToolTip("Additional FFmpeg parameters")
		
		advanced_layout.addRow("Max File Size:", self.max_filesize)
		advanced_layout.addRow("Extra Params:", self.extra_params)
		layout.addWidget(advanced_group)
		
		# Multi-encode settings
		multi_group = QGroupBox("Multi-Encode Settings")
		multi_layout = QVBoxLayout(multi_group)
		
		# 설명
		info_label = QLabel("여러 설정으로 순차 인코딩할 수 있습니다. 예: h264 CRF 20, h264 CRF 30")
		info_label.setWordWrap(True)
		info_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
		multi_layout.addWidget(info_label)
		
		# 설정 목록
		self.multi_settings_list = QListWidget()
		self.multi_settings_list.setMaximumHeight(150)
		multi_layout.addWidget(self.multi_settings_list)
		
		# 버튼들
		button_layout = QHBoxLayout()
		self.add_setting_btn = QPushButton("Add Current Settings")
		self.remove_setting_btn = QPushButton("Remove Selected")
		self.clear_settings_btn = QPushButton("Clear All")
		
		button_layout.addWidget(self.add_setting_btn)
		button_layout.addWidget(self.remove_setting_btn)
		button_layout.addWidget(self.clear_settings_btn)
		multi_layout.addLayout(button_layout)
		
		layout.addWidget(multi_group)
		
		# 연결
		self.add_setting_btn.clicked.connect(self._add_current_settings)
		self.remove_setting_btn.clicked.connect(self._remove_selected_setting)
		self.clear_settings_btn.clicked.connect(self._clear_all_settings)
		
		layout.addStretch()
		return w

	def _populate_user_friendly_codecs(self, container: str = None) -> None:
		"""Populate codec lists with user-friendly names."""
		# Store codec data for later use
		self.codec_data = {}
		
		# Clear existing codecs
		self.video_codec.clear()
		
		# Always add comprehensive fallback codecs
		fallback_codecs = [
			{"id": "libx264", "name": "libx264 (CPU)", "description": ""},
			{"id": "libx264_ll", "name": "libx264 (CPU) Low Latency", "description": "low latency"},
			{"id": "h264_nvenc", "name": "H.264 (GPU)", "description": ""},
			{"id": "h264_nvenc_ll", "name": "H.264 (GPU) Low Latency", "description": "low latency"},
			{"id": "separator1", "name": "─────────────────────────", "description": "", "separator": True},
			{"id": "libx265", "name": "libx265 (CPU)", "description": ""},
			{"id": "libx265_ll", "name": "libx265 (CPU) Low Latency", "description": "low latency"},
			{"id": "hevc_nvenc", "name": "H.265 (GPU)", "description": ""},
			{"id": "hevc_nvenc_ll", "name": "H.265 (GPU) Low Latency", "description": "low latency"},
			{"id": "separator2", "name": "─────────────────────────", "description": "", "separator": True},
			{"id": "libvpx-vp9", "name": "libvpx-vp9 (CPU)", "description": ""},
			{"id": "libaom-av1", "name": "libaom-av1 (CPU)", "description": ""},
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
		
		
		# Update CRF visibility only if crf is initialized
		if hasattr(self, 'crf'):
			self._update_crf_visibility()
	
	
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
								label.setText("CRF (Quality):")
								label.setVisible(True)
							elif supports_qp:
								label.setText("QP (Quality):")
								label.setVisible(True)
							else:
								label.setVisible(False)
							break


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

	def _build_guide_tab(self) -> QWidget:
		w = QWidget()
		layout = QVBoxLayout(w)
		
		guide_text = QLabel("""
		<h2>FFmpeg Encoder 사용법</h2>
		
		<h3>1. 파일 추가</h3>
		<p>• <b>Add Files:</b> 개별 비디오 파일 선택</p>
		<p>• <b>Add Folder:</b> 폴더 내 모든 비디오 파일 자동 추가</p>
		
		<h3>2. 파일 선택</h3>
		<p>• 체크박스로 인코딩할 파일 선택</p>
		<p>• <b>CTRL/Shift:</b> 다중선택</p>
		<p>• <b>Select All/Deselect All:</b> 전체 선택/해제</p>
		
		<h3>3. 인코딩 설정</h3>
		<p>• <b>Video:</b> 코덱, 품질(CRF/QP), 저지연 모드</p>
		<p>• <b>Audio:</b> 오디오 코덱, 비트레이트</p>
		<p>• <b>Flamenco:</b> 분산 인코딩 설정</p>
		
		<h3>4. 인코딩 실행</h3>
		<p>• <b>Encode with FFmpeg:</b> 로컬 인코딩</p>
		<p>• <b>Submit to Flamenco:</b> 분산 인코딩</p>
		<p>• 출력 설정 다이얼로그에서 폴더, 파일명 패턴 설정</p>
		
		<h3>5. 큐 관리</h3>
		<p>• <b>Remove Checked:</b> 체크된 항목 삭제</p>
		<p>• <b>Batch Rename:</b> 체크된 파일 일괄 이름변경</p>
		<p>• <b>Select All/Deselect All:</b> 전체 선택/해제</p>
		
		<h3>6. 프리셋</h3>
		<p>• 자주 사용하는 설정을 프리셋으로 저장/불러오기</p>
		<p>• Export/Import로 프리셋 공유 가능</p>
		""")
		guide_text.setWordWrap(True)
		guide_text.setStyleSheet("padding: 20px; line-height: 1.5;")
		layout.addWidget(guide_text)
		
		layout.addStretch()
		return w

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

	def _get_user_friendly_codec_name(self, codec_id: str) -> str:
		"""코덱 ID를 사용자 친화적인 이름으로 변환합니다."""
		if hasattr(self, 'codec_data') and codec_id in self.codec_data:
			return self.codec_data[codec_id]['name']
		
		# Fallback: codec_id를 그대로 반환
		return codec_id

	def _add_current_settings(self) -> None:
		"""현재 설정을 목록에 추가합니다."""
		settings = self.get_settings()
		
		# 사용자 친화적인 코덱 이름 가져오기
		codec_id = settings["video_codec"]
		codec_name = self._get_user_friendly_codec_name(codec_id)
		crf = settings["crf"]
		bitrate = settings["bitrate"]
		
		if bitrate:
			name = f"{codec_name} - {bitrate}"
		else:
			name = f"{codec_name} - CRF {crf}"
		
		# 중복 확인
		for i in range(self.multi_settings_list.count()):
			item = self.multi_settings_list.item(i)
			if item.text() == name:
				QMessageBox.warning(self, "Warning", "이미 동일한 설정이 있습니다.")
				return
		
		# 추가
		item = QListWidgetItem(name)
		item.setData(Qt.UserRole, settings)
		self.multi_settings_list.addItem(item)

	def _remove_selected_setting(self) -> None:
		"""선택된 설정을 제거합니다."""
		current_row = self.multi_settings_list.currentRow()
		if current_row >= 0:
			self.multi_settings_list.takeItem(current_row)

	def _clear_all_settings(self) -> None:
		"""모든 설정을 제거합니다."""
		self.multi_settings_list.clear()

	def get_multi_settings(self) -> list:
		"""여러 설정 목록을 반환합니다."""
		settings_list = []
		for i in range(self.multi_settings_list.count()):
			item = self.multi_settings_list.item(i)
			settings = item.data(Qt.UserRole)
			settings_list.append(settings)
		return settings_list

	def get_settings(self) -> dict:
		"""현재 설정을 딕셔너리로 반환합니다."""
		# Get video codec ID from user-friendly selection
		video_codec_data = self.video_codec.currentData()
		video_codec = video_codec_data if video_codec_data else self.video_codec.currentText()
		
		# GPU enable is determined by codec selection
		gpu_enable = "nvenc" in video_codec
		
		# Low latency is determined by codec selection
		low_latency = "_ll" in video_codec
		
		return {
			"container": self.container_format.currentText(),
			"video_codec": video_codec,
			"crf": self.crf.value(),
			"bitrate": self.bitrate.text().strip() or None,
			"gpu_enable": gpu_enable,
			"low_latency": low_latency,
			"tune": "none",  # Not used anymore
			"audio_codec": self.audio_codec.currentText(),
			"audio_bitrate": self.audio_bitrate.text().strip() or None,
			"max_filesize": getattr(self, 'max_filesize', QLineEdit()).text().strip() or None,
		}

	def set_settings(self, settings: dict) -> None:
		"""딕셔너리로 설정을 적용합니다."""
		if "container" in settings:
			self.container_format.setCurrentText(settings["container"])
		if "video_codec" in settings:
			# Set video codec by finding the matching item
			for i in range(self.video_codec.count()):
				if self.video_codec.itemData(i) == settings["video_codec"]:
					self.video_codec.setCurrentIndex(i)
					break
			else:
				# Fallback to text matching
				self.video_codec.setCurrentText(settings["video_codec"])
		if "crf" in settings:
			self.crf.setValue(settings["crf"])
		if "bitrate" in settings:
			self.bitrate.setText(settings["bitrate"] or "")
		if "audio_codec" in settings:
			self.audio_codec.setCurrentText(settings["audio_codec"])
		if "audio_bitrate" in settings:
			self.audio_bitrate.setText(settings["audio_bitrate"] or "")
		if "max_filesize" in settings and hasattr(self, 'max_filesize'):
			self.max_filesize.setText(settings["max_filesize"] or "")

