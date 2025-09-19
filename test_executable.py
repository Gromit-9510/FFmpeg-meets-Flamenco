#!/usr/bin/env python3
"""
Test script to verify the executable works correctly.
"""

import subprocess
import sys
import time
from pathlib import Path

def test_executable():
    """Test the executable by running it briefly."""
    exe_path = Path("dist/FFmpegEncoder.exe")
    
    if not exe_path.exists():
        print("❌ Executable not found!")
        return False
    
    print(f"✅ Found executable: {exe_path}")
    print(f"   Size: {exe_path.stat().st_size / (1024*1024):.1f} MB")
    
    print("\n🚀 Testing executable startup...")
    
    try:
        # Start the executable
        process = subprocess.Popen(
            [str(exe_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Let it run for a few seconds
        time.sleep(3)
        
        # Check if it's still running (good sign)
        if process.poll() is None:
            print("✅ Executable started successfully and is running!")
            
            # Terminate it gracefully
            process.terminate()
            process.wait(timeout=5)
            print("✅ Executable terminated gracefully")
            return True
        else:
            # Process ended, check for errors
            stdout, stderr = process.communicate()
            print(f"❌ Executable exited with code: {process.returncode}")
            if stderr:
                print(f"   Error: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to test executable: {e}")
        return False

def main():
    """Run the test."""
    print("FFmpeg Encoder - Executable Test")
    print("=" * 40)
    
    success = test_executable()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 Executable test PASSED!")
        print("   Your FFmpeg Encoder is ready to use!")
    else:
        print("❌ Executable test FAILED!")
        print("   Check the errors above.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
