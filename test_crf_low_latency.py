#!/usr/bin/env python3
"""
Test script to verify CRF works in low latency mode
"""

from ffmpeg_encoder.core.ffmpeg_cmd import build_ffmpeg_commands, VideoSettings

def test_crf_low_latency():
    """Test CRF in low latency mode"""
    
    input_path = "test_input.mp4"
    
    # Test H.264 Low Latency
    print("=== H.264 Low Latency Tests ===")
    settings = VideoSettings()
    settings.video_codec = "libx264_ll"  # Low latency H.264
    settings.crf = 0  # Lossless
    settings.bitrate = None
    settings.two_pass = False
    settings.gpu_enable = False
    settings.low_latency = True
    settings.tune = "none"
    settings.audio_codec = "aac"
    settings.audio_bitrate = "192k"
    settings.max_filesize = None
    settings.extra_params = None
    
    commands = build_ffmpeg_commands(input_path, "test_h264_crf0.mp4", settings)
    print("H.264 CRF 0:", ' '.join(commands[0]))
    
    settings.crf = 18
    commands = build_ffmpeg_commands(input_path, "test_h264_crf18.mp4", settings)
    print("H.264 CRF 18:", ' '.join(commands[0]))
    
    print("\n" + "="*50)
    
    # Test H.265 Low Latency
    print("=== H.265 Low Latency Tests ===")
    settings.video_codec = "libx265_ll"  # Low latency H.265
    settings.crf = 0  # Lossless
    
    commands = build_ffmpeg_commands(input_path, "test_h265_crf0.mp4", settings)
    print("H.265 CRF 0:", ' '.join(commands[0]))
    
    settings.crf = 18
    commands = build_ffmpeg_commands(input_path, "test_h265_crf18.mp4", settings)
    print("H.265 CRF 18:", ' '.join(commands[0]))
    
    print("\n" + "="*50)
    
    # Test H.264 GPU Low Latency
    print("=== H.264 GPU Low Latency Tests ===")
    settings.video_codec = "h264_nvenc_ll"  # Low latency H.264 GPU
    settings.gpu_enable = True
    settings.crf = 0  # Lossless
    
    commands = build_ffmpeg_commands(input_path, "test_h264_gpu_crf0.mp4", settings)
    print("H.264 GPU CRF 0:", ' '.join(commands[0]))
    
    settings.crf = 18
    commands = build_ffmpeg_commands(input_path, "test_h264_gpu_crf18.mp4", settings)
    print("H.264 GPU CRF 18:", ' '.join(commands[0]))
    
    print("\n" + "="*50)
    
    # Test H.265 GPU Low Latency
    print("=== H.265 GPU Low Latency Tests ===")
    settings.video_codec = "hevc_nvenc_ll"  # Low latency H.265 GPU
    settings.crf = 0  # Lossless
    
    commands = build_ffmpeg_commands(input_path, "test_h265_gpu_crf0.mp4", settings)
    print("H.265 GPU CRF 0:", ' '.join(commands[0]))
    
    settings.crf = 18
    commands = build_ffmpeg_commands(input_path, "test_h265_gpu_crf18.mp4", settings)
    print("H.265 GPU CRF 18:", ' '.join(commands[0]))

if __name__ == "__main__":
    test_crf_low_latency()
