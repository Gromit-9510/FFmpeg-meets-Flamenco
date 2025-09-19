#!/usr/bin/env python3
"""
Test script to verify FFmpeg Encoder functionality.
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from ffmpeg_encoder.app import main
        print("✓ Main app imports successfully")
    except Exception as e:
        print(f"✗ Main app import failed: {e}")
        return False
    
    try:
        from ffmpeg_encoder.core.ffmpeg_cmd import VideoSettings, build_ffmpeg_commands
        print("✓ Core modules import successfully")
    except Exception as e:
        print(f"✗ Core modules import failed: {e}")
        return False
    
    try:
        from ffmpeg_encoder.ui.main_window import MainWindow
        print("✓ UI modules import successfully")
    except Exception as e:
        print(f"✗ UI modules import failed: {e}")
        return False
    
    return True

def test_ffmpeg_detection():
    """Test FFmpeg detection."""
    print("\nTesting FFmpeg detection...")
    
    try:
        from ffmpeg_encoder.utils.ffmpeg_check import check_ffmpeg_installation
        info = check_ffmpeg_installation()
        
        if info['ffmpeg_available']:
            print(f"✓ FFmpeg found: {info['ffmpeg_path']}")
            print(f"✓ Version: {info['version']}")
            print(f"✓ GPU encoders: {len(info['gpu_encoders'])}")
            return True
        else:
            print("✗ FFmpeg not found")
            return False
    except Exception as e:
        print(f"✗ FFmpeg detection failed: {e}")
        return False

def test_command_building():
    """Test FFmpeg command building."""
    print("\nTesting command building...")
    
    try:
        from ffmpeg_encoder.core.ffmpeg_cmd import VideoSettings, build_ffmpeg_commands
        
        settings = VideoSettings(
            container="mp4",
            video_codec="libx264",
            crf=18,
            audio_codec="aac"
        )
        
        commands = build_ffmpeg_commands("input.mov", "output.mp4", settings)
        
        if commands and len(commands) > 0:
            print(f"✓ Command building works: {len(commands)} command(s) generated")
            print(f"  Example: {' '.join(commands[0][:5])}...")
            return True
        else:
            print("✗ No commands generated")
            return False
    except Exception as e:
        print(f"✗ Command building failed: {e}")
        return False

def test_preset_system():
    """Test preset system."""
    print("\nTesting preset system...")
    
    try:
        from ffmpeg_encoder.core.presets import Preset, PresetStore
        
        # Create a test preset
        preset = Preset(
            name="test_preset",
            container="mp4",
            video_codec="libx264",
            crf=18
        )
        
        # Test preset creation
        if preset.name == "test_preset":
            print("✓ Preset creation works")
            return True
        else:
            print("✗ Preset creation failed")
            return False
    except Exception as e:
        print(f"✗ Preset system failed: {e}")
        return False

def main():
    """Run all tests."""
    print("FFmpeg Encoder - System Test")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_ffmpeg_detection,
        test_command_building,
        test_preset_system
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n{'='*40}")
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! Application is ready.")
        return True
    else:
        print("✗ Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
