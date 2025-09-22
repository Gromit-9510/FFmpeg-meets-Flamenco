from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
	QWidget,
	QVBoxLayout,
	QHBoxLayout,
	QListWidget,
	QPushButton,
	QFileDialog,
	QLabel,
	QDialog,
	QTreeWidget,
	QTreeWidgetItem,
	QCheckBox,
	QMessageBox,
	QHeaderView,
)


@dataclass
class QueueFileItem:
	path: str
	checked: bool = True
	folder_path: str = ""
	display_name: str = ""

class QueuePanel(QWidget):
	# Signals
	selection_changed = Signal(list)  # Emits list of checked file paths
	
	def __init__(self) -> None:
		super().__init__()
		layout = QVBoxLayout(self)

		controls = QHBoxLayout()
		self.add_files_btn = QPushButton("Add Files")
		self.add_folder_btn = QPushButton("Add Folder")
		self.remove_btn = QPushButton("Remove Checked")
		self.select_all_btn = QPushButton("Check All")
		self.deselect_all_btn = QPushButton("Uncheck All")
		
		controls.addWidget(self.add_files_btn)
		controls.addWidget(self.add_folder_btn)
		controls.addWidget(self.remove_btn)
		controls.addWidget(self.select_all_btn)
		controls.addWidget(self.deselect_all_btn)
		controls.addStretch(1)

		# Tree widget for hierarchical display with checkboxes
		self.tree_widget = QTreeWidget()
		self.tree_widget.setHeaderLabels(["File", "Path", "Status"])
		self.tree_widget.setAlternatingRowColors(True)
		self.tree_widget.setSelectionMode(QTreeWidget.ExtendedSelection)  # Allow CTRL/Shift selection
		
		# Set column widths
		self.tree_widget.setColumnWidth(0, 300)  # File name - wider
		self.tree_widget.setColumnWidth(1, 200)  # Path
		self.tree_widget.setColumnWidth(2, 100)  # Status
		
		# Enable column resizing
		self.tree_widget.header().setStretchLastSection(False)
		self.tree_widget.header().setSectionResizeMode(0, QHeaderView.Stretch)  # File name stretches
		self.tree_widget.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Path auto-resize
		self.tree_widget.header().setSectionResizeMode(2, QHeaderView.Fixed)  # Status fixed width
		self.tree_widget.setStyleSheet("""
			QTreeWidget::item {
				padding: 4px;
				border-bottom: 1px solid #ddd;
			}
			QTreeWidget::item:selected {
				background-color: #0078d4;
				color: white;
			}
			QTreeWidget::item:checked {
				background-color: #e6f3ff;
			}
		""")
		
		# Store file items for easy access
		self.file_items: Dict[str, QueueFileItem] = {}
		self.folder_items: Dict[str, QTreeWidgetItem] = {}
		
		# Drag selection variables
		self._drag_start_item = None
		self._drag_start_checked = False
		
		layout.addLayout(controls)
		layout.addWidget(self.tree_widget)

		self._connect_signals()

	def _connect_signals(self) -> None:
		self.add_files_btn.clicked.connect(self._on_add_files)
		self.add_folder_btn.clicked.connect(self._on_add_folder)
		self.remove_btn.clicked.connect(self._on_remove)
		self.select_all_btn.clicked.connect(self._on_select_all)
		self.deselect_all_btn.clicked.connect(self._on_deselect_all)
		self.tree_widget.itemChanged.connect(self._on_item_changed)
		self.tree_widget.itemPressed.connect(self._on_item_pressed)
		self.tree_widget.itemClicked.connect(self._on_item_clicked)

	def _on_add_files(self) -> None:
		files, _ = QFileDialog.getOpenFileNames(self, "Select Video Files")
		for f in files:
			self._add_file_to_queue(f)

	def _on_add_folder(self) -> None:
		folder = QFileDialog.getExistingDirectory(self, "Select Folder")
		if folder:
			self._add_folder_to_queue(folder)

	def _add_file_to_queue(self, file_path: str) -> None:
		path = Path(file_path)
		
		# Create file item
		file_item = QueueFileItem(
			path=file_path,
			checked=True,
			folder_path=str(path.parent),
			display_name=path.name
		)
		self.file_items[file_path] = file_item
		
		# Create tree item with checkbox
		tree_item = QTreeWidgetItem()
		tree_item.setText(0, path.name)
		tree_item.setText(1, str(path.parent))
		tree_item.setText(2, "Ready")
		tree_item.setCheckState(0, Qt.Checked)
		tree_item.setData(0, Qt.UserRole, file_path)  # Store file path
		
		# Add to tree (no grouping for individual files)
		self.tree_widget.addTopLevelItem(tree_item)

	def _add_folder_to_queue(self, folder_path: str) -> None:
		folder = Path(folder_path)
		video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
		
		video_files = []
		for ext in video_extensions:
			video_files.extend(folder.glob(f"*{ext}"))
			video_files.extend(folder.glob(f"*{ext.upper()}"))
		
		if video_files:
			# Create folder group
			folder_item = QTreeWidgetItem()
			folder_item.setText(0, f"📁 {folder.name}")
			folder_item.setText(1, str(folder))
			folder_item.setText(2, f"{len(video_files)} files")
			folder_item.setCheckState(0, Qt.Checked)
			folder_item.setData(0, Qt.UserRole, f"folder:{folder_path}")
			
			# Add folder to tree
			self.tree_widget.addTopLevelItem(folder_item)
			self.folder_items[folder_path] = folder_item
			
			# Add video files as children
			for video_file in video_files:
				file_path = str(video_file)
				file_item = QueueFileItem(
					path=file_path,
					checked=True,
					folder_path=folder_path,
					display_name=video_file.name
				)
				self.file_items[file_path] = file_item
				
				child_item = QTreeWidgetItem()
				child_item.setText(0, video_file.name)
				child_item.setText(1, str(video_file.parent))
				child_item.setText(2, "Ready")
				child_item.setCheckState(0, Qt.Checked)
				child_item.setData(0, Qt.UserRole, file_path)
				
				folder_item.addChild(child_item)
		else:
			QMessageBox.information(self, "No Videos", f"No video files found in {folder.name}")

	def _find_item_by_path(self, item: QTreeWidgetItem, target_path: str) -> bool:
		"""Find tree item by file path recursively."""
		item_path = item.data(0, Qt.UserRole)
		if item_path == target_path:
			return True
		
		for i in range(item.childCount()):
			if self._find_item_by_path(item.child(i), target_path):
				return True
		return False

	def _on_remove(self) -> None:
		"""Remove checked items from tree."""
		checked_items = []
		for file_path, file_item in self.file_items.items():
			if file_item.checked:
				# Find the tree item for this file
				for i in range(self.tree_widget.topLevelItemCount()):
					item = self.tree_widget.topLevelItem(i)
					if self._find_item_by_path(item, file_path):
						checked_items.append(item)
						break
		
		for item in checked_items:
			file_path = item.data(0, Qt.UserRole)
			if file_path and not file_path.startswith("folder:"):
				# Remove from file_items
				if file_path in self.file_items:
					del self.file_items[file_path]
			elif file_path and file_path.startswith("folder:"):
				# Remove folder and all its children
				folder_path = file_path[7:]  # Remove "folder:" prefix
				if folder_path in self.folder_items:
					# Remove all child files from file_items
					for i in range(item.childCount()):
						child = item.child(i)
						child_path = child.data(0, Qt.UserRole)
						if child_path in self.file_items:
							del self.file_items[child_path]
					del self.folder_items[folder_path]
			
			# Remove from tree
			parent = item.parent()
			if parent:
				parent.removeChild(item)
			else:
				self.tree_widget.takeTopLevelItem(self.tree_widget.indexOfTopLevelItem(item))

	def _remove_item_recursive(self, item: QTreeWidgetItem, target_path: str) -> bool:
		"""Recursively remove item with target_path."""
		file_path = item.data(0, Qt.UserRole)
		if file_path == target_path:
			parent = item.parent()
			if parent:
				parent.removeChild(item)
			else:
				self.tree_widget.takeTopLevelItem(self.tree_widget.indexOfTopLevelItem(item))
			if file_path in self.file_items:
				del self.file_items[file_path]
			return True
		
		# Check children
		for i in range(item.childCount()):
			if self._remove_item_recursive(item.child(i), target_path):
				return True
		return False

	def _on_select_all(self) -> None:
		"""Select all items."""
		for i in range(self.tree_widget.topLevelItemCount()):
			item = self.tree_widget.topLevelItem(i)
			self._set_item_checked_recursive(item, True)

	def _on_deselect_all(self) -> None:
		"""Deselect all items."""
		for i in range(self.tree_widget.topLevelItemCount()):
			item = self.tree_widget.topLevelItem(i)
			self._set_item_checked_recursive(item, False)

	def _set_item_checked_recursive(self, item: QTreeWidgetItem, checked: bool) -> None:
		"""Recursively set item checked state."""
		item.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
		
		# Update file_items for file items
		file_path = item.data(0, Qt.UserRole)
		if file_path and not file_path.startswith("folder:") and file_path in self.file_items:
			self.file_items[file_path].checked = checked
		
		for i in range(item.childCount()):
			self._set_item_checked_recursive(item.child(i), checked)

	def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
		"""Handle item checkbox changes."""
		if column == 0:  # Checkbox column
			file_path = item.data(0, Qt.UserRole)
			checked = item.checkState(0) == Qt.Checked
			
			if file_path and file_path.startswith("folder:"):
				# Folder checkbox changed - update all children
				self._set_item_checked_recursive(item, checked)
				# Update file_items for all child files
				for i in range(item.childCount()):
					child = item.child(i)
					child_path = child.data(0, Qt.UserRole)
					if child_path and child_path in self.file_items:
						self.file_items[child_path].checked = checked
			elif file_path and not file_path.startswith("folder:"):
				# File checkbox changed
				if file_path in self.file_items:
					self.file_items[file_path].checked = checked
			
			self.selection_changed.emit(self.get_checked_files())

	def _on_item_pressed(self, item: QTreeWidgetItem, column: int) -> None:
		"""Handle item press for drag selection."""
		if column == 0:  # Checkbox column
			self._drag_start_item = item
			self._drag_start_checked = item.checkState(0) == Qt.Checked

	def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
		"""Handle item click for multi-selection checkbox changes."""
		if column == 0:  # Checkbox column
			# Check if multiple items are selected
			selected_items = self.tree_widget.selectedItems()
			if len(selected_items) > 1 and item in selected_items:
				# Apply checkbox state to all selected items
				new_state = item.checkState(0)
				for selected_item in selected_items:
					if selected_item != item:  # Don't change the clicked item again
						selected_item.setCheckState(0, new_state)
						# Update file_items for file items
						file_path = selected_item.data(0, Qt.UserRole)
						if file_path and not file_path.startswith("folder:") and file_path in self.file_items:
							self.file_items[file_path].checked = new_state == Qt.Checked
				
				self.selection_changed.emit(self.get_checked_files())



	def get_checked_files(self) -> List[str]:
		"""Get list of checked file paths."""
		checked_files = []
		for file_path, file_item in self.file_items.items():
			if file_item.checked:
				checked_files.append(file_path)
		return checked_files

	def get_all_files(self) -> List[str]:
		"""Get list of all file paths."""
		return list(self.file_items.keys())

	def clear(self) -> None:
		"""Clear all items."""
		self.tree_widget.clear()
		self.file_items.clear()
		self.folder_items.clear()

	def set_item_status(self, file_path: str, status: str) -> None:
		"""Set status for a specific file."""
		for i in range(self.tree_widget.topLevelItemCount()):
			item = self.tree_widget.topLevelItem(i)
			if self._set_item_status_recursive(item, file_path, status):
				break

	def _set_item_status_recursive(self, item: QTreeWidgetItem, target_path: str, status: str) -> bool:
		"""Recursively set item status."""
		file_path = item.data(0, Qt.UserRole)
		if file_path == target_path:
			item.setText(2, status)
			return True
		
		for i in range(item.childCount()):
			if self._set_item_status_recursive(item.child(i), target_path, status):
				return True
		return False

	# Backward compatibility methods
	@property
	def list_widget(self) -> QTreeWidget:
		"""Backward compatibility - return tree_widget as list_widget."""
		return self.tree_widget