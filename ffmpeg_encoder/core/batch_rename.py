from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pandas as pd


def apply_pattern_rename(files: List[str], pattern: str) -> List[Tuple[str, str]]:
	"""Apply pattern-based renaming. Pattern supports {n:03d} for zero-padded numbers."""
	results = []
	for i, file_path in enumerate(files, 1):
		path = Path(file_path)
		try:
			new_name = pattern.format(n=i)
			new_path = path.parent / new_name
			results.append((file_path, str(new_path)))
		except (ValueError, KeyError):
			# Fallback to original if pattern is invalid
			results.append((file_path, file_path))
	return results


def apply_find_replace(files: List[str], find: str, replace: str, use_regex: bool = False) -> List[Tuple[str, str]]:
	"""Apply find/replace renaming to filenames."""
	results = []
	for file_path in files:
		path = Path(file_path)
		old_name = path.name
		
		if use_regex:
			try:
				new_name = re.sub(find, replace, old_name)
			except re.error:
				new_name = old_name
		else:
			new_name = old_name.replace(find, replace)
		
		new_path = path.parent / new_name
		results.append((file_path, str(new_path)))
	return results


def load_excel_mapping(excel_path: str, source_col: str = "source", target_col: str = "target") -> Dict[str, str]:
	"""Load filename mapping from Excel file."""
	try:
		df = pd.read_excel(excel_path)
		if source_col not in df.columns or target_col not in df.columns:
			raise ValueError(f"Required columns not found: {source_col}, {target_col}")
		
		mapping = {}
		for _, row in df.iterrows():
			source = str(row[source_col]).strip()
			target = str(row[target_col]).strip()
			if source and target:
				mapping[source] = target
		return mapping
	except Exception as e:
		raise ValueError(f"Failed to load Excel mapping: {e}")


def apply_excel_mapping(files: List[str], mapping: Dict[str, str]) -> List[Tuple[str, str]]:
	"""Apply Excel-based filename mapping."""
	results = []
	for file_path in files:
		path = Path(file_path)
		filename = path.name
		
		if filename in mapping:
			new_name = mapping[filename]
			new_path = path.parent / new_name
			results.append((file_path, str(new_path)))
		else:
			# Keep original if no mapping found
			results.append((file_path, file_path))
	return results


def preview_renames(rename_operations: List[Tuple[str, str]]) -> List[Dict[str, str]]:
	"""Preview rename operations without actually renaming files."""
	preview = []
	for old_path, new_path in rename_operations:
		old_name = Path(old_path).name
		new_name = Path(new_path).name
		preview.append({
			"old_path": old_path,
			"new_path": new_path,
			"old_name": old_name,
			"new_name": new_name,
			"changed": old_name != new_name
		})
	return preview


def execute_renames(rename_operations: List[Tuple[str, str]], dry_run: bool = False) -> List[Tuple[str, str, bool, str]]:
	"""Execute rename operations. Returns (old_path, new_path, success, error_message)."""
	results = []
	for old_path, new_path in rename_operations:
		if old_path == new_path:
			results.append((old_path, new_path, True, "No change needed"))
			continue
		
		if dry_run:
			results.append((old_path, new_path, True, "Dry run - would rename"))
			continue
		
		try:
			Path(old_path).rename(new_path)
			results.append((old_path, new_path, True, "Success"))
		except Exception as e:
			results.append((old_path, new_path, False, str(e)))
	
	return results
