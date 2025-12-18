import time
import sys
import os
# Ensure repo root is in sys.path so 'audiometer' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from audiometer.controller import Controller

class DummyWindow:
    def __init__(self):
        self.events = []
    def write_event_value(self, key, value):
        print(f'Event: {key} -> {value}')
        self.events.append((key, value))

c = Controller()
c.ui_window = DummyWindow()
# Simulate a test with 4 steps, currently at step 1
c.total_steps = 4
c.step_idx = 1
print('Calling _progress_sleep(0.5)')
c._progress_sleep(0.5)
print('Events captured (should be empty):', c.ui_window.events)

# Simulate zero UI window
print('Calling _progress_sleep with no ui_window')
dc = Controller()
dc._progress_sleep(0.1)
print('Done')
