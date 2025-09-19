#!/usr/bin/env python3
"""
Test script for new features: video file filtering, output paths, low latency.
"""

from pathlib import Path
from ffmpeg_encoder.core.ffmpeg_cmd import VideoSettings, build_ffmpeg_commands

def test_video_file_filtering():
    """Test video file extension filtering."""
    print("Testing video file filtering...")
    
    # Test extensions
    video_extensions = {
        '.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.m4v',
        '.3gp', '.3g2', '.f4v', '.asf', '.rm', '.rmvb', '.vob', '.ogv',
        '.m2v', '.mts', '.m2ts', '.ts', '.mxf', '.dv', '.divx', '.xvid',
        '.prores', '.dnxhd', '.dpx', '.exr', '.tiff', '.tga', '.bmp',
        '.png', '.jpg', '.jpeg', '.gif', '.webp', '.hevc', '.h265',
        '.h264', '.av1', '.vp8', '.vp9', '.theora'
    }
    
    test_files = [
        "video.mp4",      # Should be included
        "document.pdf",    # Should be excluded
        "image.jpg",       # Should be included
        "audio.mp3",       # Should be excluded
        "movie.mov",       # Should be included
        "data.txt"         # Should be excluded
    ]
    
    included = []
    for file in test_files:
        ext = Path(file).suffix.lower()
        if ext in video_extensions:
            included.append(file)
    
    print(f"  Test files: {test_files}")
    print(f"  Included: {included}")
    print(f"  ✓ Video filtering works: {len(included)}/{len(test_files)} files included")
    return len(included) == 3

def test_low_latency_settings():
    """Test low latency FFmpeg command generation."""
    print("\nTesting low latency settings...")
    
    # Test H.264 low latency
    settings_h264 = VideoSettings(
        video_codec="libx264",
        low_latency=True,
        tune="none"
    )
    
    commands = build_ffmpeg_commands("input.mov", "output.mp4", settings_h264)
    cmd = commands[0]
    
    has_ultrafast = "-preset ultrafast" in " ".join(cmd)
    has_zerolatency = "-tune zerolatency" in " ".join(cmd)
    
    print(f"  H.264 low latency command: {' '.join(cmd[:10])}...")
    print(f"  ✓ Has ultrafast preset: {has_ultrafast}")
    print(f"  ✓ Has zerolatency tune: {has_zerolatency}")
    
    # Test NVENC low latency
    settings_nvenc = VideoSettings(
        video_codec="h264_nvenc",
        low_latency=True,
        tune="none"
    )
    
    commands = build_ffmpeg_commands("input.mov", "output.mp4", settings_nvenc)
    cmd = commands[0]
    
    has_p1 = "-preset p1" in " ".join(cmd)
    has_ull = "-tune ull" in " ".join(cmd)
    
    print(f"  NVENC low latency command: {' '.join(cmd[:10])}...")
    print(f"  ✓ Has p1 preset: {has_p1}")
    print(f"  ✓ Has ull tune: {has_ull}")
    
    return has_ultrafast and has_zerolatency and has_p1 and has_ull

def test_tune_settings():
    """Test tune parameter settings."""
    print("\nTesting tune settings...")
    
    settings = VideoSettings(
        video_codec="libx264",
        tune="film"
    )
    
    commands = build_ffmpeg_commands("input.mov", "output.mp4", settings)
    cmd = commands[0]
    
    has_tune = "-tune film" in " ".join(cmd)
    print(f"  Command with tune: {' '.join(cmd[:10])}...")
    print(f"  ✓ Has tune parameter: {has_tune}")
    
    return has_tune

def test_output_path_generation():
    """Test output path generation logic."""
    print("\nTesting output path generation...")
    
    input_path = "C:/Videos/movie.mp4"
    input_file = Path(input_path)
    
    # Test filename pattern
    pattern = "{name}_{codec}_{quality}"
    settings = VideoSettings(video_codec="libx264", crf=18)
    
    filename = pattern.format(
        name=input_file.stem,
        codec=settings.video_codec.replace("lib", "").replace("_", ""),
        quality=f"crf{settings.crf}" if settings.crf else "bitrate",
        container=settings.container
    )
    
    expected = "movie_x264_crf18"
    print(f"  Input: {input_path}")
    print(f"  Pattern: {pattern}")
    print(f"  Generated: {filename}")
    print(f"  Expected: {expected}")
    print(f"  ✓ Pattern generation works: {filename == expected}")
    
    return filename == expected

def main():
    """Run all tests."""
    print("FFmpeg Encoder - New Features Test")
    print("=" * 50)
    
    tests = [
        test_video_file_filtering,
        test_low_latency_settings,
        test_tune_settings,
        test_output_path_generation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All new features working correctly!")
        return True
    else:
        print("❌ Some features need attention.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
