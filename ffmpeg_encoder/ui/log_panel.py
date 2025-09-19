from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout


class LogPanel(QWidget):
	def __init__(self) -> None:
		super().__init__()
		layout = QVBoxLayout(self)
		self.text = QTextEdit()
		self.text.setReadOnly(True)
		btns = QHBoxLayout()
		self.clear_btn = QPushButton("Clear")
		self.copy_btn = QPushButton("Copy")
		btns.addWidget(self.clear_btn)
		btns.addWidget(self.copy_btn)
		btns.addStretch(1)
		layout.addLayout(btns)
		layout.addWidget(self.text)
		self.clear_btn.clicked.connect(self.text.clear)
		self.copy_btn.clicked.connect(self._on_copy)

	def append_line(self, line: str) -> None:
		self.text.append(line)

	def _on_copy(self) -> None:
		self.text.selectAll()
		self.text.copy()
