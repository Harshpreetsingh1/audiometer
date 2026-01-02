import unittest
from unittest.mock import patch
from collections import Counter

from ascending_method import AscendingMethod
from audiometer import controller


class TestVerifyQuickMode(unittest.TestCase):
    def setUp(self):
        # Patch the heavy hearing_test to be instantaneous and deterministic
        self.patcher_ht = patch.object(AscendingMethod, 'hearing_test', lambda self: setattr(self, 'current_level', 10))
        self.patcher_ht.start()

        # Patch AudioStream to avoid opening real audio devices during tests
        class FakeAudioStream:
            def __init__(self, device, attack, release):
                self._target_gain = 0
                self._attack = attack
                self._release = release
                self._freq = None
                self._index = 0
                self._channel = 0
                self.channel_mask = [0.0, 0.0]
            def start(self, freq, gain_db, earside=None):
                self._freq = freq
                self._target_gain = 1.0
                if earside == 'left':
                    self._channel = 0
                else:
                    self._channel = 1
            def stop(self):
                self._target_gain = 0
            def close(self):
                pass
        self.patcher_audio = patch('audiometer.tone_generator.AudioStream', new=FakeAudioStream)
        self.patcher_audio.start()

        # Collect calls to save_results
        self.saved = []
        def fake_save(self_obj, level, freq, earside):
            # accept the bound instance and record the call
            self.saved.append((level, freq, earside))
        self.patcher_save = patch.object(controller.Controller, 'save_results', new=fake_save)
        self.patcher_save.start()

    def tearDown(self):
        self.patcher_ht.stop()
        self.patcher_save.stop()

    def test_frequency_count(self):
        # Run a full test in quick mode (4 freqs per ear => 8 saves)
        am = AscendingMethod(quick_mode=True)
        am.run()
        self.assertEqual(len(self.saved), 8, f"Expected 8 save_results calls, got {len(self.saved)}")

    def test_randomization(self):
        # Instantiate multiple times and count starting ear
        starts = []
        for _ in range(20):
            am = AscendingMethod()  # random ear order by default
            starts.append(am.ctrl.config.earsides[0])
        counts = Counter(starts)
        # Assert both ears appear as starting ear at least once
        self.assertTrue(counts['right'] > 0 and counts['left'] > 0,
                        f"Ear randomization appears deterministic: {counts}")

    def test_progress_accuracy(self):
        # Collect progress notifications
        progress_vals = []
        def progress_cb(pct):
            progress_vals.append(round(float(pct), 4))

        am = AscendingMethod(quick_mode=True, progress_callback=progress_cb)
        am.run()

        # progress values should include 12.5 (after first), 50.0 (after 4 steps), and 100.0 (final)
        self.assertIn(12.5, [round(v, 1) for v in progress_vals], f"Missing 12.5 in progress values: {progress_vals}")
        self.assertIn(50.0, [round(v, 1) for v in progress_vals], f"Missing 50.0 in progress values: {progress_vals}")
        self.assertIn(100.0, [round(v, 1) for v in progress_vals], f"Missing 100.0 in progress values: {progress_vals}")


if __name__ == '__main__':
    unittest.main()
