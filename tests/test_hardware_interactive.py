#!/usr/bin/env python3
"""Interactive hardware verification tests for audiometer.

This script performs manual hardware checks that cannot be automated:
- Audio channel separation (LEFT/RIGHT ear isolation)
- USB headset button input latency and detection

Run this script to verify your hardware setup before running actual hearing tests.
"""

import sys
import os
import time
import sounddevice as sd
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from audiometer import tone_generator
from audiometer import responder


def print_header(title):
    """Print a formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def print_debug_checklist():
    """Print debugging checklist for audio issues."""
    print("\n" + "-"*70)
    print("DEBUG CHECKLIST:")
    print("-"*70)
    print("1. Check USB headphone connection:")
    print("   - Ensure USB cable is firmly connected")
    print("   - Try unplugging and reconnecting")
    print("   - Check if device appears in system audio settings")
    print()
    print("2. Check system audio settings:")
    print("   - Verify USB headphones are set as default output device")
    print("   - Check system volume is not muted")
    print("   - Ensure USB device is not disabled in device manager")
    print()
    print("3. Check audio device selection:")
    print("   - Run: python -c \"import sounddevice as sd; print(sd.query_devices())\"")
    print("   - Verify your USB device appears in the list")
    print("   - Note the device ID and use it in the main application")
    print()
    print("4. Check headphone hardware:")
    print("   - Test headphones with another device (phone, music player)")
    print("   - Verify both earcups produce sound")
    print("   - Check for physical damage to cables or earcups")
    print("-"*70 + "\n")


def test_audio_channel_separation():
    """Test that audio plays only in the specified ear (LEFT or RIGHT)."""
    print_header("AUDIO CHANNEL SEPARATION TEST")
    
    print("This test verifies that audio is properly isolated to each ear.")
    print("You should hear tones ONLY in the specified ear, with NO sound in the other ear.\n")
    
    # Get audio device
    print("Available audio devices:")
    devices = sd.query_devices()
    output_devices = []
    for i, d in enumerate(devices):
        if d['max_output_channels'] > 0:
            print(f"  [{i}] {d['name']} ({d['max_output_channels']} channels)")
            output_devices.append(i)
    
    if not output_devices:
        print("\nERROR: No audio output devices found!")
        print_debug_checklist()
        return False
    
    device_id = None
    while device_id is None:
        try:
            user_input = input(f"\nEnter device ID to test (0-{len(devices)-1}) or 'q' to quit: ").strip()
            if user_input.lower() == 'q':
                return False
            device_id = int(user_input)
            if device_id not in output_devices:
                print(f"ERROR: Device {device_id} is not an output device. Try again.")
                device_id = None
        except ValueError:
            print("ERROR: Please enter a valid number.")
            device_id = None
    
    # Initialize audio stream
    try:
        audio = tone_generator.AudioStream(device=device_id, attack=30, release=40)
        print("\n✓ Audio stream initialized successfully")
    except Exception as e:
        print(f"\n✗ ERROR initializing audio: {e}")
        print_debug_checklist()
        return False
    
    # Test LEFT channel
    print("\n" + "-"*70)
    print("TEST 1: LEFT CHANNEL ONLY")
    print("-"*70)
    print("Playing a 1000 Hz tone in the LEFT ear only...")
    print("You should hear this ONLY in your LEFT ear.")
    print("Press ENTER when ready to play the tone...")
    input()
    
    try:
        # Play tone in LEFT ear (channel 0)
        audio.start(1000, -20, 'left')  # 1000 Hz, -20 dBFS, left ear
        print("Playing... (2 seconds)")
        time.sleep(2)
        audio.stop()
        print("Tone stopped.\n")
    except Exception as e:
        print(f"ERROR playing tone: {e}")
        audio.close()
        return False
    
    left_response = None
    while left_response not in ['y', 'n', 'yes', 'no']:
        left_response = input("Did you hear this tone ONLY in your LEFT ear? (y/n): ").strip().lower()
    
    if left_response in ['n', 'no']:
        print("\n✗ LEFT CHANNEL TEST FAILED")
        print("You should have heard the tone ONLY in the left ear.")
        print_debug_checklist()
        audio.close()
        return False
    else:
        print("✓ LEFT channel test PASSED\n")
    
    # Test RIGHT channel
    print("-"*70)
    print("TEST 2: RIGHT CHANNEL ONLY")
    print("-"*70)
    print("Playing a 1000 Hz tone in the RIGHT ear only...")
    print("You should hear this ONLY in your RIGHT ear.")
    print("Press ENTER when ready to play the tone...")
    input()
    
    try:
        # Play tone in RIGHT ear (channel 1)
        audio.start(1000, -20, 'right')  # 1000 Hz, -20 dBFS, right ear
        print("Playing... (2 seconds)")
        time.sleep(2)
        audio.stop()
        print("Tone stopped.\n")
    except Exception as e:
        print(f"ERROR playing tone: {e}")
        audio.close()
        return False
    
    right_response = None
    while right_response not in ['y', 'n', 'yes', 'no']:
        right_response = input("Did you hear this tone ONLY in your RIGHT ear? (y/n): ").strip().lower()
    
    if right_response in ['n', 'no']:
        print("\n✗ RIGHT CHANNEL TEST FAILED")
        print("You should have heard the tone ONLY in the right ear.")
        print_debug_checklist()
        audio.close()
        return False
    else:
        print("✓ RIGHT channel test PASSED\n")
    
    audio.close()
    print("="*70)
    print("✓ AUDIO CHANNEL SEPARATION: ALL TESTS PASSED")
    print("="*70)
    return True


def test_input_latency():
    """Test USB headset button input latency and detection."""
    print_header("USB HEADSET BUTTON INPUT TEST")
    
    print("This test measures the latency between button press and detection.")
    print("You will press your USB headset 'Volume Up' or 'Volume Down' button,")
    print("and we will measure how quickly the system detects it.\n")
    
    # Initialize responder
    try:
        rpd = responder.Responder(tone_duration=2.0)
        print("✓ Responder initialized successfully")
        print("✓ Media key handlers registered\n")
    except Exception as e:
        print(f"✗ ERROR initializing responder: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure 'keyboard' library is installed: pip install keyboard")
        print("2. On Linux, you may need to run with sudo for media key access")
        print("3. Check that your USB headset buttons are recognized by the OS\n")
        return False
    
    # Test Volume Up button
    print("-"*70)
    print("TEST 1: VOLUME UP BUTTON")
    print("-"*70)
    print("When prompted, press your USB headset 'Volume Up' button.")
    print("We will measure the time from prompt to detection.\n")
    
    input("Press ENTER when ready, then IMMEDIATELY press 'Volume Up' button...")
    
    start_time = time.time()
    print("\n⏱️  TIMING STARTED - Press 'Volume Up' button NOW!")
    print("(Waiting up to 5 seconds for button press...)\n")
    
    # Wait for button press with timeout
    button_detected = False
    timeout = 5.0
    elapsed = 0.0
    check_interval = 0.01  # Check every 10ms
    
    while elapsed < timeout:
        if rpd.click_down():
            button_detected = True
            break
        time.sleep(check_interval)
        elapsed = time.time() - start_time
    
    if button_detected:
        latency = time.time() - start_time
        print(f"✓ BUTTON DETECTED!")
        print(f"  Latency: {latency*1000:.2f} ms")
        if latency < 0.1:
            print("  Status: EXCELLENT (< 100ms)")
        elif latency < 0.2:
            print("  Status: GOOD (< 200ms)")
        else:
            print("  Status: ACCEPTABLE (but may affect test accuracy)")
    else:
        print("✗ BUTTON NOT DETECTED within 5 seconds")
        print("\nTroubleshooting:")
        print("1. Ensure USB headset is connected and recognized")
        print("2. Try pressing the button multiple times")
        print("3. Check if buttons work in other applications (e.g., media player)")
        print("4. On Windows, check Device Manager for USB audio device")
        print("5. Try the 'Volume Down' button instead\n")
        rpd.clear()
        rpd.close()
        return False
    
    # Clear state and wait for release
    rpd.clear()
    time.sleep(0.5)
    
    # Test Volume Down button
    print("\n" + "-"*70)
    print("TEST 2: VOLUME DOWN BUTTON")
    print("-"*70)
    print("When prompted, press your USB headset 'Volume Down' button.")
    print("We will verify that BOTH buttons trigger the same response.\n")
    
    input("Press ENTER when ready, then IMMEDIATELY press 'Volume Down' button...")
    
    start_time = time.time()
    print("\n⏱️  TIMING STARTED - Press 'Volume Down' button NOW!")
    print("(Waiting up to 5 seconds for button press...)\n")
    
    button_detected = False
    elapsed = 0.0
    
    while elapsed < timeout:
        if rpd.click_down():
            button_detected = True
            break
        time.sleep(check_interval)
        elapsed = time.time() - start_time
    
    if button_detected:
        latency = time.time() - start_time
        print(f"✓ BUTTON DETECTED!")
        print(f"  Latency: {latency*1000:.2f} ms")
        print("  Status: Both Volume Up and Volume Down buttons work correctly")
    else:
        print("✗ BUTTON NOT DETECTED within 5 seconds")
        rpd.clear()
        rpd.close()
        return False
    
    rpd.clear()
    rpd.close()
    
    print("\n" + "="*70)
    print("✓ USB HEADSET BUTTON INPUT: ALL TESTS PASSED")
    print("="*70)
    return True


def main():
    """Run all interactive hardware tests."""
    print("\n" + "="*70)
    print("  AUDIOMETER HARDWARE VERIFICATION SUITE")
    print("="*70)
    print("\nThis script will guide you through manual hardware verification.")
    print("These tests require human interaction and cannot be fully automated.\n")
    
    input("Press ENTER to begin...")
    
    results = {
        'audio_channels': False,
        'input_latency': False
    }
    
    # Test 1: Audio channel separation
    try:
        results['audio_channels'] = test_audio_channel_separation()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        return
    except Exception as e:
        print(f"\n✗ ERROR during audio channel test: {e}")
        import traceback
        traceback.print_exc()
    
    if not results['audio_channels']:
        print("\n⚠️  Audio channel test failed. Please fix issues before proceeding.")
        response = input("Continue with input latency test anyway? (y/n): ").strip().lower()
        if response not in ['y', 'yes']:
            return
    
    # Test 2: Input latency
    try:
        results['input_latency'] = test_input_latency()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        return
    except Exception as e:
        print(f"\n✗ ERROR during input latency test: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)
    print(f"Audio Channel Separation: {'✓ PASSED' if results['audio_channels'] else '✗ FAILED'}")
    print(f"USB Button Input Latency:  {'✓ PASSED' if results['input_latency'] else '✗ FAILED'}")
    print("="*70)
    
    if all(results.values()):
        print("\n🎉 ALL HARDWARE TESTS PASSED!")
        print("Your hardware is ready for hearing tests.\n")
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("Please fix the issues above before running hearing tests.\n")


if __name__ == '__main__':
    main()


