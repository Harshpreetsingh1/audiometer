#!/usr/bin/env python3
"""
Diagnoses the sounddevice/PortAudio backend to check for device enumeration issues.

This script helps identify common problems, such as:
- No audio devices being found due to OS privacy settings.
- Errors in the underlying audio driver or PortAudio installation.
"""

import sounddevice as sd
import sys

def check_audio_backend():
    """Queries the audio backend and prints diagnostic information."""
    print("--- Audio Backend Diagnostic ---")
    
    try:
        version_info = sd.get_portaudio_version()
        print(f"PortAudio Version: {version_info}")
    except Exception as e:
        print(f"ERROR: Could not get PortAudio version: {e}")
        
    print("\nQuerying for audio devices...")
    try:
        devices = sd.query_devices()
        if not devices:
            print("\nCRITICAL: No audio devices found.")
            print("This is often caused by OS privacy settings.")
            if sys.platform == 'win32':
                print("\nOn Windows, please check:")
                print("  Settings > Privacy & security > Microphone")
                print("  And ensure 'Let desktop apps access your microphone' is ON.")
            elif sys.platform == 'darwin':
                print("\nOn macOS, please check:")
                print("  System Settings > Privacy & Security > Microphone")
                print("  And ensure the application or terminal has permission.")
        else:
            print(f"\nSUCCESS: Found {len(devices)} devices.")
            print("-" * 30)
            print(devices)
            print("-" * 30)

    except Exception as e:
        print(f"\nCRITICAL ERROR during device query: {e}")
        print("This may indicate a driver or system-level audio issue.")

if __name__ == "__main__":
    check_audio_backend()