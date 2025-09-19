#!/usr/bin/env python3
"""
QP 설정이 제대로 작동하는지 테스트하는 스크립트
"""

from ffmpeg_encoder.core.ffmpeg_cmd import VideoSettings, build_ffmpeg_commands

def test_qp_settings():
    """QP 설정이 제대로 적용되는지 테스트"""
    
    print("=== QP 설정 테스트 ===\n")
    
    # H.264 GPU 일반 모드 테스트
    print("1. H.264 GPU 일반 모드:")
    settings1 = VideoSettings(
        video_codec="h264_nvenc",
        crf=18,  # QP 18
        container="mp4"
    )
    cmd1 = build_ffmpeg_commands("input.mp4", "output1.mp4", settings1)
    print(f"명령어: {' '.join(cmd1[0])}")
    print(f"QP 파라미터 포함: {'-qp' in cmd1[0]}")
    print()
    
    # H.264 GPU 저지연 모드 테스트
    print("2. H.264 GPU 저지연 모드:")
    settings2 = VideoSettings(
        video_codec="h264_nvenc_ll",
        crf=18,  # QP 18
        container="mp4"
    )
    cmd2 = build_ffmpeg_commands("input.mp4", "output2.mp4", settings2)
    print(f"명령어: {' '.join(cmd2[0])}")
    print(f"QP 파라미터 포함: {'-qp' in cmd2[0]}")
    print()
    
    # H.265 GPU 일반 모드 테스트
    print("3. H.265 GPU 일반 모드:")
    settings3 = VideoSettings(
        video_codec="hevc_nvenc",
        crf=20,  # QP 20
        container="mp4"
    )
    cmd3 = build_ffmpeg_commands("input.mp4", "output3.mp4", settings3)
    print(f"명령어: {' '.join(cmd3[0])}")
    print(f"QP 파라미터 포함: {'-qp' in cmd3[0]}")
    print()
    
    # H.265 GPU 저지연 모드 테스트
    print("4. H.265 GPU 저지연 모드:")
    settings4 = VideoSettings(
        video_codec="hevc_nvenc_ll",
        crf=20,  # QP 20
        container="mp4"
    )
    cmd4 = build_ffmpeg_commands("input.mp4", "output4.mp4", settings4)
    print(f"명령어: {' '.join(cmd4[0])}")
    print(f"QP 파라미터 포함: {'-qp' in cmd4[0]}")
    print()
    
    # CPU 코덱 비교 (CRF 사용)
    print("5. H.264 CPU (CRF 사용):")
    settings5 = VideoSettings(
        video_codec="libx264",
        crf=18,
        container="mp4"
    )
    cmd5 = build_ffmpeg_commands("input.mp4", "output5.mp4", settings5)
    print(f"명령어: {' '.join(cmd5[0])}")
    print(f"CRF 파라미터 포함: {'-crf' in cmd5[0]}")
    print()

if __name__ == "__main__":
    test_qp_settings()
