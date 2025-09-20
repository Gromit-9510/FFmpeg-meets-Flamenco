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
			self.queue_panel._add_file_to_queue(f)

	def _collect_settings(self) -> VideoSettings:
		s = VideoSettings()
		s.container = self.settings_panel.container_format.currentText()
		
		# Get video codec ID from user-friendly selection
		video_codec_data = self.settings_panel.video_codec.currentData()
		s.video_codec = video_codec_data if video_codec_data else self.settings_panel.video_codec.currentText()
		
		s.crf = int(self.settings_panel.crf.value())
		bitrate = self.settings_panel.bitrate.text().strip()
		s.bitrate = bitrate or None
		# Two-pass UI has been removed; force single-pass
		s.two_pass = False
		
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
		# Two-pass UI removed; nothing to set here
		
		self.settings_panel.audio_codec.setCurrentText(s.audio_codec)
		self.settings_panel.audio_bitrate.setText(s.audio_bitrate or "")
		self.settings_panel.max_filesize.setText(s.max_filesize or "")
		self.settings_panel.extra_params.setText(s.extra_params or "")

	def _on_encode_clicked(self) -> None:
		# Get checked file paths from queue
		checked_files = self.queue_panel.get_checked_files()
		
		if not checked_files:
			self.status.showMessage("No files checked", 3000)
			return

		settings = self._collect_settings()
		
		# Show output dialog
		from .output_dialog import OutputDialog
		dialog = OutputDialog(checked_files, settings, self)
		if dialog.exec() != QDialog.Accepted:
			return
		
		# Get output path for first file
		output_path = dialog.get_output_path(checked_files[0])
		if not output_path:
			self.status.showMessage("Cannot generate output path", 3000)
			return

		cmds = build_ffmpeg_commands(checked_files[0], output_path, settings)
		cmd = cmds[-1]  # Single pass or second pass

		self._start_worker(cmd)


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
		
		# Get checked file paths from queue
		checked_files = self.queue_panel.get_checked_files()
		if not checked_files:
			QMessageBox.warning(self, "Flamenco", "No files checked.")
			return
		
		# Output path 설정 (원래 버전처럼 직접 파일 다이얼로그 사용)
		settings = self._collect_settings()
		input_path = checked_files[0]
		default_output = str(Path(input_path).with_suffix(f".{settings.output_extension()}"))
		
		# Output directory 선택
		output_dir = QFileDialog.getExistingDirectory(
			self, 
			"Flamenco Output Directory", 
			str(Path(default_output).parent)
		)
		
		if not output_dir:
			return  # 사용자가 취소한 경우
		
		# Output filename 설정
		output_filename = QFileDialog.getSaveFileName(
			self,
			"Flamenco Output Filename",
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
			job = client.submit_ffmpeg_job("FFmpeg Encoding Job", command, checked_files, output_filename)
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
				# Convert VideoSettings to dict for Preset creation
				settings_dict = {
					'container': settings.container,
					'video_codec': settings.video_codec,
					'crf': settings.crf,
					'bitrate': settings.bitrate,
					'two_pass': settings.two_pass,
					'gpu_enable': settings.gpu_enable,
					'low_latency': settings.low_latency,
					'tune': settings.tune,
					'audio_codec': settings.audio_codec,
					'audio_bitrate': settings.audio_bitrate,
					'max_filesize': settings.max_filesize,
					'extra_params': settings.extra_params
				}
				preset = Preset(name=name, **settings_dict)
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
