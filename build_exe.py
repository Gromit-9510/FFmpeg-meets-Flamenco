#!/usr/bin/env python3
"""
Build script for creating Windows executable.
Run this after installing dependencies.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
	"""Run a command and return success status."""
	print(f"\n{description}...")
	print(f"Running: {' '.join(cmd)}")
	
	try:
		result = subprocess.run(cmd, check=True, capture_output=True, text=True)
		print("✓ Success")
		return True
	except subprocess.CalledProcessError as e:
		print(f"✗ Failed: {e}")
		if e.stdout:
			print(f"STDOUT: {e.stdout}")
		if e.stderr:
			print(f"STDERR: {e.stderr}")
		return False


def main():
	"""Build the Windows executable."""
	print("FFmpeg Encoder - Windows EXE Builder")
	print("=" * 40)
	
	# Check if we're in the right directory
	if not Path("pyproject.toml").exists():
		print("Error: pyproject.toml not found. Run this from the project root.")
		sys.exit(1)
	
	# Install dependencies
	if not run_command([sys.executable, "-m", "pip", "install", "-U", "pip"], "Upgrading pip"):
		sys.exit(1)
	
	if not run_command([sys.executable, "-m", "pip", "install", "-e", "."], "Installing project in development mode"):
		sys.exit(1)
	
	if not run_command([sys.executable, "-m", "pip", "install", "pyinstaller"], "Installing PyInstaller"):
		sys.exit(1)
	
	# Clean previous builds
	dist_dir = Path("dist")
	if dist_dir.exists():
		print("\nCleaning previous builds...")
		import shutil
		shutil.rmtree(dist_dir)
	
	# Build executable
	if not run_command([sys.executable, "-m", "PyInstaller", "build.spec"], "Building executable"):
		sys.exit(1)
	
	# Check if build was successful
	exe_path = dist_dir / "FFmpegEncoder.exe"
	if exe_path.exists():
		print(f"\n✓ Build successful!")
		print(f"Executable: {exe_path.absolute()}")
		print(f"Size: {exe_path.stat().st_size / (1024*1024):.1f} MB")
		print(f"\nYou can now run: {exe_path.name}")
	else:
		print("\n✗ Build failed - executable not found")
		sys.exit(1)


if __name__ == "__main__":
	main()
