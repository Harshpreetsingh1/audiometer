"""Audio simulated smoke test for AscendingMethod

This test replaces the real Controller with a FakeController that uses a
FakeAudio stream (no sounddevice). It runs a short AscendingMethod test
and asserts that audio start/stop calls happened for each frequency/ear
combination (Quick Test defaults) and that save_results was called the
expected number of times.
"""

import unittest
from unittest.mock import patch
from types import SimpleNamespace
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audiometer.ascending_method import AscendingMethod


class FakeAudio:
    def __init__(self):
        self.start_calls = []
        self.stop_calls = 0
    def start(self, freq, gain, earside):
        self.start_calls.append((freq, gain, earside))
    def stop(self):
        self.stop_calls += 1
    def close(self):
        pass

class FakeController:
    def __init__(self, device_id=None, subject_name=None):
        # Use quick-screen frequencies to keep the test fast
        self.config = SimpleNamespace(
            freqs=[1000, 2000, 4000, 500],
            earsides=['right', 'left'],
            tone_duration=0.01,
            pause_time=[0, 0],
            filename='result_test.csv',
            results_path='audiometer/results/',
            carry_on=None,
            attack=30,
            release=40,
            tolerance=0.2,
            masking='off',
            conduction='air'
        )
        self._audio = FakeAudio()
        self._rpd = None  # not needed for this smoke test
        self.save_calls = []
        self.stop_event = type('E', (), {'is_set': lambda s: False})()

    def _progress_sleep(self, t, stop_event=None):
        # No-op sleep for fast test
        return True

    def save_results(self, level, freq, earside):
        self.save_calls.append((level, freq, earside))

    def dBHL2dBFS(self, freq_value, dBHL):
        return -1.0


class TestAudioSimulatedSmoke(unittest.TestCase):
    def test_quick_screen_runs_and_uses_fake_audio(self):
        # Patch the Controller used by AscendingMethod
        with patch('audiometer.ascending_method.controller.Controller', new=FakeController):
            # Track ear and progress callbacks
            ear_events = []
            progress_events = []

            def ear_cb(ear):
                ear_events.append(ear)

            def progress_cb(pct):
                progress_events.append(pct)

            am = AscendingMethod(progress_callback=progress_cb, ear_change_callback=ear_cb)

            # Replace hearing_test with a quick stub that sets a threshold
            def quick_test():
                am.current_level = 10

            am.hearing_test = quick_test

            # Run the test
            am.run()

            # After run, controller should have recorded save_results for each freq/ear
            ctrl = am.ctrl
            expected = len(ctrl.config.freqs) * len(ctrl.config.earsides)
            self.assertEqual(len(ctrl.save_calls), expected, "save_results should be called for each freq/ear")

            # Fake audio start calls should match expected (each tone starts once)
            self.assertEqual(len(ctrl._audio.start_calls), expected)

            # Ear events should have been fired (at least once per ear start)
            self.assertGreaterEqual(len(ear_events), 1)

            # Progress events should have happened and reach near 100 at the end
            self.assertGreaterEqual(len(progress_events), 1)
            self.assertAlmostEqual(progress_events[-1], 100.0, delta=0.01)


if __name__ == '__main__':
    unittest.main()
