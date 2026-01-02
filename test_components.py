#!/usr/bin/env python3
"""
Comprehensive test of audiometer components
Tests all components that are used when START TEST is clicked
"""

import sys
import traceback

print("=" * 70)
print("PC AUDIOMETER COMPONENT TEST")
print("=" * 70)

test_results = []

def test(name, func):
    """Run a test and record result"""
    print(f"\n[TEST] {name}...", end=" ")
    try:
        func()
        print("✓ PASS")
        test_results.append((name, "PASS"))
    except Exception as e:
        print(f"✗ FAIL: {e}")
        traceback.print_exc()
        test_results.append((name, f"FAIL: {e}"))

# Test 1: Import sounddevice
def test_sounddevice():
    import sounddevice as sd
    devices = sd.query_devices()
    assert len(devices) > 0, "No audio devices found"

test("Import sounddevice", test_sounddevice)

# Test 2: List audio devices
def test_audio_devices():
    import sounddevice as sd
    devices = sd.query_devices()
    output_devices = [d for d in devices if d['max_output_channels'] > 0]
    assert len(output_devices) > 0, "No output devices found"
    print(f"\n        Found {len(output_devices)} output devices")

test("List audio devices", test_audio_devices)

# Test 3: Import controller
def test_controller_import():
    from audiometer.controller import Controller, config
    assert Controller is not None
    assert config is not None

test("Import controller", test_controller_import)

# Test 4: Initialize config with empty args
def test_config_init():
    from audiometer.controller import config
    cfg = config(args=[])
    assert cfg is not None
    assert hasattr(cfg, 'device')
    assert hasattr(cfg, 'freqs')

test("Initialize config with empty args", test_config_init)

# Test 5: Initialize Controller with device_id=None
def test_controller_init_none():
    from audiometer.controller import Controller
    ctrl = Controller(device_id=None)
    assert ctrl is not None
    assert ctrl.config is not None
    # Clean up to free audio resources
    try:
        if hasattr(ctrl, '__exit__'):
            ctrl.__exit__()
    except Exception:
        pass

test("Initialize Controller(device_id=None)", test_controller_init_none)

# Test 6: Initialize Controller with specific device
def test_controller_init_device():
    import sounddevice as sd
    from audiometer.controller import Controller
    devices = sd.query_devices()
    output_devices = [i for i, d in enumerate(devices) if d['max_output_channels'] > 0]
    if output_devices:
        device_id = output_devices[0]
        ctrl = Controller(device_id=device_id)
        assert ctrl.config.device == device_id
        print(f"\n        Using device {device_id}")
        try:
            if hasattr(ctrl, '__exit__'):
                ctrl.__exit__()
        except Exception:
            pass

test("Initialize Controller with specific device", test_controller_init_device)

# Test 7: Import ascending method
def test_ascending_import():
    from ascending_method import AscendingMethod
    assert AscendingMethod is not None

test("Import AscendingMethod", test_ascending_import)

# Test 8: Initialize AscendingMethod with device_id=None
def test_ascending_init_none():
    from ascending_method import AscendingMethod
    test = AscendingMethod(device_id=None)
    assert test is not None
    assert test.ctrl is not None
    # Clean up to free audio resources
    try:
        if hasattr(test, 'ctrl') and hasattr(test.ctrl, '__exit__'):
            test.ctrl.__exit__()
    except Exception:
        pass

test("Initialize AscendingMethod(device_id=None)", test_ascending_init_none)

# Test 9: Initialize AscendingMethod with specific device
def test_ascending_init_device():
    import sounddevice as sd
    from ascending_method import AscendingMethod
    devices = sd.query_devices()
    output_devices = [i for i, d in enumerate(devices) if d['max_output_channels'] > 0]
    if output_devices:
        device_id = output_devices[0]
        test = AscendingMethod(device_id=device_id)
        assert test.ctrl.config.device == device_id
        print(f"\n        Using device {device_id}")
        try:
            if hasattr(test, 'ctrl') and hasattr(test.ctrl, '__exit__'):
                test.ctrl.__exit__()
        except Exception:
            pass

test("Initialize AscendingMethod with specific device", test_ascending_init_device)

# Test 10: Test tone_generator
def test_tone_generator():
    from audiometer.tone_generator import AudioStream
    audio = AudioStream(device=None, attack=30, release=40)
    assert audio is not None
    # Close the audio stream to release the device
    try:
        audio.close()
    except Exception:
        pass

test("Initialize AudioStream", test_tone_generator)

# Test 11: Test responder
def test_responder():
    from audiometer.responder import Responder
    rpd = Responder(tone_duration=2)
    assert rpd is not None

test("Initialize Responder", test_responder)

# Test 12: Test PySimpleGUI import
def test_pysimplegui():
    import PySimpleGUI as sg
    assert sg is not None

test("Import PySimpleGUI", test_pysimplegui)

if __name__ == '__main__':
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in test_results if result == "PASS")
    failed = len(test_results) - passed

    for name, result in test_results:
        status = "✓" if result == "PASS" else "✗"
        print(f"{status} {name}: {result}")

    print(f"\nTotal: {passed} passed, {failed} failed out of {len(test_results)}")
    print("=" * 70)

    if failed == 0:
        print("\n✓ All components initialized successfully!")
        print("The application should work. If it still exits on START TEST,")
        print("run: python main_ui.py  and watch the console output for errors.")
        sys.exit(0)
    else:
        print(f"\n✗ {failed} component(s) failed initialization")
        sys.exit(1)
