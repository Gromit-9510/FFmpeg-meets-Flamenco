from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any

from PySide6.QtWidgets import (
	QDialog,
	QVBoxLayout,
	QHBoxLayout,
	QTabWidget,
	QWidget,
	QFormLayout,
	QLineEdit,
	QPushButton,
	QCheckBox,
	QLabel,
	QTableWidget,
	QTableWidgetItem,
	QHeaderView,
	QFileDialog,
	QMessageBox,
	QGroupBox,
)

from ..core.batch_rename import (
	apply_pattern_rename,
	apply_find_replace,
	load_excel_mapping,
	apply_excel_mapping,
	preview_renames,
	execute_renames,
)


class RenameDialog(QDialog):
	def __init__(self, files: List[str], parent=None) -> None:
		super().__init__(parent)
		self.files = files
		self.rename_operations: List[tuple[str, str]] = []
		self.setWindowTitle("Batch Rename Files")
		self.setModal(True)
		self.resize(800, 600)
		
		layout = QVBoxLayout(self)
		
		# Tabs for different rename methods
		tabs = QTabWidget()
		tabs.addTab(self._build_pattern_tab(), "Pattern")
		tabs.addTab(self._build_find_replace_tab(), "Find & Replace")
		tabs.addTab(self._build_excel_tab(), "Excel Mapping")
		layout.addWidget(tabs)
		
		# Preview table
		preview_group = QGroupBox("Preview")
		preview_layout = QVBoxLayout(preview_group)
		
		self.preview_table = QTableWidget()
		self.preview_table.setColumnCount(4)
		self.preview_table.setHorizontalHeaderLabels(["Original", "New Name", "Changed", "Status"])
		self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
		preview_layout.addWidget(self.preview_table)
		
		layout.addWidget(preview_group)
		
		# Buttons
		button_layout = QHBoxLayout()
		self.preview_btn = QPushButton("Preview")
		self.execute_btn = QPushButton("Execute Renames")
		self.cancel_btn = QPushButton("Cancel")
		
		button_layout.addWidget(self.preview_btn)
		button_layout.addWidget(self.execute_btn)
		button_layout.addStretch()
		button_layout.addWidget(self.cancel_btn)
		
		layout.addLayout(button_layout)
		
		# Connect signals
		self.preview_btn.clicked.connect(self._preview_renames)
		self.execute_btn.clicked.connect(self._execute_renames)
		self.cancel_btn.clicked.connect(self.reject)

	def _build_pattern_tab(self) -> QWidget:
		w = QWidget()
		layout = QFormLayout(w)
		
		self.pattern_input = QLineEdit()
		self.pattern_input.setPlaceholderText("e.g., video_{n:03d}.mp4")
		layout.addRow("Pattern:", self.pattern_input)
		
		help_label = QLabel("Use {n:03d} for zero-padded numbers (001, 002, etc.)")
		help_label.setStyleSheet("color: gray; font-size: 10px;")
		layout.addRow(help_label)
		
		return w

	def _build_find_replace_tab(self) -> QWidget:
		w = QWidget()
		layout = QFormLayout(w)
		
		self.find_input = QLineEdit()
		self.find_input.setPlaceholderText("Text to find")
		layout.addRow("Find:", self.find_input)
		
		self.replace_input = QLineEdit()
		self.replace_input.setPlaceholderText("Replacement text")
		layout.addRow("Replace with:", self.replace_input)
		
		self.regex_checkbox = QCheckBox("Use regular expressions")
		layout.addRow(self.regex_checkbox)
		
		return w

	def _build_excel_tab(self) -> QWidget:
		w = QWidget()
		layout = QFormLayout(w)
		
		self.excel_path_input = QLineEdit()
		self.excel_path_input.setPlaceholderText("Path to Excel file")
		layout.addRow("Excel file:", self.excel_path_input)
		
		browse_btn = QPushButton("Browse...")
		browse_btn.clicked.connect(self._browse_excel)
		layout.addRow(browse_btn)
		
		self.source_col_input = QLineEdit()
		self.source_col_input.setText("source")
		self.source_col_input.setPlaceholderText("Source column name")
		layout.addRow("Source column:", self.source_col_input)
		
		self.target_col_input = QLineEdit()
		self.target_col_input.setText("target")
		self.target_col_input.setPlaceholderText("Target column name")
		layout.addRow("Target column:", self.target_col_input)
		
		return w

	def _browse_excel(self) -> None:
		path, _ = QFileDialog.getOpenFileName(self, "Select Excel file", filter="*.xlsx *.xls")
		if path:
			self.excel_path_input.setText(path)

	def _preview_renames(self) -> None:
		try:
			# Determine which tab is active and get rename operations
			if hasattr(self, 'pattern_input') and self.pattern_input.text().strip():
				pattern = self.pattern_input.text().strip()
				self.rename_operations = apply_pattern_rename(self.files, pattern)
			elif hasattr(self, 'find_input') and self.find_input.text().strip():
				find = self.find_input.text().strip()
				replace = self.replace_input.text().strip()
				use_regex = self.regex_checkbox.isChecked()
				self.rename_operations = apply_find_replace(self.files, find, replace, use_regex)
			elif hasattr(self, 'excel_path_input') and self.excel_path_input.text().strip():
				excel_path = self.excel_path_input.text().strip()
				source_col = self.source_col_input.text().strip() or "source"
				target_col = self.target_col_input.text().strip() or "target"
				mapping = load_excel_mapping(excel_path, source_col, target_col)
				self.rename_operations = apply_excel_mapping(self.files, mapping)
			else:
				QMessageBox.warning(self, "Preview", "Please fill in the required fields for the selected method.")
				return
			
			# Update preview table
			preview_data = preview_renames(self.rename_operations)
			self.preview_table.setRowCount(len(preview_data))
			
			for row, data in enumerate(preview_data):
				self.preview_table.setItem(row, 0, QTableWidgetItem(data["old_name"]))
				self.preview_table.setItem(row, 1, QTableWidgetItem(data["new_name"]))
				self.preview_table.setItem(row, 2, QTableWidgetItem("Yes" if data["changed"] else "No"))
				self.preview_table.setItem(row, 3, QTableWidgetItem("Ready"))
			
			self.execute_btn.setEnabled(True)
			
		except Exception as e:
			QMessageBox.critical(self, "Preview Error", f"Failed to preview renames: {e}")

	def _execute_renames(self) -> None:
		if not self.rename_operations:
			QMessageBox.warning(self, "Execute", "Please preview the renames first.")
			return
		
		reply = QMessageBox.question(
			self, 
			"Confirm Rename", 
			f"Are you sure you want to rename {len(self.rename_operations)} files?",
			QMessageBox.Yes | QMessageBox.No
		)
		
		if reply == QMessageBox.Yes:
			results = execute_renames(self.rename_operations, dry_run=False)
			
			# Update preview table with results
			for row, (old_path, new_path, success, message) in enumerate(results):
				status_item = QTableWidgetItem("Success" if success else f"Error: {message}")
				if not success:
					status_item.setStyleSheet("color: red;")
				self.preview_table.setItem(row, 3, status_item)
			
			success_count = sum(1 for _, _, success, _ in results if success)
			QMessageBox.information(
				self, 
				"Rename Complete", 
				f"Successfully renamed {success_count} out of {len(results)} files."
			)
			
			if success_count > 0:
				self.accept()
