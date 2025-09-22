#!/usr/bin/env python3
"""
FFmpeg Encoder 빌드 스크립트
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def clean_build():
    """빌드 폴더 정리"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"Cleaned {dir_name}/")
    
    # .spec 파일들 정리
    for spec_file in Path('.').glob('*.spec'):
        spec_file.unlink()
        print(f"Removed {spec_file}")

def build_exe():
    """실행 파일 빌드"""
    print("Building FFmpeg Encoder...")
    
    # PyInstaller 명령어
    cmd = [
        'pyinstaller',
        '--onefile',
        '--name', 'FFmpegEncoder',
        '--console',
        '--clean',
        '--add-data', 'ffmpeg_encoder;ffmpeg_encoder',
        '--hidden-import', 'PySide6.QtCore',
        '--hidden-import', 'PySide6.QtWidgets',
        '--hidden-import', 'PySide6.QtGui',
        '--hidden-import', 'pydantic',
        '--hidden-import', 'requests',
        '--hidden-import', 'colorlog',
        '--hidden-import', 'yaml',
        'main.py'
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Build successful!")
        print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    """메인 함수"""
    print("FFmpeg Encoder 빌드 시작...")
    
    # 1. 빌드 폴더 정리
    clean_build()
    
    # 2. 빌드 실행
    if build_exe():
        print("\n✅ 빌드 완료!")
        print("실행 파일 위치: dist/FFmpegEncoder.exe")
        
        # 3. 빌드 결과 확인
        exe_path = Path("dist/FFmpegEncoder.exe")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"파일 크기: {size_mb:.1f} MB")
        else:
            print("❌ 실행 파일을 찾을 수 없습니다.")
    else:
        print("❌ 빌드 실패")

if __name__ == "__main__":
    main()
