import sys
import traceback

print("--- DIAGNOSTIC START ---")
try:
    import sounddevice as sd
    print(f"SoundDevice Version: {sd.__version__}")
    try:
        print(f"PortAudio Version: {sd.get_portaudio_version()}")
    except Exception:
        print("WARNING: Could not get PortAudio version.")
        
    print("\nAttempting to query devices...")
    devices = sd.query_devices()
    print(f"Found {len(devices)} devices.")
    print(devices)
    
except ImportError:
    print("CRITICAL: 'sounddevice' module not found. Run 'pip install sounddevice'.")
except Exception as e:
    print("\n!!! CRITICAL AUDIO ERROR !!!")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {e}")
    print("\nTraceback:")
    traceback.print_exc()
    
    print("\n--- TROUBLESHOOTING ---")
    print("1. WINDOWS PRIVACY: Go to Settings > Privacy > Microphone.")
    print("   Ensure 'Allow desktop apps to access your microphone' is ON.")
    print("2. DRIVERS: Ensure your headphones are plugged in.")

print("\n--- DIAGNOSTIC END ---")
input("Press Enter to close...")