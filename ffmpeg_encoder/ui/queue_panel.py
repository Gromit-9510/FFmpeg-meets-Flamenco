from __future__ import annotations

from pathlib import Path
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
	QWidget,
	QVBoxLayout,
	QHBoxLayout,
	QListWidget,
	QPushButton,
	QFileDialog,
	QLabel,
	QDialog,
)


class QueuePanel(QWidget):
	def __init__(self) -> None:
		super().__init__()
		layout = QVBoxLayout(self)

		controls = QHBoxLayout()
		self.add_files_btn = QPushButton("Add Files")
		self.add_folder_btn = QPushButton("Add Folder")
		self.remove_btn = QPushButton("Remove Selected")
		self.rename_btn = QPushButton("Batch Rename")
		controls.addWidget(self.add_files_btn)
		controls.addWidget(self.add_folder_btn)
		controls.addWidget(self.remove_btn)
		controls.addWidget(self.rename_btn)
		controls.addStretch(1)

		# File list with source/output display
		self.list_widget = QListWidget()
		self.list_widget.setAlternatingRowColors(True)
		self.list_widget.setStyleSheet("""
			QListWidget::item {
				padding: 8px;
				border-bottom: 1px solid #ddd;
			}
			QListWidget::item:selected {
				background-color: #0078d4;
				color: white;
			}
		""")
		
		
		self.hint = QLabel("버튼을 클릭하여 파일을 추가하세요")
		self.hint.setAlignment(Qt.AlignCenter)
		self.hint.setStyleSheet("color: gray; padding: 20px;")

		layout.addLayout(controls)
		layout.addWidget(self.list_widget)
		layout.addWidget(self.hint)

		self._connect_signals()

	def _connect_signals(self) -> None:
		self.add_files_btn.clicked.connect(self._on_add_files)
		self.add_folder_btn.clicked.connect(self._on_add_folder)
		self.remove_btn.clicked.connect(self._on_remove)
		self.rename_btn.clicked.connect(self._on_rename)


	def _on_add_files(self) -> None:
		files, _ = QFileDialog.getOpenFileNames(self, "비디오 파일 선택")
		for f in files:
			self._add_file_to_queue(f)

	def _on_add_folder(self) -> None:
		folder = QFileDialog.getExistingDirectory(self, "폴더 선택")
		if folder:
			# Video file extensions supported by FFmpeg (images excluded)
			video_extensions = {
				'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.m4v',
				'.3gp', '.3g2', '.f4v', '.asf', '.rm', '.rmvb', '.vob', '.ogv',
				'.m2v', '.mts', '.m2ts', '.ts', '.mxf', '.dv', '.divx', '.xvid',
				'.prores', '.dnxhd', '.hevc', '.h265', '.h264', '.av1', '.vp8', '.vp9', '.theora'
			}
			
			added_count = 0
			for p in Path(folder).rglob('*'):  # Recursive search
				if p.is_file() and p.suffix.lower() in video_extensions:
					self._add_file_to_queue(str(p))
					added_count += 1
			
			if added_count == 0:
				from PySide6.QtWidgets import QMessageBox
				QMessageBox.information(self, "비디오 파일 없음", "선택한 폴더에서 지원되는 비디오 파일을 찾을 수 없습니다.")
			else:
				self.hint.setText(f"{added_count}개의 비디오 파일이 추가되었습니다")

	def _add_file_to_queue(self, file_path: str) -> None:
		"""Add a file to the queue with source/output display."""
		path = Path(file_path)
		display_text = f"📁 소스: {path.name}\n📤 출력: {path.stem}_encoded{path.suffix}"
		
		# Add item and get the item object
		row = self.list_widget.count()
		self.list_widget.addItem(display_text)
		item = self.list_widget.item(row)
		
		if item:
			item.setData(0, file_path)  # Store original path in data
		
		# Hide hint if files are added
		if self.list_widget.count() > 0:
			self.hint.hide()

	def _on_remove(self) -> None:
		for item in self.list_widget.selectedItems():
			row = self.list_widget.row(item)
			self.list_widget.takeItem(row)

	def _on_rename(self) -> None:
		files = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
		if not files:
			return
		
		from .rename_dialog import RenameDialog
		dialog = RenameDialog(files, self)
		if dialog.exec() == QDialog.Accepted:
			# Refresh the list widget with new names
			self.list_widget.clear()
			for old_path, new_path in dialog.rename_operations:
				if old_path != new_path:  # Only add if actually renamed
					self.list_widget.addItem(new_path)
				else:
					self.list_widget.addItem(old_path)
