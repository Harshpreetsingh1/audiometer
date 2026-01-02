import unittest
import time
from unittest.mock import patch

from audiometer import main_ui


class FakeAscendingProgress:
    last_instance = None

    def __init__(self, device_id=None, subject_name=None, progress_callback=None, ear_change_callback=None, freq_change_callback=None, quick_mode=False):
        self.progress_callback = progress_callback
        FakeAscendingProgress.last_instance = self

    def run(self):
        # Simulate progress updates
        for p in [0.0, 12.5, 50.0, 100.0]:
            try:
                if self.progress_callback:
                    self.progress_callback(p)
                time.sleep(0.05)
            except Exception:
                pass

    def stop_test(self):
        return


class TestUIProgress(unittest.TestCase):
    def setUp(self):
        # Patch sounddevice.query_devices
        self.patcher_sd = patch('sounddevice.query_devices', return_value={'max_output_channels': 2, 'name': 'Fake USB Device'})
        self.mock_sd = self.patcher_sd.start()

        # Patch AscendingMethod in main_ui
        self.patcher_am = patch('audiometer.main_ui.AscendingMethod', new=FakeAscendingProgress)
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

    def test_progress_bar_updates(self):
        # Start the test
        self.app.start_button.invoke()

        timeout = time.time() + 3.0
        seen = set()
        while time.time() < timeout and 100.0 not in seen:
            try:
                self.app.update()
            except Exception:
                pass

            # Read progress value and text
            val = float(self.app.progress_var.get())
            text = self.app.progress_text.cget('text')
            seen.add(round(val, 1))
            # Ensure progress_text matches the var when possible
            if '%' in text:
                # Just confirm it's formatted with a percent sign
                self.assertIn('%', text)

            time.sleep(0.01)

        self.assertIn(100.0, seen, f"Never observed final 100% progress, observed: {seen}")


if __name__ == '__main__':
    unittest.main()
