import unittest
import time
from unittest.mock import patch

import sounddevice as sd
from audiometer import main_ui


class FakeAscendingMethod:
    last_instance = None

    def __init__(self, device_id=None, subject_name=None, progress_callback=None, ear_change_callback=None, freq_change_callback=None, quick_mode=False, mini_mode=False):
        # Record the parameters for assertions
        self.device_id = device_id
        self.subject_name = subject_name
        self.progress_callback = progress_callback
        self.ear_change_callback = ear_change_callback
        self.freq_change_callback = freq_change_callback
        self.quick_mode = quick_mode
        self.mini_mode = mini_mode
        # Simulate controller config for quick-mode and mini-mode behavior
        if mini_mode:
            self.ctrl = type('C', (), {'config': type('Cfg', (), {'freqs': [1000, 4000]})()})()
        elif quick_mode:
            self.ctrl = type('C', (), {'config': type('Cfg', (), {'freqs': [1000, 2000, 4000, 500]})()})()
        else:
            self.ctrl = type('C', (), {'config': type('Cfg', (), {'freqs': [125, 250, 500, 1000]})()})()
        FakeAscendingMethod.last_instance = self

    def run(self):
        # Do nothing - allow thread to finish quickly
        return

    def stop_test(self):
        return


class TestUIQuickModeIntegration(unittest.TestCase):
    def setUp(self):
        # Patch sounddevice.query_devices to avoid needing real hardware
        self.patcher_sd = patch('sounddevice.query_devices', return_value={'max_output_channels': 2, 'name': 'Fake USB Device'})
        self.mock_sd = self.patcher_sd.start()

        # Patch AscendingMethod in the main_ui module
        self.patcher_am = patch('audiometer.main_ui.AscendingMethod', new=FakeAscendingMethod)
        self.mock_am = self.patcher_am.start()

        # Instantiate the UI (do not call mainloop)
        self.app = main_ui.AudiometerUI()

        # Provide valid form values to pass input validation
        self.app.device_var.set('0: Fake USB Device')
        self.app.id_entry.delete(0, 'end')
        self.app.id_entry.insert(0, 'TEST123')
        self.app.name_entry.delete(0, 'end')
        self.app.name_entry.insert(0, 'Test Subject')

    def tearDown(self):
        # Destroy the UI and stop patchers
        try:
            self.app.destroy()
        except Exception:
            pass
        self.patcher_am.stop()
        self.patcher_sd.stop()

    def test_start_test_passes_quick_mode_true(self):
        # Enable quick mode in the UI
        self.app.quick_mode_var.set(True)
        self.app.mini_mode_var.set(False)

        # Simulate user clicking the Start button (preferred over calling private method)
        try:
            self.app.start_button.invoke()
        except Exception:
            # Fall back to direct call if widget invocation is not available
            self.app._start_test()

        # Poll for the AscendingMethod instance with backoff to avoid flakiness
        timeout = time.time() + 5.0
        delay = 0.005
        while FakeAscendingMethod.last_instance is None and time.time() < timeout:
            time.sleep(delay)
            # Exponential backoff with cap
            delay = min(delay * 1.5, 0.05)

        self.assertIsNotNone(FakeAscendingMethod.last_instance, "AscendingMethod was not instantiated")
        self.assertTrue(FakeAscendingMethod.last_instance.quick_mode, "Quick mode flag was not passed as True")
        self.assertFalse(FakeAscendingMethod.last_instance.mini_mode, "Mini mode flag should be False")
        self.assertEqual(FakeAscendingMethod.last_instance.ctrl.config.freqs, [1000, 2000, 4000, 500])

    def test_start_test_passes_mini_mode_true(self):
        # Enable mini (2-frequency) mode in the UI
        self.app.mini_mode_var.set(True)
        self.app.quick_mode_var.set(False)

        try:
            self.app.start_button.invoke()
        except Exception:
            self.app._start_test()

        timeout = time.time() + 5.0
        delay = 0.005
        while FakeAscendingMethod.last_instance is None and time.time() < timeout:
            time.sleep(delay)
            delay = min(delay * 1.5, 0.05)

        self.assertIsNotNone(FakeAscendingMethod.last_instance, "AscendingMethod was not instantiated")
        self.assertTrue(FakeAscendingMethod.last_instance.mini_mode, "Mini mode flag was not passed as True")
        self.assertFalse(FakeAscendingMethod.last_instance.quick_mode, "Quick mode flag should be False when mini is True")
        self.assertEqual(FakeAscendingMethod.last_instance.ctrl.config.freqs, [1000, 4000])

    def test_start_test_passes_quick_mode_false(self):
        # Disable quick mode in the UI
        self.app.quick_mode_var.set(False)

        # Start test
        self.app._start_test()

        # Wait briefly for the thread to create the AscendingMethod instance
        timeout = time.time() + 2.0
        while FakeAscendingMethod.last_instance is None and time.time() < timeout:
            time.sleep(0.01)

        self.assertIsNotNone(FakeAscendingMethod.last_instance, "AscendingMethod was not instantiated")
        self.assertFalse(FakeAscendingMethod.last_instance.quick_mode, "Quick mode flag was not passed as False")
        self.assertEqual(FakeAscendingMethod.last_instance.ctrl.config.freqs, [125, 250, 500, 1000])


if __name__ == '__main__':
    unittest.main()
