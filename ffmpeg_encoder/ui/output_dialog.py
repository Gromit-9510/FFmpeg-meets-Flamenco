from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
	QDialog,
	QVBoxLayout,
	QHBoxLayout,
	QFormLayout,
	QLineEdit,
	QPushButton,
	QFileDialog,
	QLabel,
	QComboBox,
	QCheckBox,
	QGroupBox,
	QMessageBox,
	QSpinBox,
)


class OutputDialog(QDialog):
	"""Output settings dialog for encoding jobs."""
	
	def __init__(self, input_files: List[str], settings, parent=None):
		super().__init__(parent)
		self.input_files = input_files
		self.settings = settings
		self.output_paths: List[str] = []
		
		self.setWindowTitle("Output Settings")
		self.setModal(True)
		self.resize(600, 400)
		
		self._setup_ui()
		self._populate_defaults()

	def _setup_ui(self):
		layout = QVBoxLayout(self)
		
		# File info group
		info_group = QGroupBox("Input Files")
		info_layout = QVBoxLayout(info_group)
		
		self.file_count_label = QLabel(f"Files to encode: {len(self.input_files)}")
		info_layout.addWidget(self.file_count_label)
		
		# Show first few files
		preview_text = ""
		for i, file_path in enumerate(self.input_files[:3]):
			preview_text += f"• {Path(file_path).name}\n"
		if len(self.input_files) > 3:
			preview_text += f"... and {len(self.input_files) - 3} more files"
		
		self.files_preview = QLabel(preview_text)
		self.files_preview.setStyleSheet("color: gray; font-size: 10px;")
		self.files_preview.setWordWrap(True)
		info_layout.addWidget(self.files_preview)
		
		layout.addWidget(info_group)
		
		# Output settings group
		output_group = QGroupBox("Output Settings")
		output_layout = QFormLayout(output_group)
		
		# Output mode
		self.output_mode = QComboBox()
		self.output_mode.addItems(["Same folder as input", "Custom folder", "Ask for each file"])
		self.output_mode.currentTextChanged.connect(self._on_output_mode_changed)
		output_layout.addRow("Output Mode:", self.output_mode)
		
		# Custom folder
		folder_layout = QHBoxLayout()
		self.custom_folder = QLineEdit()
		self.custom_folder.setPlaceholderText("Select output folder...")
		self.browse_folder_btn = QPushButton("Browse...")
		self.browse_folder_btn.clicked.connect(self._browse_folder)
		folder_layout.addWidget(self.custom_folder)
		folder_layout.addWidget(self.browse_folder_btn)
		output_layout.addRow("Custom Folder:", folder_layout)
		
		# Filename pattern
		self.filename_pattern = QLineEdit()
		self.filename_pattern.setPlaceholderText("e.g., {name}_{codec}_{quality}")
		self.filename_pattern.setText("{name}_encoded")
		output_layout.addRow("Filename Pattern:", self.filename_pattern)
		
		# Pattern help
		pattern_help = QLabel("Available variables: {name}, {codec}, {quality}, {container}")
		pattern_help.setStyleSheet("color: gray; font-size: 10px;")
		output_layout.addRow("", pattern_help)
		
		# File exists handling
		self.overwrite_mode = QComboBox()
		self.overwrite_mode.addItems(["Ask", "Overwrite", "Skip", "Rename"])
		output_layout.addRow("If file exists:", self.overwrite_mode)
		
		# Quality suffix
		quality_layout = QHBoxLayout()
		self.add_quality_suffix = QCheckBox("Add quality suffix")
		self.add_quality_suffix.setChecked(True)
		self.quality_suffix_format = QLineEdit()
		self.quality_suffix_format.setText("_crf{crf}")
		self.quality_suffix_format.setPlaceholderText("e.g., _crf{crf}, _bitrate{bitrate}")
		quality_layout.addWidget(self.add_quality_suffix)
		quality_layout.addWidget(self.quality_suffix_format)
		output_layout.addRow("Quality Suffix:", quality_layout)
		
		layout.addWidget(output_group)
		
		# Preview group
		preview_group = QGroupBox("Output Preview")
		preview_layout = QVBoxLayout(preview_group)
		
		self.preview_label = QLabel("Output files will be generated based on your settings.")
		self.preview_label.setStyleSheet("color: gray; font-size: 10px;")
		self.preview_label.setWordWrap(True)
		preview_layout.addWidget(self.preview_label)
		
		layout.addWidget(preview_group)
		
		# Buttons
		button_layout = QHBoxLayout()
		self.preview_btn = QPushButton("Preview Output")
		self.preview_btn.clicked.connect(self._preview_output)
		self.ok_btn = QPushButton("OK")
		self.ok_btn.clicked.connect(self.accept)
		self.cancel_btn = QPushButton("Cancel")
		self.cancel_btn.clicked.connect(self.reject)
		
		button_layout.addWidget(self.preview_btn)
		button_layout.addStretch()
		button_layout.addWidget(self.ok_btn)
		button_layout.addWidget(self.cancel_btn)
		
		layout.addLayout(button_layout)
		
		# Connect signals
		self.filename_pattern.textChanged.connect(self._update_preview)
		self.add_quality_suffix.toggled.connect(self._update_preview)
		self.quality_suffix_format.textChanged.connect(self._update_preview)
		self.output_mode.currentTextChanged.connect(self._update_preview)
		self.custom_folder.textChanged.connect(self._update_preview)

	def _populate_defaults(self):
		"""Populate default values based on settings."""
		# Set default output mode
		self.output_mode.setCurrentText("Same folder as input")
		self._on_output_mode_changed("Same folder as input")

	def _on_output_mode_changed(self, mode: str):
		"""Handle output mode change."""
		self.custom_folder.setEnabled(mode == "Custom folder")
		self.browse_folder_btn.setEnabled(mode == "Custom folder")
		self._update_preview()

	def _browse_folder(self):
		"""Browse for output folder."""
		folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
		if folder:
			self.custom_folder.setText(folder)

	def _update_preview(self):
		"""Update output preview."""
		if not self.input_files:
			return
		
		# Generate preview for first file
		first_file = Path(self.input_files[0])
		output_path = self._generate_output_path(first_file)
		
		if output_path:
			preview_text = f"Example output: {Path(output_path).name}"
			if len(self.input_files) > 1:
				preview_text += f"\n({len(self.input_files)} files total)"
		else:
			preview_text = "Output files will be generated based on your settings."
		
		self.preview_label.setText(preview_text)

	def _preview_output(self):
		"""Show detailed output preview."""
		if not self.input_files:
			return
		
		preview_text = "Output files preview:\n\n"
		
		for i, input_file in enumerate(self.input_files[:5]):  # Show first 5 files
			file_path = Path(input_file)
			output_path = self._generate_output_path(file_path)
			if output_path:
				preview_text += f"{i+1}. {file_path.name} → {Path(output_path).name}\n"
		
		if len(self.input_files) > 5:
			preview_text += f"... and {len(self.input_files) - 5} more files\n"
		
		QMessageBox.information(self, "Output Preview", preview_text)

	def _generate_output_path(self, input_file: Path) -> Optional[str]:
		"""Generate output path for a given input file."""
		try:
			# Get output directory
			output_mode = self.output_mode.currentText()
			if output_mode == "Same folder as input":
				output_dir = input_file.parent
			elif output_mode == "Custom folder":
				custom_folder = self.custom_folder.text().strip()
				if not custom_folder:
					return None
				output_dir = Path(custom_folder)
			else:  # Ask for each file
				return None
			
			# Generate filename
			pattern = self.filename_pattern.text().strip()
			if not pattern:
				pattern = "{name}_encoded"
			
			# Replace pattern variables
			codec_name = self.settings.video_codec.replace("lib", "").replace("_", "")
			quality = f"crf{self.settings.crf}" if self.settings.crf else "bitrate"
			
			filename = pattern.format(
				name=input_file.stem,
				codec=codec_name,
				quality=quality,
				container=self.settings.container
			)
			
			# Add quality suffix if enabled
			if self.add_quality_suffix.isChecked():
				suffix_format = self.quality_suffix_format.text().strip()
				if suffix_format:
					suffix = suffix_format.format(
						crf=self.settings.crf,
						bitrate=self.settings.bitrate or "auto"
					)
					filename += suffix
			
			# Add extension
			extension = self.settings.output_extension()
			output_file = output_dir / f"{filename}.{extension}"
			
			return str(output_file)
			
		except Exception as e:
			print(f"Error generating output path: {e}")
			return None

	def get_output_paths(self) -> List[str]:
		"""Get list of output paths for all input files."""
		output_paths = []
		
		for input_file in self.input_files:
			file_path = Path(input_file)
			output_path = self._generate_output_path(file_path)
			if output_path:
				output_paths.append(output_path)
			else:
				# If we can't generate path, use input file as fallback
				output_paths.append(str(file_path))
		
		return output_paths

	def get_output_path(self, input_file: str) -> Optional[str]:
		"""Get output path for a specific input file."""
		file_path = Path(input_file)
		return self._generate_output_path(file_path)
