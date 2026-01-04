import unittest
import time
from unittest.mock import patch

from audiometer import main_ui


class FakeAscendingEarChanges:
    last_instance = None

    def __init__(self, device_id=None, subject_name=None, progress_callback=None, ear_change_callback=None, freq_change_callback=None, quick_mode=False):
        self.ear_change_callback = ear_change_callback
        FakeAscendingEarChanges.last_instance = self

    def run(self):
        # Simulate ear change events from test thread
        try:
            if self.ear_change_callback:
                self.ear_change_callback('right')
                time.sleep(0.05)
                self.ear_change_callback('left')
                time.sleep(0.05)
        except Exception:
            pass

    def stop_test(self):
        return


class TestUIEarIndicator(unittest.TestCase):
    def setUp(self):
        # Patch sounddevice.query_devices
        self.patcher_sd = patch('sounddevice.query_devices', return_value={'max_output_channels': 2, 'name': 'Fake USB Device'})
        self.mock_sd = self.patcher_sd.start()

        # Patch AscendingMethod in main_ui with our fake
        self.patcher_am = patch('audiometer.main_ui.AscendingMethod', new=FakeAscendingEarChanges)
        self.mock_am = self.patcher_am.start()

        # Create the app instance
        self.app = main_ui.AudiometerUI()

        # Set valid form fields
        self.app.device_var.set('0: Fake USB Device')
        self.app.id_entry.delete(0, 'end')
        self.app.id_entry.insert(0, 'PATIENT1')
        self.app.name_entry.delete(0, 'end')
        self.app.name_entry.insert(0, 'Patient Test')

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            pass
        self.patcher_am.stop()
        self.patcher_sd.stop()

    def test_ear_indicator_updates_and_styles(self):
        # Click the Start button
        self.app.quick_mode_var.set(False)
        self.app.start_button.invoke()

        # Poll the UI until we observe the RIGHT ear indicator
        timeout = time.time() + 3.0
        saw_right = False
        saw_left = False
        while time.time() < timeout and not (saw_right and saw_left):
            # Process UI events
            try:
                self.app.update()
            except Exception:
                pass

            txt = self.app.ear_indicator_label.cget('text')
            style = self.app.ear_indicator_label.cget('bootstyle')

            if txt == 'TESTING: RIGHT EAR 🔴':
                saw_right = True
                self.assertEqual(style, 'danger', 'RIGHT ear should use danger style')

            if txt == 'TESTING: LEFT EAR 🔵':
                saw_left = True
                self.assertEqual(style, 'info', 'LEFT ear should use info style')

            time.sleep(0.01)

        self.assertTrue(saw_right and saw_left, 'Ear indicator did not show both RIGHT and LEFT changes')


if __name__ == '__main__':
    unittest.main()
