#!/usr/bin/env python3
"""
Minimal test to reproduce the GUI exit issue
"""

import sys
import PySimpleGUI as sg
import threading
from ascending_method import AscendingMethod

current_test = None
is_running = False
test_lock = threading.Lock()

def run_test_thread(device_id, window):
    global current_test, is_running
    is_running = True
    try:
        print(f"[Thread] Creating AscendingMethod with device_id={device_id}")
        test = AscendingMethod(device_id=device_id)
        with test_lock:
            current_test = test
        print("[Thread] AscendingMethod created, signaling started")
        window.write_event_value('-TEST_STARTED-', '')
        print("[Thread] About to call test.run()")
        test.run()
        print("[Thread] test.run() completed, signaling finished")
        window.write_event_value('-TEST_FINISHED-', '')
    except Exception as e:
        print(f"[Thread] ERROR: {e}")
        import traceback
        traceback.print_exc()
        window.write_event_value('-TEST_ERROR-', str(e))
    finally:
        is_running = False
        with test_lock:
            current_test = None
        print("[Thread] Thread cleanup complete")

def main():
    sg.theme('DarkBlue3')
    
    layout = [
        [sg.Text("Minimal GUI Test", font=("Helvetica", 24, "bold"))],
        [sg.Button("START TEST", key='-START-'), sg.Button("EXIT", key='-EXIT-')],
        [sg.Multiline(size=(80, 20), key='-OUTPUT-', disabled=True)],
    ]
    
    print("[Main] Creating window...")
    window = sg.Window("Minimal Test", layout)
    print("[Main] Window created")
    
    output = "Window initialized\n"
    window['-OUTPUT-'].update(output)
    
    print("[Main] Starting event loop...")
    while True:
        try:
            print("[Main] Calling window.read()...")
            event, values = window.read(timeout=100)
            print(f"[Main] Got event: {event}")
            
            if event == sg.WINDOW_CLOSED or event == '-EXIT-':
                print("[Main] Window closed, exiting")
                break
            
            if event is None:
                print("[Main] Timeout event, continuing...")
                continue
            
            if event == '-START-':
                print("[Main] START TEST clicked")
                output += "START TEST clicked\n"
                window['-OUTPUT-'].update(output)
                
                print("[Main] Starting test thread...")
                test_thread = threading.Thread(
                    target=run_test_thread,
                    args=(None, window),
                    daemon=True
                )
                test_thread.start()
                print("[Main] Test thread started")
                
        except Exception as e:
            print(f"[Main] Exception in event loop: {e}")
            import traceback
            traceback.print_exc()
            break
    
    print("[Main] Closing window...")
    window.close()
    print("[Main] Main complete")

if __name__ == '__main__':
    main()
