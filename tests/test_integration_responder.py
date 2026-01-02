"""Integration test: AscendingMethod with mocked Controller and keyboard.

This test injects a fake 'keyboard' module into sys.modules so the real
Responder registers handlers, patches the Controller used by
AscendingMethod to a lightweight FakeController (avoiding filesystem and
real audio), and runs a single-frequency test to verify ear switching,
progress updates, and that Responder successfully registered handlers.
"""

import unittest
from unittest.mock import patch
import threading
from types import SimpleNamespace

# Add parent directory to path for imports (pytest may handle this, but be explicit)
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audiometer.ascending_method import AscendingMethod
from audiometer import responder


class FakeAudio:
    def __init__(self):
        self._target_gain = 0
    def start(self, freq, gain, earside):
        self._target_gain = gain
    def stop(self):
        self._target_gain = 0
    def close(self):
        pass


class FakeController:
    def __init__(self, device_id=None, subject_name=None):
        # Minimal config with one frequency and both ears
        self.config = SimpleNamespace(
            freqs=[1000],
            earsides=['right', 'left'],
            tone_duration=0.01,
            pause_time=[0, 0],
            filename='result_test.csv',
            results_path='audiometer/results/',
            carry_on=None,
            attack=30,
            release=40,
            tolerance=1.5,
            masking='off',
            conduction='air'
        )
        self._audio = FakeAudio()
        # Create a real Responder (it will pick up a mocked keyboard from sys.modules)
        self._rpd = responder.Responder(self.config.tone_duration)
        self.save_calls = []
        self.stop_event = threading.Event()

    def _progress_sleep(self, t, stop_event=None):
        # Don't actually sleep in tests
        return True

    def save_results(self, level, freq, earside):
        self.save_calls.append((level, freq, earside))


class TestIntegrationResponder(unittest.TestCase):
    def test_ascending_method_with_mocked_keyboard(self):
        # Prepare a mock keyboard module exposing on_press_key/on_release_key
        called = {'press': False, 'release': False}

        def on_press_key(name, cb, suppress=True):
            called['press'] = True
            return f"press_{name}"

        def on_release_key(name, cb, suppress=True):
            called['release'] = True
            return f"release_{name}"

        mock_keyboard = SimpleNamespace(
            on_press_key=on_press_key,
            on_release_key=on_release_key,
            unhook=lambda h: None
        )

        with patch.dict('sys.modules', {'keyboard': mock_keyboard}):
            # Patch the Controller used by AscendingMethod to our FakeController
            with patch('audiometer.ascending_method.controller.Controller', new=FakeController):
                # Track ear change and progress callbacks
                ear_events = []
                progress_events = []

                def ear_cb(ear):
                    ear_events.append(ear)

                def progress_cb(pct):
                    progress_events.append(pct)

                # Create AscendingMethod and monkeypatch hearing_test to be fast
                am = AscendingMethod(progress_callback=progress_cb, ear_change_callback=ear_cb)

                # Replace hearing_test with a simple function that sets current_level
                def quick_test():
                    am.current_level = 20

                am.hearing_test = quick_test

                # Run the method (should iterate right then left for single freq)
                am.run()

                # Ensure responder registered handlers from mocked keyboard
                rpd = am.ctrl._rpd
                self.assertTrue(len(rpd._handlers) > 0 or (called['press'] and called['release']))

                # Ensure save_results was called for both ears
                self.assertEqual(len(am.ctrl.save_calls), 2)
                ears = [call[2] for call in am.ctrl.save_calls]
                self.assertIn('right', ears)
                self.assertIn('left', ears)

                # Ear events should reflect ear changes (ordering may vary due to shuffle)
                self.assertGreaterEqual(len(ear_events), 1)

                # Progress callback should have been invoked
                self.assertGreaterEqual(len(progress_events), 1)


if __name__ == '__main__':
    unittest.main()
