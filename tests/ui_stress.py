import unittest
import time
from unittest.mock import patch

import main_ui


class FakeAscendingStress:
    instances = 0
    last_instance = None

    def __init__(self, device_id=None, subject_name=None, progress_callback=None, ear_change_callback=None, freq_change_callback=None, quick_mode=False, mini_mode=False):
        FakeAscendingStress.instances += 1
        FakeAscendingStress.last_instance = self
        self._stop_requested = False
        # Provide a stop_event to mimic real AscendingMethod API
        import threading
        self.stop_event = threading.Event()

    def run(self):
        # Simulate a running test; check stop_event for termination
        for _ in range(40):
            if self.stop_event.is_set() or self._stop_requested:
                return
            time.sleep(0.05)

    def stop_test(self):
        self._stop_requested = True
        try:
            self.stop_event.set()
        except Exception:
            pass


class TestUIStress(unittest.TestCase):
    def setUp(self):
        # Patch sounddevice query to detect a fake device
        self.patcher_sd = patch('sounddevice.query_devices', return_value={'max_output_channels': 2, 'name': 'Fake USB Device'})
        self.patcher_sd.start()

        # Patch AscendingMethod with a fake that simulates running
        self.patcher_am = patch('main_ui.AscendingMethod', new=FakeAscendingStress)
        self.patcher_am.start()

        # Patch ttkbootstrap Checkbutton to avoid theme-specific layout errors during tests
        class DummyCheckbutton:
            def __init__(self, *args, **kwargs):
                # keep a reference to the command (if any) and variable
                self._cmd = kwargs.get('command')
                self._var = kwargs.get('variable', None)
            def pack(self, *a, **kw):
                pass
            def invoke(self):
                if callable(self._cmd):
                    return self._cmd()
                return None
        self.patcher_check = patch('ttkbootstrap.Checkbutton', new=DummyCheckbutton)
        self.patcher_check.start()

        # Create the app
        self.app = main_ui.AudiometerUI()
        # Replace tkinter BooleanVars with thread-safe simple vars for test
        class SimpleVar:
            def __init__(self, value=False):
                self._v = value
            def get(self):
                return self._v
            def set(self, v):
                self._v = bool(v)
        # Initialize testable vars
        self.app.quick_mode_var = SimpleVar(False)
        self.app.mini_mode_var = SimpleVar(False)

        # Fill valid form values
        self.app.device_var.set('0: Fake USB Device')
        self.app.id_entry.delete(0, 'end')
        self.app.id_entry.insert(0, 'STRESS1')
        self.app.name_entry.delete(0, 'end')
        self.app.name_entry.insert(0, 'Stress Test')

        # Replace after with immediate executor to avoid Tkinter mainloop requirements
        import threading
        self.app.after = lambda delay, func, *a, **kw: threading.Timer(0, func, args=a, kwargs=kw).start()

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            pass
        self.patcher_am.stop()
        self.patcher_sd.stop()
        try:
            self.patcher_check.stop()
        except Exception:
            pass

    def test_spam_start_clicks(self):
        FakeAscendingStress.instances = 0
        # Spam Start 10 times within one second
        start_time = time.time()
        while time.time() - start_time < 1.0:
            try:
                self.app.start_button.invoke()
            except Exception:
                self.app._start_test()
            time.sleep(0.01)

        # Wait a bit for any threads to begin
        time.sleep(0.2)
        # Only one instance should have been created
        self.assertEqual(FakeAscendingStress.instances, 1, f"Expected 1 test instance, got {FakeAscendingStress.instances}")

    def test_mid_test_stop_and_restart(self):
        FakeAscendingStress.instances = 0
        # Start test
        try:
            self.app.start_button.invoke()
        except Exception:
            self.app._start_test()
        time.sleep(0.3)
        # Click Stop
        self.app.stop_button.invoke()

        # Wait until UI reports not running (allow background cleanup)
        timeout = time.time() + 2.0
        while self.app.is_running and time.time() < timeout:
            time.sleep(0.05)

        # Start again after cleanup
        try:
            self.app.start_button.invoke()
        except Exception:
            self.app._start_test()

        # Wait until second instance starts (or timeout)
        timeout = time.time() + 2.0
        while FakeAscendingStress.instances < 2 and time.time() < timeout:
            time.sleep(0.05)

        # Should have created two instances over time
        self.assertTrue(FakeAscendingStress.instances >= 2, f"Expected >=2 instances after restart, got {FakeAscendingStress.instances}")

    def test_invalid_age_input(self):
        # Patch messagebox.showerror to capture invocation
        with patch('tkinter.messagebox.showerror') as mock_error:
            self.app.age_entry.delete(0, 'end')
            self.app.age_entry.insert(0, 'notanumber')
            # Click Start
            try:
                self.app.start_button.invoke()
            except Exception:
                self.app._start_test()

            self.assertTrue(mock_error.called, "Expected error dialog for invalid age input")


if __name__ == '__main__':
    unittest.main()
