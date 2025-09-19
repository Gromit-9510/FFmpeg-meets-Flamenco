from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import List


class JobStatus(Enum):
	PENDING = auto()
	RUNNING = auto()
	DONE = auto()
	FAILED = auto()
	CANCELLED = auto()


@dataclass
class QueueItem:
	source_path: str
	output_path: str | None = None
	status: JobStatus = JobStatus.PENDING
	progress: float = 0.0
	message: str | None = None


class JobQueue:
	def __init__(self) -> None:
		self.items: List[QueueItem] = []

	def add(self, item: QueueItem) -> None:
		self.items.append(item)

	def remove_indices(self, indices: List[int]) -> None:
		for idx in sorted(indices, reverse=True):
			if 0 <= idx < len(self.items):
				self.items.pop(idx)

	def clear(self) -> None:
		self.items.clear()
