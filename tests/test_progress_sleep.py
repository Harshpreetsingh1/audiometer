import os
import sys
import time

# Make repo importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from audiometer.controller import Controller


class DummyWindow:
    def __init__(self):
        self.events = []

    def write_event_value(self, key, value):
        # Record any events written by the controller
        self.events.append((key, value))


def test_progress_sleep_does_not_emit_progress_events():
    c = Controller()
    c.ui_window = DummyWindow()
    # Provide a context for total_steps/step_idx that would have produced
    # intermediate updates previously
    c.total_steps = 4
    c.step_idx = 1

    # Call with a short duration
    c._progress_sleep(0.2)

    # No '-PROGRESS-' events should have been emitted during the tone
    assert all(evt[0] != '-PROGRESS-' for evt in c.ui_window.events)
