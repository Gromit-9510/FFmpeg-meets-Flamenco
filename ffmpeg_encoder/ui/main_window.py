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
from .multi_encoding_dialog import MultiEncodingDialog
from ..core.ffmpeg_cmd import VideoSettings, build_ffmpeg_commands
from ..core.runner import FFmpegRunner
from ..core.multi_encoder import MultiEncoder
from ..core.presets import Preset, PresetStore
from ..integrations.flamenco_client import FlamencoClient, FlamencoConfig
from pathlib import Path


class Worker(QObject):
	finished = Signal(int)  # Return code as int
	log = Signal(str)

	def __init__(self, cmd: list[str]) -> None:
		super().__init__()
		self.cmd = cmd

	def run(self) -> None:
		try:
			runner = FFmpegRunner(on_log=self.log.emit)
			code = runner.run(self.cmd)
			self.finished.emit(code)
		except Exception as e:
			self.log.emit(f"Worker error: {e}")
			self.finished.emit(-1)


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
		self.multi_encoder = MultiEncoder()
		
		# Connect multi-encoder signals
		self.multi_encoder.job_started.connect(self._on_multi_job_started)
		self.multi_encoder.job_progress.connect(self._on_multi_job_progress)
		self.multi_encoder.job_completed.connect(self._on_multi_job_completed)
		self.multi_encoder.encoding_finished.connect(self._on_multi_encoding_finished)

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

		file_menu.addSeparator()

		multi_preset_action = QAction("Multi-Encoding...", self)
		multi_preset_action.triggered.connect(self._on_multi_preset_encoding)
		file_menu.addAction(multi_preset_action)

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
		
		try:
			s.container = self.settings_panel.container_format.currentText()
			
			# Get video codec ID from user-friendly selection
			video_codec_data = self.settings_panel.video_codec.currentData()
			if video_codec_data and isinstance(video_codec_data, str):
				s.video_codec = video_codec_data
			else:
				s.video_codec = self.settings_panel.video_codec.currentText()
			
			s.crf = int(self.settings_panel.crf.value())
			bitrate = self.settings_panel.bitrate.text().strip()
			s.bitrate = bitrate or None
			
			# Advanced settings
			s.two_pass = self.settings_panel.two_pass.isChecked()
			s.gpu_enable = isinstance(s.video_codec, str) and "nvenc" in s.video_codec
			s.low_latency = False  # Low latency is now handled via tune option
			
			# Additional settings (will be passed as extra_params)
			preset = self.settings_panel.preset.currentText()
			tune = self.settings_panel.tune.currentText()
			profile = self.settings_panel.profile.currentText()
			level = self.settings_panel.level.currentText()
			
			# Build extra parameters
			extra_params = []
			if preset and preset != "auto":
				extra_params.append(f"-preset {preset}")
			if tune and tune != "none":
				extra_params.append(f"-tune {tune}")
			if profile and profile != "auto":
				extra_params.append(f"-profile:v {profile}")
			if level and level != "auto":
				extra_params.append(f"-level {level}")
			
			s.extra_params = " ".join(extra_params) if extra_params else None
			
			s.audio_codec = self.settings_panel.audio_codec.currentText()
			s.audio_bitrate = self.settings_panel.audio_bitrate.text().strip() or None
			s.max_filesize = self.settings_panel.max_filesize.text().strip() or None
			
		except Exception as e:
			# Fallback to default values if any error occurs
			print(f"Error collecting settings: {e}")
			# Keep the VideoSettings defaults
			
		return s

	def _apply_settings(self, s: VideoSettings) -> None:
		try:
			self.settings_panel.container_format.setCurrentText(s.container)
			
			# Set video codec by finding the matching item
			found = False
			for i in range(self.settings_panel.video_codec.count()):
				if self.settings_panel.video_codec.itemData(i) == s.video_codec:
					self.settings_panel.video_codec.setCurrentIndex(i)
					found = True
					break
			
			if not found:
				# Fallback to text matching
				self.settings_panel.video_codec.setCurrentText(s.video_codec)
			
			self.settings_panel.crf.setValue(int(s.crf or 18))
			self.settings_panel.bitrate.setText(s.bitrate or "")
			# Two-pass UI removed; nothing to set here
			
			self.settings_panel.audio_codec.setCurrentText(s.audio_codec)
			self.settings_panel.audio_bitrate.setText(s.audio_bitrate or "")
			self.settings_panel.max_filesize.setText(s.max_filesize or "")
			self.settings_panel.extra_params.setText(s.extra_params or "")
			
		except Exception as e:
			print(f"Error applying settings: {e}")
			# Continue with partial application

	def _on_encode_clicked(self) -> None:
		try:
			print(f"[DEBUG] Starting single encoding process")
			# Get checked file paths from queue
			checked_files = self.queue_panel.get_checked_files()
			print(f"[DEBUG] Checked files: {checked_files}")
			
			if not checked_files:
				self.status.showMessage("No files checked", 3000)
				return

			settings = self._collect_settings()
			print(f"[DEBUG] Collected settings: {settings}")
			
			# Show output dialog
			from .output_dialog import OutputDialog
			dialog = OutputDialog(checked_files, settings, self)
			if dialog.exec() != QDialog.Accepted:
				print(f"[DEBUG] Output dialog cancelled")
				return
			
			# Get output path for first file
			output_path = dialog.get_output_path(checked_files[0])
			if not output_path:
				self.status.showMessage("Cannot generate output path", 3000)
				return
			print(f"[DEBUG] Output path: {output_path}")

			print(f"[DEBUG] Building FFmpeg commands...")
			cmds = build_ffmpeg_commands(checked_files[0], output_path, settings)
			print(f"[DEBUG] Generated {len(cmds)} command(s)")
			
			if not cmds:
				self.status.showMessage("Failed to generate FFmpeg commands", 3000)
				return
				
			cmd = cmds[-1]  # Single pass or second pass
			print(f"[DEBUG] Using command: {' '.join(cmd)}")

			self._start_worker(cmd)
			
		except Exception as e:
			self.status.showMessage(f"Encoding error: {e}", 5000)
			print(f"[ERROR] Encode error: {e}")
			import traceback
			print(f"[ERROR] Traceback: {traceback.format_exc()}")


	def _start_worker(self, cmd: list[str]) -> None:
		try:
			self.thread = QThread(self)
			self.worker = Worker(cmd)
			self.worker.moveToThread(self.thread)
			self.thread.started.connect(self.worker.run)
			self.worker.log.connect(self.log_panel.append_line)
			self.worker.finished.connect(self._on_worker_finished)
			self.thread.start()
		except Exception as e:
			self.status.showMessage(f"Failed to start worker: {e}", 5000)
			print(f"Worker start error: {e}")

	def _on_worker_finished(self, code: int) -> None:
		try:
			self.status.showMessage(f"FFmpeg finished with code {code}", 5000)
			if hasattr(self, 'thread') and self.thread:
				self.thread.quit()
				self.thread.wait()
			# Clean up worker and thread references
			if hasattr(self, 'worker'):
				del self.worker
			if hasattr(self, 'thread'):
				del self.thread
		except Exception as e:
			print(f"Worker finished error: {e}")
			self.status.showMessage(f"Worker finished with error: {e}", 5000)

	def _on_submit_flamenco(self) -> None:
		try:
			print(f"[DEBUG] Starting Flamenco submission process")
			# Submit directly using settings
			base_url = self.settings_panel.flamenco_base_url.text().strip()
			token = self.settings_panel.flamenco_token.text().strip()
			if not base_url or not token:
				QMessageBox.warning(self, "Flamenco", "Please configure Flamenco Base URL and API Token in settings.")
				return
			print(f"[DEBUG] Flamenco config - Base URL: {base_url}, Token: {'*' * len(token)}")
			
			# Get checked file paths from queue
			checked_files = self.queue_panel.get_checked_files()
			if not checked_files:
				QMessageBox.warning(self, "Flamenco", "No files checked.")
				return
			print(f"[DEBUG] Checked files: {checked_files}")
			
			# Output path 설정 (원래 버전처럼 직접 파일 다이얼로그 사용)
			settings = self._collect_settings()
			print(f"[DEBUG] Collected settings: {settings}")
			input_path = checked_files[0]
			default_output = str(Path(input_path).with_suffix(f".{settings.output_extension()}"))
			print(f"[DEBUG] Default output: {default_output}")
			
			# Output directory 선택
			output_dir = QFileDialog.getExistingDirectory(
				self, 
				"Flamenco Output Directory", 
				str(Path(default_output).parent)
			)
			
			if not output_dir:
				print(f"[DEBUG] Output directory selection cancelled")
				return  # 사용자가 취소한 경우
			print(f"[DEBUG] Selected output directory: {output_dir}")
			
			# Output filename 설정
			output_filename = QFileDialog.getSaveFileName(
				self,
				"Flamenco Output Filename",
				str(Path(output_dir) / Path(default_output).name),
				f"{settings.output_extension().upper()} Files (*.{settings.output_extension()});;All Files (*)"
			)[0]
			
			if not output_filename:
				print(f"[DEBUG] Output filename selection cancelled")
				return  # 사용자가 취소한 경우
			print(f"[DEBUG] Selected output filename: {output_filename}")
			
			# FFmpeg 명령어 생성
			print(f"[DEBUG] Building FFmpeg commands for Flamenco...")
			cmds = build_ffmpeg_commands(input_path, output_filename, settings)
			print(f"[DEBUG] Generated {len(cmds)} command(s)")
			if not cmds:
				QMessageBox.critical(self, "Flamenco", "Failed to generate FFmpeg commands")
				return
			command = cmds[-1]
			print(f"[DEBUG] Using command: {' '.join(command)}")
			
			client = FlamencoClient(FlamencoConfig(base_url=base_url, token=token))
			try:
				job = client.submit_ffmpeg_job("FFmpeg Encoding Job", command, checked_files, output_filename)
				job_id = job.get("id") or job.get("job_id") or "?"
				print(f"[DEBUG] Flamenco job submitted successfully: {job_id}")
				self.status.showMessage(f"Submitted to Flamenco (Job {job_id}) - Output: {output_filename}", 5000)
			except Exception as e:
				print(f"[ERROR] Flamenco submission failed: {e}")
				import traceback
				print(f"[ERROR] Traceback: {traceback.format_exc()}")
				QMessageBox.critical(self, "Flamenco", f"Submission failed: {e}")
		except Exception as e:
			print(f"[ERROR] Flamenco submission error: {e}")
			import traceback
			print(f"[ERROR] Traceback: {traceback.format_exc()}")
			QMessageBox.critical(self, "Flamenco", f"Submission error: {e}")

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
<li>Multi-encoding (one file, multiple configurations)</li>
<li>Flamenco distributed encoding</li>
<li>Preset management</li>
</ul>

<p><b>GitHub:</b> <a href="https://github.com/insu9510/ffmpeg-encoder">https://github.com/insu9510/ffmpeg-encoder</a></p>

<p><b>License:</b> LGPL 3.0+<br>
This software is free to use, modify, and distribute for non-commercial purposes.<br>
Commercial use requires permission from the author.</p>
		"""
		
		QMessageBox.about(self, "About FFmpeg Encoder", about_text)

	def _on_multi_preset_encoding(self) -> None:
		"""Handle multi-encoding menu action."""
		# Get checked file paths from queue
		checked_files = self.queue_panel.get_checked_files()
		
		if not checked_files:
			QMessageBox.warning(self, "No Selection", "No files checked. Please check files to encode.")
			return

		# Get current settings
		current_settings = self._collect_settings()

		# Show multi-encoding dialog
		dialog = MultiEncodingDialog(checked_files, current_settings, self)
		if dialog.exec() != QDialog.Accepted:
			return

		# Get encoding jobs
		jobs = dialog.get_encoding_jobs()
		if not jobs:
			QMessageBox.warning(self, "No Jobs", "No encoding jobs to execute.")
			return

		# Confirm before starting
		total_jobs = len(jobs)
		reply = QMessageBox.question(
			self,
			"Confirm Multi-Encoding",
			f"Start encoding {total_jobs} jobs?\n\n"
			f"Files: {len(checked_files)}\n"
			f"Configurations: {len(set(job['config_name'] for job in jobs))}\n\n"
			f"This may take a long time. Continue?",
			QMessageBox.Yes | QMessageBox.No
		)

		if reply == QMessageBox.Yes:
			self.multi_encoder.start_encoding(jobs)
			self.status.showMessage(f"Multi-encoding started: {total_jobs} jobs", 5000)

	def _on_multi_job_started(self, job_index: int, config_name: str, output_path: str) -> None:
		"""Handle multi-encoder job started signal."""
		self.status.showMessage(f"Job {job_index + 1} started: {config_name} → {Path(output_path).name}", 3000)
		self.log_panel.append_line(f"=== Job {job_index + 1} Started ===")
		self.log_panel.append_line(f"Config: {config_name}")
		self.log_panel.append_line(f"Output: {output_path}")

	def _on_multi_job_progress(self, job_index: int, progress: float, message: str) -> None:
		"""Handle multi-encoder job progress signal."""
		if message:
			self.log_panel.append_line(f"Job {job_index + 1}: {message}")

	def _on_multi_job_completed(self, job_index: int, success: bool, message: str) -> None:
		"""Handle multi-encoder job completed signal."""
		if success:
			self.log_panel.append_line(f"Job {job_index + 1} completed successfully: {message}")
		else:
			self.log_panel.append_line(f"Job {job_index + 1} failed: {message}")
		
		self.status.showMessage(f"Job {job_index + 1} {'completed' if success else 'failed'}: {message}", 3000)

	def _on_multi_encoding_finished(self) -> None:
		"""Handle multi-encoder finished signal."""
		self.status.showMessage("Multi-encoding finished", 5000)
		self.log_panel.append_line("=== Multi-Encoding Finished ===")
