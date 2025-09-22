from __future__ import annotations

import subprocess
import threading
from typing import Callable, List, Optional


class FFmpegRunner:
	def __init__(self, on_log: Callable[[str], None]) -> None:
		self.on_log = on_log
		self._proc: Optional[subprocess.Popen[str]] = None

	def run(self, cmd: List[str]) -> int:
		self.on_log("Running: " + " ".join(cmd))
		
		try:
			self._proc = subprocess.Popen(
				cmd,
				stderr=subprocess.PIPE,
				stdout=subprocess.PIPE,
				text=True,
				bufsize=1,
				universal_newlines=True,
				encoding='utf-8',
				errors='replace'
			)
		except Exception as e:
			self.on_log(f"Failed to start FFmpeg: {e}")
			return -1

		def _pipe(stream):
			assert stream is not None
			try:
				for line in stream:
					self.on_log(line.rstrip())
			except UnicodeDecodeError as e:
				self.on_log(f"Encoding error: {e}")
			except Exception as e:
				self.on_log(f"Pipe error: {e}")

		threads: list[threading.Thread] = []
		if self._proc.stdout:
			threads.append(threading.Thread(target=_pipe, args=(self._proc.stdout,), daemon=True))
			threads[-1].start()
		if self._proc.stderr:
			threads.append(threading.Thread(target=_pipe, args=(self._proc.stderr,), daemon=True))
			threads[-1].start()

		try:
			code = self._proc.wait()
			self.on_log(f"FFmpeg process finished with exit code: {code}")
		except Exception as e:
			self.on_log(f"Error waiting for FFmpeg: {e}")
			code = -1
		
		for t in threads:
			t.join(timeout=0.2)
		return code

	def terminate(self) -> None:
		if self._proc and self._proc.poll() is None:
			self._proc.terminate()
	
	def cleanup(self) -> None:
		"""Clean up resources."""
		if self._proc:
			if self._proc.poll() is None:
				self._proc.terminate()
			self._proc = None
