from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QGroupBox,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QMessageBox,
    QDialogButtonBox,
    QFileDialog,
    QComboBox,
    QSpinBox,
    QSplitter,
)
from PySide6.QtCore import Qt

from ..core.ffmpeg_cmd import VideoSettings
from ..utils.ffmpeg_check import get_compatible_gpu_encoders


class MultiEncodingDialog(QDialog):
    def __init__(self, input_files: List[str], current_settings: VideoSettings, parent=None) -> None:
        super().__init__(parent)
        self.input_files = input_files
        self.current_settings = current_settings
        self.encoding_configs: List[VideoSettings] = []
        
        self.setWindowTitle("Multi-Encoding Setup")
        self.setModal(True)
        self.resize(800, 600)
        
        self._setup_ui()
        self._populate_current_settings()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        # Input files info
        info_group = QGroupBox("Input Files")
        info_layout = QVBoxLayout(info_group)
        self.files_label = QLabel(f"Files to encode: {len(self.input_files)}")
        info_layout.addWidget(self.files_label)
        
        # Show file list
        self.files_list = QListWidget()
        self.files_list.setMaximumHeight(100)
        for file_path in self.input_files:
            self.files_list.addItem(Path(file_path).name)
        info_layout.addWidget(self.files_list)
        layout.addWidget(info_group)
        
        # Splitter for settings and config list
        splitter = QSplitter()
        
        # Left side: Current settings panel
        settings_group = QGroupBox("Current Settings")
        settings_layout = QVBoxLayout(settings_group)
        
        # Settings form
        self.settings_form = QFormLayout()
        
        # Container format
        self.container_combo = QComboBox()
        self.container_combo.addItems(["mp4", "mkv", "mov", "avi", "webm"])
        self.settings_form.addRow("Container:", self.container_combo)
        
        # Video codec
        self.video_codec_combo = QComboBox()
        self._populate_video_codecs()
        self.settings_form.addRow("Video Codec:", self.video_codec_combo)
        
        # CRF/QP
        self.crf_spin = QSpinBox()
        self.crf_spin.setRange(0, 51)
        self.crf_spin.setValue(18)
        self.crf_label = QLabel("CRF:")
        self.settings_form.addRow(self.crf_label, self.crf_spin)
        
        # Connect codec change to update label and advanced settings
        self.video_codec_combo.currentTextChanged.connect(self._on_codec_changed)
        self.video_codec_combo.currentIndexChanged.connect(self._on_codec_changed)
        
        # Bitrate
        self.bitrate_edit = QLineEdit()
        self.bitrate_edit.setPlaceholderText("e.g. 8M or 2000k")
        self.settings_form.addRow("Bitrate:", self.bitrate_edit)
        
        # Audio codec
        self.audio_codec_combo = QComboBox()
        self.audio_codec_combo.addItems(["aac", "libmp3lame", "libopus", "libvorbis", "ac3", "flac", "pcm_s16le"])
        self.settings_form.addRow("Audio Codec:", self.audio_codec_combo)
        
        # Audio bitrate
        self.audio_bitrate_edit = QLineEdit()
        self.audio_bitrate_edit.setPlaceholderText("e.g. 192k")
        self.settings_form.addRow("Audio Bitrate:", self.audio_bitrate_edit)
        
        # Advanced settings
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "ultrafast", "superfast", "veryfast", "faster", "fast", 
            "medium", "slow", "slower", "veryslow", "placebo"
        ])
        self.preset_combo.setCurrentText("medium")
        self.preset_combo.setToolTip("인코딩 속도 vs 압축률: ultrafast(빠름) → placebo(느림, 고압축)")
        self.settings_form.addRow("Preset:", self.preset_combo)
        
        self.tune_combo = QComboBox()
        self.tune_combo.addItems([
            "none", "film", "animation", "grain", "stillimage", 
            "fastdecode", "zerolatency", "psnr", "ssim"
        ])
        self.tune_combo.setCurrentText("none")
        self.tune_combo.setToolTip("최적화 타입: film(영화), animation(애니메이션), grain(노이즈), zerolatency(실시간)")
        self.settings_form.addRow("Tune:", self.tune_combo)
        
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["auto", "baseline", "main", "high", "high10", "high422", "high444"])
        self.profile_combo.setCurrentText("auto")
        self.profile_combo.setToolTip("프로파일: baseline(호환성), main(기본), high(고품질), auto(자동선택)")
        self.settings_form.addRow("Profile:", self.profile_combo)
        
        self.level_combo = QComboBox()
        self.level_combo.addItems(["auto", "3.0", "3.1", "3.2", "4.0", "4.1", "4.2", "5.0", "5.1", "5.2"])
        self.level_combo.setCurrentText("auto")
        self.level_combo.setToolTip("레벨: 디코더 호환성 (auto=자동선택)")
        self.settings_form.addRow("Level:", self.level_combo)
        
        # Checkboxes
        self.two_pass_check = QCheckBox("2-Pass Encoding")
        self.two_pass_check.setToolTip("2단계 인코딩: 더 정확한 비트레이트 제어 (CPU 코덱만 지원)")
        self.settings_form.addRow("", self.two_pass_check)
        
        
        settings_layout.addLayout(self.settings_form)
        
        # Add to config button
        self.add_config_btn = QPushButton("Add Current Settings to List")
        self.add_config_btn.clicked.connect(self._add_current_settings)
        settings_layout.addWidget(self.add_config_btn)
        
        splitter.addWidget(settings_group)
        
        # Right side: Config list
        config_group = QGroupBox("Encoding Configurations")
        config_layout = QVBoxLayout(config_group)
        
        config_layout.addWidget(QLabel("Configurations to encode:"))
        self.config_list = QListWidget()
        config_layout.addWidget(self.config_list)
        
        # Config buttons
        config_btn_layout = QHBoxLayout()
        self.remove_config_btn = QPushButton("Remove Selected")
        self.clear_config_btn = QPushButton("Clear All")
        self.remove_config_btn.clicked.connect(self._remove_selected_config)
        self.clear_config_btn.clicked.connect(self._clear_all_configs)
        config_btn_layout.addWidget(self.remove_config_btn)
        config_btn_layout.addWidget(self.clear_config_btn)
        config_layout.addLayout(config_btn_layout)
        
        splitter.addWidget(config_group)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
        
        # Output settings
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout(output_group)
        
        self.output_dir = QLineEdit()
        self.output_dir.setPlaceholderText("Output directory (leave empty for same as input)")
        self.browse_output_btn = QPushButton("Browse...")
        self.browse_output_btn.clicked.connect(self._browse_output_dir)
        
        output_layout.addRow("Output Directory:", self.output_dir)
        output_layout.addRow("", self.browse_output_btn)
        
        self.add_config_suffix = QCheckBox("Add config number as suffix")
        self.add_config_suffix.setChecked(True)
        output_layout.addRow("", self.add_config_suffix)
        
        layout.addWidget(output_group)
        
        # Summary
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("color: blue; font-weight: bold;")
        layout.addWidget(self.summary_label)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self._update_summary()

    def _populate_video_codecs(self) -> None:
        """Populate video codec list with user-friendly names."""
        # Store codec data for later use
        self.codec_data = {}
        
        # Clear existing codecs
        self.video_codec_combo.clear()
        
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
            self.video_codec_combo.addItem(display_name, codec['id'])
            self.codec_data[codec['id']] = codec

    def _on_codec_changed(self) -> None:
        """Handle codec selection change and update CRF/QP label and advanced settings."""
        current_data = self.video_codec_combo.currentData()
        if not current_data:
            return
        
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
        
        # Update advanced settings
        self._update_advanced_settings(current_data)
    
    def _update_advanced_settings(self, codec_id: str) -> None:
        """Update advanced settings based on selected codec."""
        is_cpu_codec = codec_id.startswith("libx")
        is_gpu_codec = "nvenc" in codec_id
        
        # 2-pass encoding only for CPU codecs
        self.two_pass_check.setEnabled(is_cpu_codec)
        if not is_cpu_codec:
            self.two_pass_check.setChecked(False)
        
        # Update preset options based on codec
        if is_gpu_codec:
            # GPU codecs have different presets
            self.preset_combo.clear()
            self.preset_combo.addItems(["p1", "p2", "p3", "p4", "p5", "p6", "p7"])
            self.preset_combo.setCurrentText("p4")
            self.preset_combo.setToolTip("NVENC 프리셋: p1(최고속도) → p7(최고품질)")
        else:
            # CPU codecs use standard presets
            self.preset_combo.clear()
            self.preset_combo.addItems([
                "ultrafast", "superfast", "veryfast", "faster", "fast", 
                "medium", "slow", "slower", "veryslow", "placebo"
            ])
            self.preset_combo.setCurrentText("medium")
            self.preset_combo.setToolTip("인코딩 속도 vs 압축률: ultrafast(빠름) → placebo(느림, 고압축)")
        
        # Update tune options based on codec
        if is_gpu_codec:
            # GPU codecs have limited tune options
            self.tune_combo.clear()
            self.tune_combo.addItems(["none", "hq", "ll", "ull"])
            self.tune_combo.setCurrentText("none")
            self.tune_combo.setToolTip("NVENC 튠: hq(고품질), ll(저지연), ull(초저지연)")
        else:
            # CPU codecs have full tune options
            self.tune_combo.clear()
            self.tune_combo.addItems([
                "none", "film", "animation", "grain", "stillimage", 
                "fastdecode", "zerolatency", "psnr", "ssim"
            ])
            self.tune_combo.setCurrentText("none")
            self.tune_combo.setToolTip("최적화 타입: film(영화), animation(애니메이션), grain(노이즈), zerolatency(실시간)")

    def _get_codec_display_name(self, codec_id: str) -> str:
        """Get user-friendly codec display name."""
        if not isinstance(codec_id, str):
            return str(codec_id) if codec_id is not None else "Unknown"
        
        codec_names = {
            "libx264": "H.264 (CPU)",
            "h264_nvenc": "H.264 (GPU)",
            "libx265": "H.265 (CPU)", 
            "hevc_nvenc": "H.265 (GPU)",
            "libvpx-vp9": "VP9 (CPU)",
            "libaom-av1": "AV1 (CPU)",
        }
        return codec_names.get(codec_id, codec_id)

    def _populate_current_settings(self) -> None:
        """Populate form with current settings."""
        self.container_combo.setCurrentText(self.current_settings.container)
        
        # Find matching codec by data (id)
        for i in range(self.video_codec_combo.count()):
            if self.video_codec_combo.itemData(i) == self.current_settings.video_codec:
                self.video_codec_combo.setCurrentIndex(i)
                break
        
        self.crf_spin.setValue(self.current_settings.crf or 18)
        self.bitrate_edit.setText(self.current_settings.bitrate or "")
        self.audio_codec_combo.setCurrentText(self.current_settings.audio_codec)
        self.audio_bitrate_edit.setText(self.current_settings.audio_bitrate or "")
        
        # Parse extra_params to populate advanced settings
        if self.current_settings.extra_params:
            extra_parts = self.current_settings.extra_params.split()
            i = 0
            while i < len(extra_parts):
                if extra_parts[i] == "-preset" and i + 1 < len(extra_parts):
                    self.preset_combo.setCurrentText(extra_parts[i + 1])
                elif extra_parts[i] == "-tune" and i + 1 < len(extra_parts):
                    self.tune_combo.setCurrentText(extra_parts[i + 1])
                elif extra_parts[i] == "-profile:v" and i + 1 < len(extra_parts):
                    self.profile_combo.setCurrentText(extra_parts[i + 1])
                elif extra_parts[i] == "-level" and i + 1 < len(extra_parts):
                    self.level_combo.setCurrentText(extra_parts[i + 1])
                i += 1

    def _add_current_settings(self) -> None:
        """Add current form settings to config list."""
        print(f"[DEBUG] Adding current settings to config list")
        settings = VideoSettings()
        settings.container = self.container_combo.currentText()
        # Get codec ID from current selection
        codec_data = self.video_codec_combo.currentData()
        if codec_data and isinstance(codec_data, str):
            settings.video_codec = codec_data
        else:
            # Fallback to current text if no data
            settings.video_codec = self.video_codec_combo.currentText()
        settings.crf = self.crf_spin.value()
        settings.bitrate = self.bitrate_edit.text().strip() or None
        settings.audio_codec = self.audio_codec_combo.currentText()
        settings.audio_bitrate = self.audio_bitrate_edit.text().strip() or None
        
        print(f"[DEBUG] Settings created:")
        print(f"  container: {settings.container}")
        print(f"  video_codec: {settings.video_codec}")
        print(f"  crf: {settings.crf}")
        print(f"  bitrate: {settings.bitrate}")
        print(f"  audio_codec: {settings.audio_codec}")
        print(f"  audio_bitrate: {settings.audio_bitrate}")
        
        # Advanced settings
        settings.two_pass = self.two_pass_check.isChecked()
        settings.gpu_enable = isinstance(settings.video_codec, str) and "nvenc" in settings.video_codec
        settings.low_latency = False  # Low latency is now handled via tune option
        
        # Build extra parameters from advanced settings
        extra_params = []
        preset = self.preset_combo.currentText()
        tune = self.tune_combo.currentText()
        profile = self.profile_combo.currentText()
        level = self.level_combo.currentText()
        
        if preset and preset != "auto":
            extra_params.append(f"-preset {preset}")
        if tune and tune != "none":
            extra_params.append(f"-tune {tune}")
        if profile and profile != "auto":
            extra_params.append(f"-profile:v {profile}")
        if level and level != "auto":
            extra_params.append(f"-level {level}")
        
        settings.extra_params = " ".join(extra_params) if extra_params else None
        
        print(f"[DEBUG] Advanced settings:")
        print(f"  two_pass: {settings.two_pass}")
        print(f"  gpu_enable: {settings.gpu_enable}")
        print(f"  low_latency: {settings.low_latency}")
        print(f"  extra_params: {settings.extra_params}")

        # Create display name with codec type and quality
        codec_display = self._get_codec_display_name(settings.video_codec)
        quality_label = "CRF" if isinstance(settings.video_codec, str) and (settings.video_codec.startswith("libx") or settings.video_codec in ["libvpx-vp9", "libaom-av1"]) else "QP"
        
        config_name = f"{codec_display} ({settings.container})"
        if settings.crf is not None:
            config_name += f" - {quality_label} {settings.crf}"
        if settings.bitrate:
            config_name += f" - {settings.bitrate}"
        
        # Add preset info if not default
        preset = self.preset_combo.currentText()
        if preset and preset not in ["medium", "p4", "auto"]:
            config_name += f" - {preset}"
        
        # Add tune info if not none
        tune = self.tune_combo.currentText()
        if tune and tune != "none":
            config_name += f" - {tune}"
        
        # Check if already exists
        for i in range(self.config_list.count()):
            item = self.config_list.item(i)
            if item.text() == config_name:
                QMessageBox.information(self, "Duplicate", "This configuration is already in the list.")
                return
        
        # Add to list
        self.encoding_configs.append(settings)
        self.config_list.addItem(config_name)
        self._update_summary()

    def _remove_selected_config(self) -> None:
        """Remove selected configuration from list."""
        current_row = self.config_list.currentRow()
        if current_row >= 0:
            del self.encoding_configs[current_row]
            self.config_list.takeItem(current_row)
            self._update_summary()

    def _clear_all_configs(self) -> None:
        """Clear all configurations."""
        reply = QMessageBox.question(
            self, "Clear All", "Remove all configurations?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.encoding_configs.clear()
            self.config_list.clear()
            self._update_summary()

    def _browse_output_dir(self) -> None:
        """Browse for output directory."""
        if self.input_files:
            default_dir = str(Path(self.input_files[0]).parent)
        else:
            default_dir = str(Path.home())
        
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory", default_dir)
        if dir_path:
            self.output_dir.setText(dir_path)

    def _update_summary(self) -> None:
        """Update the summary label."""
        if not self.encoding_configs:
            self.summary_label.setText("No configurations added. Add at least one configuration.")
            return
        
        total_jobs = len(self.input_files) * len(self.encoding_configs)
        self.summary_label.setText(
            f"Total encoding jobs: {total_jobs} "
            f"({len(self.input_files)} files × {len(self.encoding_configs)} configurations)"
        )

    def _validate_and_accept(self) -> None:
        """Validate settings and accept dialog."""
        if not self.encoding_configs:
            QMessageBox.warning(self, "No Configurations", "Please add at least one configuration.")
            return
        
        if not self.input_files:
            QMessageBox.warning(self, "No Files", "No input files specified.")
            return
        
        self.accept()

    def get_encoding_jobs(self) -> List[Dict[str, Any]]:
        """Get list of encoding jobs to execute."""
        jobs = []
        
        for file_path in self.input_files:
            for i, settings in enumerate(self.encoding_configs):
                # Determine output path
                input_path = Path(file_path)
                
                if self.output_dir.text().strip():
                    output_dir = Path(self.output_dir.text().strip())
                else:
                    output_dir = input_path.parent
                
                # Generate output filename with codec and quality info
                # Get proper extension based on container format
                container_ext = f".{settings.container}"
                
                if self.add_config_suffix.isChecked():
                    # Create descriptive suffix
                    codec_display = self._get_codec_display_name(settings.video_codec)
                    quality_label = "CRF" if isinstance(settings.video_codec, str) and (settings.video_codec.startswith("libx") or settings.video_codec in ["libvpx-vp9", "libaom-av1"]) else "QP"
                    
                    suffix_parts = [codec_display.replace(" ", "").replace("(", "").replace(")", "")]
                    if settings.crf is not None:
                        suffix_parts.append(f"{quality_label}{settings.crf}")
                    if settings.bitrate:
                        suffix_parts.append(settings.bitrate.replace("k", "K").replace("M", "M"))
                    
                    suffix = "_".join(suffix_parts)
                    output_name = f"{input_path.stem}_{suffix}{container_ext}"
                else:
                    output_name = f"{input_path.stem}{container_ext}"
                
                output_path = output_dir / output_name
                
                # Create descriptive config name
                codec_display = self._get_codec_display_name(settings.video_codec)
                quality_label = "CRF" if isinstance(settings.video_codec, str) and (settings.video_codec.startswith("libx") or settings.video_codec in ["libvpx-vp9", "libaom-av1"]) else "QP"
                
                config_name = f"{codec_display}"
                if settings.crf is not None:
                    config_name += f" {quality_label}{settings.crf}"
                if settings.bitrate:
                    config_name += f" {settings.bitrate}"
                
                jobs.append({
                    'input_path': str(input_path),
                    'output_path': str(output_path),
                    'config_name': config_name,
                    'settings': settings
                })
        
        return jobs
