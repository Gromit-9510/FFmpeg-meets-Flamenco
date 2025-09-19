from __future__ import annotations

from PySide6.QtCore import Qt, QThread, QObject, Signal
from PySide6.QtWidgets import (
	QMainWindow,
	QSplitter,
	QWidget,
	QVBoxLayout,
	QStatusBar,
	QMenu,
	QMenuBar,
	QDockWidget,
	QFileDialog,
	QMessageBox,
	QDialog,
)
from PySide6.QtGui import QAction

from .queue_panel import QueuePanel
from .settings_panel import SettingsPanel
from .log_panel import LogPanel
from ..core.ffmpeg_cmd import VideoSettings, build_ffmpeg_commands
from ..core.runner import FFmpegRunner
from ..core.presets import Preset, PresetStore
from ..integrations.flamenco_client import FlamencoClient, FlamencoConfig
from pathlib import Path


class Worker(QObject):
	finished = Signal(object)  # Changed from int to object to avoid overflow
	log = Signal(str)

	def __init__(self, cmd: list[str]) -> None:
		super().__init__()
		self.cmd = cmd

	def run(self) -> None:
		runner = FFmpegRunner(on_log=self.log.emit)
		code = runner.run(self.cmd)
		self.finished.emit(code)


class MainWindow(QMainWindow):
	def __init__(self) -> None:
		super().__init__()
		self.setWindowTitle("FFmpeg Encoder v2.0 - by Insoo Chang")

		self._create_menu()

		splitter = QSplitter(Qt.Horizontal)
		splitter.setChildrenCollapsible(False)
		self.queue_panel = QueuePanel()
		self.settings_panel = SettingsPanel()
		splitter.addWidget(self.queue_panel)
		splitter.addWidget(self.settings_panel)
		splitter.setStretchFactor(0, 2)
		splitter.setStretchFactor(1, 1)

		container = QWidget()
		layout = QVBoxLayout(container)
		layout.addWidget(splitter)
		self.setCentralWidget(container)

		self.status = QStatusBar()
		self.setStatusBar(self.status)

		self.log_panel = LogPanel()
		self.log_dock = QDockWidget("Logs", self)
		self.log_dock.setWidget(self.log_panel)
		self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)

		self.settings_panel.encode_btn.clicked.connect(self._on_encode_clicked)
		self.settings_panel.submit_flamenco_btn.clicked.connect(self._on_submit_flamenco)
		self.settings_panel.save_preset_clicked.connect(self._on_save_preset)
		self.settings_panel.load_preset_clicked.connect(self._on_load_preset)

		self.preset_store = PresetStore(Path.home() / ".ffmpeg_encoder" / "presets")

	def _create_menu(self) -> None:
		menubar = QMenuBar(self)
		self.setMenuBar(menubar)

		file_menu = QMenu("File", self)
		menubar.addMenu(file_menu)

		open_action = QAction("Add Files/Folders", self)
		open_action.triggered.connect(self._on_add_files_folders)
		file_menu.addAction(open_action)

		export_action = QAction("Export Preset...", self)
		export_action.triggered.connect(self._on_export_preset)
		file_menu.addAction(export_action)

		import_action = QAction("Import Preset...", self)
		import_action.triggered.connect(self._on_import_preset)
		file_menu.addAction(import_action)

		quit_action = QAction("Quit", self)
		quit_action.triggered.connect(self.close)
		file_menu.addAction(quit_action)

		# Help 메뉴 추가
		help_menu = QMenu("Help", self)
		menubar.addMenu(help_menu)

		about_action = QAction("About", self)
		about_action.triggered.connect(self._on_about)
		help_menu.addAction(about_action)

	def _on_add_files_folders(self) -> None:
		files, _ = QFileDialog.getOpenFileNames(self, "Select video files")
		for f in files:
			self.queue_panel.list_widget.addItem(f)

	def _collect_settings(self) -> VideoSettings:
		s = VideoSettings()
		s.container = self.settings_panel.container_format.currentText()
		
		# Get video codec ID from user-friendly selection
		video_codec_data = self.settings_panel.video_codec.currentData()
		s.video_codec = video_codec_data if video_codec_data else self.settings_panel.video_codec.currentText()
		
		s.crf = int(self.settings_panel.crf.value())
		bitrate = self.settings_panel.bitrate.text().strip()
		s.bitrate = bitrate or None
		s.two_pass = self.settings_panel.two_pass.isChecked()
		
		# GPU enable is determined by codec selection
		s.gpu_enable = "nvenc" in s.video_codec
		
		# Low latency is determined by codec selection
		s.low_latency = "_ll" in s.video_codec
		
		# Tune is not used anymore
		s.tune = "none"
		
		s.audio_codec = self.settings_panel.audio_codec.currentText()
		s.audio_bitrate = self.settings_panel.audio_bitrate.text().strip() or None
		s.max_filesize = self.settings_panel.max_filesize.text().strip() or None
		s.extra_params = self.settings_panel.extra_params.text().strip() or None
		return s

	def _apply_settings(self, s: VideoSettings) -> None:
		self.settings_panel.container_format.setCurrentText(s.container)
		
		# Set video codec by finding the matching item
		for i in range(self.settings_panel.video_codec.count()):
			if self.settings_panel.video_codec.itemData(i) == s.video_codec:
				self.settings_panel.video_codec.setCurrentIndex(i)
				break
		else:
			# Fallback to text matching
			self.settings_panel.video_codec.setCurrentText(s.video_codec)
		
		self.settings_panel.crf.setValue(int(s.crf or 18))
		self.settings_panel.bitrate.setText(s.bitrate or "")
		self.settings_panel.two_pass.setChecked(bool(s.two_pass))
		
		self.settings_panel.audio_codec.setCurrentText(s.audio_codec)
		self.settings_panel.audio_bitrate.setText(s.audio_bitrate or "")
		self.settings_panel.max_filesize.setText(s.max_filesize or "")
		self.settings_panel.extra_params.setText(s.extra_params or "")

	def _on_encode_clicked(self) -> None:
		# Get file paths from queue (using stored data)
		items = []
		for i in range(self.queue_panel.list_widget.count()):
			item = self.queue_panel.list_widget.item(i)
			file_path = item.data(0)  # Get stored file path
			if file_path:
				items.append(file_path)
		
		if not items:
			self.status.showMessage("큐가 비어있습니다", 3000)
			return

		settings = self._collect_settings()
		
		# Generate output path based on settings
		output_path = self._generate_output_path(items[0], settings)
		if not output_path:
			return

		cmds = build_ffmpeg_commands(items[0], output_path, settings)
		cmd = cmds[-1]  # Single pass or second pass

		self._start_worker(cmd)

	def _generate_output_path(self, input_path: str, settings: VideoSettings) -> str:
		"""Generate output path based on settings."""
		input_file = Path(input_path)
		
		# Check output mode
		if self.settings_panel.output_mode.currentText() == "Global":
			output_dir = self.settings_panel.global_output_path.text().strip()
			if not output_dir:
				# Fallback to file dialog
				output_path, _ = QFileDialog.getSaveFileName(
					self, "Select output file", 
					filter=f"*.{settings.output_extension()}"
				)
				return output_path
		else:
			# Individual mode - ask for each file
			output_path, _ = QFileDialog.getSaveFileName(
				self, "Select output file", 
				filter=f"*.{settings.output_extension()}"
			)
			return output_path
		
		# Generate filename based on pattern
		pattern = self.settings_panel.filename_pattern.text().strip()
		if not pattern:
			pattern = "{name}_{codec}_{quality}"
		
		# Replace pattern variables
		filename = pattern.format(
			name=input_file.stem,
			codec=settings.video_codec.replace("lib", "").replace("_", ""),
			quality=f"crf{settings.crf}" if settings.crf else "bitrate",
			container=settings.container
		)
		
		output_file = Path(self.settings_panel.global_output_path.text().strip()) / f"{filename}.{settings.output_extension()}"
		
		# Handle file exists
		overwrite_mode = self.settings_panel.overwrite_mode.currentText()
		if output_file.exists():
			if overwrite_mode == "Ask":
				reply = QMessageBox.question(
					self, "File Exists", 
					f"File {output_file.name} already exists. Overwrite?",
					QMessageBox.Yes | QMessageBox.No
				)
				if reply != QMessageBox.Yes:
					return ""
			elif overwrite_mode == "Skip":
				self.status.showMessage(f"Skipped {output_file.name} (already exists)", 3000)
				return ""
			elif overwrite_mode == "Rename":
				counter = 1
				while output_file.exists():
					output_file = output_file.with_stem(f"{output_file.stem}_{counter}")
					counter += 1
		
		return str(output_file)

	def _start_worker(self, cmd: list[str]) -> None:
		self.thread = QThread(self)
		self.worker = Worker(cmd)
		self.worker.moveToThread(self.thread)
		self.thread.started.connect(self.worker.run)
		self.worker.log.connect(self.log_panel.append_line)
		self.worker.finished.connect(self._on_worker_finished)
		self.thread.start()

	def _on_worker_finished(self, code) -> None:
		self.status.showMessage(f"FFmpeg finished with code {code}", 5000)
		self.thread.quit()
		self.thread.wait()

	def _on_submit_flamenco(self) -> None:
		# Submit directly using settings
		base_url = self.settings_panel.flamenco_base_url.text().strip()
		token = self.settings_panel.flamenco_token.text().strip()
		if not base_url or not token:
			QMessageBox.warning(self, "Flamenco", "Please configure Flamenco Base URL and API Token in settings.")
			return
		
		# Get file paths from queue (using stored data)
		items = []
		for i in range(self.queue_panel.list_widget.count()):
			item = self.queue_panel.list_widget.item(i)
			file_path = item.data(0)  # Get stored file path
			if file_path:
				items.append(file_path)
		
		if not items:
			QMessageBox.warning(self, "Flamenco", "큐가 비어있습니다.")
			return
		
		# 출력 경로 설정 다이얼로그
		settings = self._collect_settings()
		input_path = items[0]
		default_output = str(Path(input_path).with_suffix(f".{settings.output_extension()}"))
		
		# 출력 디렉토리 선택
		output_dir = QFileDialog.getExistingDirectory(
			self, 
			"Flamenco 출력 디렉토리 선택", 
			str(Path(default_output).parent)
		)
		
		if not output_dir:
			return  # 사용자가 취소한 경우
		
		# 출력 파일명 설정
		output_filename = QFileDialog.getSaveFileName(
			self,
			"Flamenco 출력 파일명 설정",
			str(Path(output_dir) / Path(default_output).name),
			f"{settings.output_extension().upper()} Files (*.{settings.output_extension()});;All Files (*)"
		)[0]
		
		if not output_filename:
			return  # 사용자가 취소한 경우
		
		# FFmpeg 명령어 생성
		cmds = build_ffmpeg_commands(input_path, output_filename, settings)
		command = cmds[-1]
		
		client = FlamencoClient(FlamencoConfig(base_url=base_url, token=token))
		try:
			job = client.submit_ffmpeg_job("FFmpeg Encoding Job", command, items, output_filename)
			job_id = job.get("id") or job.get("job_id") or "?"
			self.status.showMessage(f"Submitted to Flamenco (Job {job_id}) - Output: {output_filename}", 5000)
		except Exception as e:
			QMessageBox.critical(self, "Flamenco", f"Submission failed: {e}")

	def _on_export_preset(self) -> None:
		"""Export current settings as a preset file."""
		from PySide6.QtWidgets import QFileDialog
		
		file_path, _ = QFileDialog.getSaveFileName(
			self, "Export Preset", "", "JSON Files (*.json);;All Files (*)"
		)
		
		if file_path:
			try:
				settings = self._collect_settings()
				from ..core.presets import PresetStore
				store = PresetStore()
				store.export_preset(settings, file_path)
				QMessageBox.information(self, "Export Success", f"Preset exported to {file_path}")
			except Exception as e:
				QMessageBox.critical(self, "Export Error", f"Failed to export preset: {str(e)}")

	def _on_import_preset(self) -> None:
		"""Import a preset file and apply settings."""
		from PySide6.QtWidgets import QFileDialog
		
		file_path, _ = QFileDialog.getOpenFileName(
			self, "Import Preset", "", "JSON Files (*.json);;All Files (*)"
		)
		
		if file_path:
			try:
				from ..core.presets import PresetStore
				store = PresetStore()
				preset = store.import_preset(file_path)
				self._apply_settings(preset)
				QMessageBox.information(self, "Import Success", f"Preset imported from {file_path}")
			except Exception as e:
				QMessageBox.critical(self, "Import Error", f"Failed to import preset: {str(e)}")

	def _on_save_preset(self) -> None:
		"""Save current settings as a preset."""
		from PySide6.QtWidgets import QInputDialog
		
		name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
		if ok and name:
			try:
				settings = self._collect_settings()
				from ..core.presets import PresetStore, Preset
				store = PresetStore()
				preset = Preset(name=name, **settings)
				store.save(preset)
				QMessageBox.information(self, "Save Success", f"Preset '{name}' saved successfully")
			except Exception as e:
				QMessageBox.critical(self, "Save Error", f"Failed to save preset: {str(e)}")

	def _on_load_preset(self) -> None:
		"""Load a preset and apply settings."""
		from PySide6.QtWidgets import QInputDialog
		
		from ..core.presets import PresetStore
		store = PresetStore()
		presets = store.list_presets()
		
		if not presets:
			QMessageBox.information(self, "No Presets", "No presets found. Save a preset first.")
			return
		
		name, ok = QInputDialog.getItem(self, "Load Preset", "Select preset:", presets, 0, False)
		if ok and name:
			try:
				preset = store.load(name)
				self._apply_settings(preset)
				QMessageBox.information(self, "Load Success", f"Preset '{name}' loaded successfully")
			except Exception as e:
				QMessageBox.critical(self, "Load Error", f"Failed to load preset: {str(e)}")

	def _on_about(self) -> None:
		"""About 다이얼로그를 표시합니다."""
		about_text = """
<h2>FFmpeg Encoder v2.0</h2>
<p><b>Author:</b> Insoo Chang<br>
<b>Email:</b> insu9510@gmail.com</p>

<p>A powerful video encoding application with Flamenco integration for distributed processing.</p>

<h3>Features:</h3>
<ul>
<li>Multiple video codecs (H.264, H.265, VP9, AV1, ProRes, DNxHD)</li>
<li>GPU acceleration support (NVENC, QSV, AMF, VAAPI)</li>
<li>Low latency encoding options</li>
<li>Batch processing with queue management</li>
<li>Flamenco distributed encoding</li>
<li>Preset management</li>
<li>Batch renaming with patterns</li>
</ul>

<p><b>GitHub:</b> <a href="https://github.com/insu9510/ffmpeg-encoder">https://github.com/insu9510/ffmpeg-encoder</a></p>

<p><b>License:</b> LGPL 3.0+<br>
This software is free to use, modify, and distribute for non-commercial purposes.<br>
Commercial use requires permission from the author.</p>
		"""
		
		QMessageBox.about(self, "About FFmpeg Encoder", about_text)
