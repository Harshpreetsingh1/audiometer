#!/usr/bin/env python3
"""
Debug script for GUI startup issues
Runs the UI with detailed logging to identify where app exits
"""

import sys
import logging
import PySimpleGUI as sg
import sounddevice as sd
import threading

# Enable detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug_gui.log", 'w'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def test_imports():
    """Test that all required modules can be imported"""
    logger.info("Testing imports...")
    try:
        from ascending_method import AscendingMethod
        logger.info("✓ AscendingMethod imported successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to import AscendingMethod: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_audio_devices():
    """Test that audio devices can be queried"""
    logger.info("Testing audio device query...")
    try:
        devices = sd.query_devices()
        logger.info(f"✓ Found {len(devices)} audio devices")
        for i, d in enumerate(devices):
            if d['max_output_channels'] > 0:
                logger.info(f"  Device {i}: {d['name']}")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to query audio devices: {e}")
        return False

def main():
    logger.info("=== PC AUDIOMETER DEBUG GUI ===")
    logger.info("Starting GUI debug process...")
    
    # Test imports first
    if not test_imports():
        logger.error("Import test failed. Exiting.")
        return
    
    # Test audio devices
    if not test_audio_devices():
        logger.warning("Audio device test failed, but continuing...")
    
    logger.info("All pre-flight checks passed. Starting GUI...")
    
    sg.theme('DarkBlue3')
    sg.set_options(font=("Helvetica", 11))
    
    # Simple test layout
    layout = [
        [sg.Text("PC AUDIOMETER DEBUG", font=("Helvetica", 24, "bold"))],
        [sg.Text("Testing GUI startup...", key='-STATUS-')],
        [sg.Button("START TEST", key='-START-'), sg.Button("EXIT", key='-EXIT-')],
        [sg.Multiline(size=(80, 20), key='-OUTPUT-', disabled=True)],
    ]
    
    logger.info("Creating window...")
    try:
        window = sg.Window("PC Audiometer Debug", layout)
        logger.info("✓ Window created successfully")
    except Exception as e:
        logger.error(f"✗ Failed to create window: {e}")
        import traceback
        traceback.print_exc()
        return
    
    output_text = "GUI initialized successfully\n"
    window['-OUTPUT-'].update(output_text)
    
    logger.info("Starting event loop...")
    while True:
        try:
            event, values = window.read(timeout=100)
            logger.debug(f"Event: {event}")
            
            if event == sg.WINDOW_CLOSED or event == '-EXIT-':
                logger.info("Window closed by user")
                break
            
            if event is None:
                continue
            
            if event == '-START-':
                logger.info("START TEST button pressed")
                output_text += "START TEST clicked\n"
                window['-OUTPUT-'].update(output_text)
                
                # Try to initialize AscendingMethod
                try:
                    logger.info("Attempting to create AscendingMethod...")
                    from ascending_method import AscendingMethod
                    test = AscendingMethod(device_id=None)
                    logger.info("✓ AscendingMethod created successfully")
                    output_text += "✓ AscendingMethod created\n"
                except Exception as e:
                    logger.error(f"✗ Failed to create AscendingMethod: {e}")
                    import traceback
                    traceback.print_exc()
                    output_text += f"✗ Error: {e}\n"
                
                window['-OUTPUT-'].update(output_text)
        
        except Exception as e:
            logger.error(f"Error in event loop: {e}")
            import traceback
            traceback.print_exc()
            break
    
    logger.info("Closing window...")
    window.close()
    logger.info("=== DEBUG SESSION COMPLETE ===")

if __name__ == '__main__':
    main()
