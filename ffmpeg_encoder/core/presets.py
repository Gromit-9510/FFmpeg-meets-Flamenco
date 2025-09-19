from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Any
import json
from pydantic import BaseModel, Field, ValidationError


class Preset(BaseModel):
	name: str
	container: str = "mp4"
	video_codec: str = "libx264"
	crf: Optional[int] = 18
	bitrate: Optional[str] = None
	two_pass: bool = False
	gpu_enable: bool = False
	low_latency: bool = False
	tune: str = "none"
	audio_codec: str = "aac"
	audio_bitrate: Optional[str] = "192k"
	max_filesize: Optional[str] = None
	additional_params: Optional[str] = Field(default=None, description="Extra ffmpeg args string")
	extra_params: Optional[str] = Field(default=None, description="Extra ffmpeg args string")

	def to_settings(self) -> Dict[str, Any]:
		return self.model_dump()


class PresetStore:
	def __init__(self, root: Optional[Path] = None) -> None:
		if root is None:
			root = Path.home() / ".ffmpeg_encoder" / "presets"
		self.root = root
		self.root.mkdir(parents=True, exist_ok=True)

	def list_presets(self) -> list[str]:
		return [p.stem for p in self.root.glob("*.json")]

	def save(self, preset: Preset) -> Path:
		path = self.root / f"{preset.name}.json"
		data = preset.model_dump()
		if not data.get("additional_params"):
			data["additional_params"] = None
		path.write_text(json.dumps(data, indent=2), encoding="utf-8")
		return path

	def load(self, name: str) -> Preset:
		path = self.root / f"{name}.json"
		data = json.loads(path.read_text(encoding="utf-8"))
		return Preset(**data)

	def delete(self, name: str) -> None:
		path = self.root / f"{name}.json"
		if path.exists():
			path.unlink()

	def export_to(self, name: str, dest_file: Path) -> Path:
		preset = self.load(name)
		dest_file.write_text(preset.model_dump_json(indent=2), encoding="utf-8")
		return dest_file

	def import_from(self, src_file: Path) -> Preset:
		data = json.loads(src_file.read_text(encoding="utf-8"))
		preset = Preset(**data)
		self.save(preset)
		return preset

	def export_preset(self, settings: Dict[str, Any], file_path: str) -> None:
		"""Export settings as a preset to a file."""
		preset = Preset(**settings)
		Path(file_path).write_text(preset.model_dump_json(indent=2), encoding="utf-8")

	def import_preset(self, file_path: str) -> Preset:
		"""Import a preset from a file."""
		data = json.loads(Path(file_path).read_text(encoding="utf-8"))
		return Preset(**data)
