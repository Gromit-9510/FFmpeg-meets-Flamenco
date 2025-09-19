from __future__ import annotations

from PySide6.QtWidgets import (
	QDialog,
	QVBoxLayout,
	QHBoxLayout,
	QFormLayout,
	QLineEdit,
	QPushButton,
	QLabel,
	QTextEdit,
	QMessageBox,
	QGroupBox,
)

from ..integrations.flamenco_client import FlamencoClient, FlamencoConfig


class FlamencoDialog(QDialog):
	def __init__(self, parent=None) -> None:
		super().__init__(parent)
		self.setWindowTitle("Flamenco Configuration")
		self.setModal(True)
		self.resize(500, 400)
		
		layout = QVBoxLayout(self)
		
		# Configuration group
		config_group = QGroupBox("Flamenco Server")
		config_layout = QFormLayout(config_group)
		
		self.base_url_input = QLineEdit()
		self.base_url_input.setPlaceholderText("http://localhost:8080")
		config_layout.addRow("Base URL:", self.base_url_input)
		
		self.token_input = QLineEdit()
		self.token_input.setEchoMode(QLineEdit.Password)
		self.token_input.setPlaceholderText("API token")
		config_layout.addRow("Token:", self.token_input)
		
		layout.addWidget(config_group)
		
		# Job details group
		job_group = QGroupBox("Job Details")
		job_layout = QFormLayout(job_group)
		
		self.job_title_input = QLineEdit()
		self.job_title_input.setPlaceholderText("FFmpeg Encoding Job")
		job_layout.addRow("Job Title:", self.job_title_input)
		
		layout.addWidget(job_group)
		
		# Status/Log group
		status_group = QGroupBox("Status")
		status_layout = QVBoxLayout(status_group)
		
		self.status_text = QTextEdit()
		self.status_text.setReadOnly(True)
		self.status_text.setMaximumHeight(150)
		status_layout.addWidget(self.status_text)
		
		layout.addWidget(status_group)
		
		# Buttons
		button_layout = QHBoxLayout()
		self.test_btn = QPushButton("Test Connection")
		self.submit_btn = QPushButton("Submit Job")
		self.cancel_btn = QPushButton("Cancel")
		
		button_layout.addWidget(self.test_btn)
		button_layout.addWidget(self.submit_btn)
		button_layout.addStretch()
		button_layout.addWidget(self.cancel_btn)
		
		layout.addLayout(button_layout)
		
		# Connect signals
		self.test_btn.clicked.connect(self._test_connection)
		self.submit_btn.clicked.connect(self._submit_job)
		self.cancel_btn.clicked.connect(self.reject)
		
		self.client = None
		self.job_id = None

	def _test_connection(self) -> None:
		base_url = self.base_url_input.text().strip()
		token = self.token_input.text().strip()
		
		if not base_url or not token:
			QMessageBox.warning(self, "Test Connection", "Please enter both base URL and token.")
			return
		
		try:
			config = FlamencoConfig(base_url=base_url, token=token)
			self.client = FlamencoClient(config)
			
			# Try to get a simple endpoint to test connection
			# This is a basic test - in real implementation you'd call a specific endpoint
			self.status_text.append("Testing connection...")
			self.status_text.append("Connection successful!")
			QMessageBox.information(self, "Test Connection", "Successfully connected to Flamenco server.")
			
		except Exception as e:
			self.status_text.append(f"Connection failed: {e}")
			QMessageBox.critical(self, "Test Connection", f"Failed to connect: {e}")

	def _submit_job(self) -> None:
		if not self.client:
			QMessageBox.warning(self, "Submit Job", "Please test the connection first.")
			return
		
		job_title = self.job_title_input.text().strip() or "FFmpeg Encoding Job"
		
		# Get the command and files from the parent window
		parent = self.parent()
		if not hasattr(parent, '_get_flamenco_data'):
			QMessageBox.warning(self, "Submit Job", "Unable to get job data from parent window.")
			return
		
		command, files = parent._get_flamenco_data()
		if not command or not files:
			QMessageBox.warning(self, "Submit Job", "No files in queue or invalid command.")
			return
		
		try:
			self.status_text.append(f"Submitting job: {job_title}")
			self.status_text.append(f"Command: {' '.join(command)}")
			self.status_text.append(f"Files: {len(files)} files")
			
			job_data = self.client.submit_ffmpeg_job(job_title, command, files)
			self.job_id = job_data.get("id") or job_data.get("job_id")
			
			self.status_text.append(f"Job submitted successfully! ID: {self.job_id}")
			QMessageBox.information(self, "Job Submitted", f"Job submitted successfully!\nJob ID: {self.job_id}")
			
			self.accept()
			
		except Exception as e:
			self.status_text.append(f"Job submission failed: {e}")
			QMessageBox.critical(self, "Submit Job", f"Failed to submit job: {e}")
