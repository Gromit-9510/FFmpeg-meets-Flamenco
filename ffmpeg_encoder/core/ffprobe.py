from __future__ import annotations

import json
import subprocess
from typing import Any, Dict


def run_ffprobe(path: str) -> Dict[str, Any]:
	cmd = [
		"ffprobe",
		"-v",
		"error",
		"-print_format",
		"json",
		"-show_format",
		"-show_streams",
		path,
	]
	proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
	if proc.returncode != 0:
		raise RuntimeError(proc.stderr.strip())
	return json.loads(proc.stdout)


def probe_duration_seconds(path: str) -> float | None:
	info = run_ffprobe(path)
	fmt = info.get("format", {})
	dur_str = fmt.get("duration")
	if dur_str is None:
		return None
	try:
		return float(dur_str)
	except ValueError:
		return None
