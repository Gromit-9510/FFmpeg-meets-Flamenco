from __future__ import annotations

import logging
from typing import Callable
from colorlog import ColoredFormatter


def create_logger(name: str = "ffmpeg_encoder") -> logging.Logger:
	logger = logging.getLogger(name)
	if logger.handlers:
		return logger
	logger.setLevel(logging.INFO)
	handler = logging.StreamHandler()
	formatter = ColoredFormatter(
		"%(log_color)s[%(levelname)s]%(reset)s %(message)s",
		log_colors={
			"DEBUG": "cyan",
			"INFO": "white",
			"WARNING": "yellow",
			"ERROR": "red",
			"CRITICAL": "bold_red",
		},
	)
	handler.setFormatter(formatter)
	logger.addHandler(handler)
	return logger


class QtLogHandler(logging.Handler):
	def __init__(self, writer: Callable[[str], None]) -> None:
		super().__init__()
		self.writer = writer

	def emit(self, record: logging.LogRecord) -> None:
		try:
			msg = self.format(record)
			self.writer(msg)
		except Exception:
			pass
