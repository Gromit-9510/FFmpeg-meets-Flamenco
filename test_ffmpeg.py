#!/usr/bin/env python3
"""
Quick test script to verify FFmpeg installation and available codecs.
"""

from ffmpeg_encoder.utils.ffmpeg_check import check_ffmpeg_installation, get_gpu_encoders, is_gpu_available

def main():
    print("FFmpeg Encoder - System Check")
    print("=" * 40)
    
    info = check_ffmpeg_installation()
    
    print(f"FFmpeg Available: {info['ffmpeg_available']}")
    print(f"FFprobe Available: {info['ffprobe_available']}")
    
    if info['ffmpeg_available']:
        print(f"FFmpeg Path: {info['ffmpeg_path']}")
        print(f"Version: {info['version']}")
        
        print(f"\nAvailable Codecs: {len(info['codecs'])}")
        print(f"Available Formats: {len(info['formats'])}")
        print(f"Available Encoders: {len(info['encoders'])}")
        
        gpu_encoders = get_gpu_encoders()
        print(f"\nGPU Encoders: {len(gpu_encoders)}")
        if gpu_encoders:
            print("  - " + "\n  - ".join(gpu_encoders[:10]))  # Show first 10
            if len(gpu_encoders) > 10:
                print(f"  ... and {len(gpu_encoders) - 10} more")
        
        print(f"\nGPU Available: {is_gpu_available()}")
    else:
        print("FFmpeg not found! Please install FFmpeg and ensure it's on PATH.")
        print("You can download it from: https://ffmpeg.org/download.html")

if __name__ == "__main__":
    main()
