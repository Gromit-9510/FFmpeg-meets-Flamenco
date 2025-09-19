#!/usr/bin/env python3
"""
Demo script showing how to use FFmpeg Encoder programmatically.
"""

from ffmpeg_encoder.core.ffmpeg_cmd import VideoSettings, build_ffmpeg_commands
from ffmpeg_encoder.core.presets import Preset, PresetStore
from ffmpeg_encoder.core.batch_rename import apply_pattern_rename, apply_find_replace
from ffmpeg_encoder.integrations.flamenco_client import FlamencoClient, FlamencoConfig
from pathlib import Path

def demo_ffmpeg_commands():
    """Demonstrate FFmpeg command building."""
    print("=== FFmpeg Command Building Demo ===")
    
    # Create settings
    settings = VideoSettings(
        container="mp4",
        video_codec="libx264",
        crf=18,
        bitrate="8M",
        two_pass=False,
        gpu_enable=True,
        audio_codec="aac",
        audio_bitrate="192k",
        max_filesize="700M",
        extra_params="-preset slow -tune film"
    )
    
    # Build commands
    input_path = "input.mov"
    output_path = "output.mp4"
    commands = build_ffmpeg_commands(input_path, output_path, settings)
    
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"Commands to run:")
    for i, cmd in enumerate(commands, 1):
        print(f"  {i}. {' '.join(cmd)}")

def demo_presets():
    """Demonstrate preset management."""
    print("\n=== Preset Management Demo ===")
    
    # Create preset store
    preset_dir = Path.home() / ".ffmpeg_encoder" / "presets"
    preset_dir.mkdir(parents=True, exist_ok=True)
    store = PresetStore(preset_dir)
    
    # Create a preset
    preset = Preset(
        name="high_quality_h264",
        container="mp4",
        video_codec="libx264",
        crf=18,
        bitrate="10M",
        two_pass=True,
        gpu_enable=False,
        audio_codec="aac",
        audio_bitrate="256k",
        max_filesize="1G",
        additional_params="-preset slow -tune film"
    )
    
    # Save preset
    store.save(preset)
    print(f"Saved preset: {preset.name}")
    
    # List presets
    presets = store.list_presets()
    print(f"Available presets: {presets}")
    
    # Load preset
    loaded = store.load(preset.name)
    print(f"Loaded preset: {loaded.name}")

def demo_batch_rename():
    """Demonstrate batch renaming."""
    print("\n=== Batch Rename Demo ===")
    
    # Sample files
    files = [
        "video1.mov",
        "video2.mov", 
        "video3.mov",
        "old_name.mp4"
    ]
    
    # Pattern-based renaming
    pattern_renames = apply_pattern_rename(files, "episode_{n:03d}.mp4")
    print("Pattern renaming (episode_{n:03d}.mp4):")
    for old, new in pattern_renames:
        print(f"  {old} -> {new}")
    
    # Find/replace renaming
    find_replace_renames = apply_find_replace(files, "video", "episode", use_regex=False)
    print("\nFind/replace renaming (video -> episode):")
    for old, new in find_replace_renames:
        print(f"  {old} -> {new}")

def demo_flamenco():
    """Demonstrate Flamenco integration."""
    print("\n=== Flamenco Integration Demo ===")
    
    # Note: This is just a demo - you'd need a real Flamenco server
    config = FlamencoConfig(
        base_url="http://localhost:8080",
        token="your-api-token-here"
    )
    
    client = FlamencoClient(config)
    print(f"Flamenco client configured for: {config.base_url}")
    print("Note: This is a demo - configure with real Flamenco server details")

def main():
    """Run all demos."""
    print("FFmpeg Encoder - Programmatic Usage Demo")
    print("=" * 50)
    
    demo_ffmpeg_commands()
    demo_presets()
    demo_batch_rename()
    demo_flamenco()
    
    print("\n" + "=" * 50)
    print("Demo complete! The GUI application should be running.")
    print("Try adding some video files and testing the features!")

if __name__ == "__main__":
    main()
