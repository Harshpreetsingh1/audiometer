"""Tests for responder timing (press during tone, release within tolerance)."""

import unittest
import threading
import time
import random
from types import SimpleNamespace

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


class FakeControllerForClickTest:
    def __init__(self, tone_duration=0.1, tolerance=0.2):
        self.config = SimpleNamespace(tone_duration=tone_duration,
                                      tolerance=tolerance,
                                      pause_time=[0, 0])
        self._audio = FakeAudio()
        self._rpd = responder.Responder(self.config.tone_duration)

    def _progress_sleep(self, total_time, stop_event=None):
        # Sleep normally to allow concurrent press/release timing test
        time.sleep(total_time)
        return True

    def dBHL2dBFS(self, freq, dBHL):
        # Return safe negative value so clicktone doesn't raise OverflowError
        return -1.0

    # Reuse Controller.clicktone logic locally for testing
    def clicktone(self, freq, current_level_dBHL, earside, stop_event=None):
        if self.dBHL2dBFS(freq, current_level_dBHL) > 0:
            raise OverflowError

        if stop_event and stop_event.is_set():
            return False

        self._rpd.clear()
        self._audio.start(freq, self.dBHL2dBFS(freq, current_level_dBHL), earside)

        if not self._progress_sleep(self.config.tone_duration, stop_event):
            self._audio.stop()
            return False

        click_down = self._rpd.click_down()
        self._audio.stop()

        if click_down:
            # Use recorded press/release timestamps when available to avoid
            # timing races between threads and the end of tone playback.
            press_ts = getattr(self._rpd, '_last_press_time', None)
            # Wait for release (blocks until release)
            self._rpd.wait_for_click_up()
            release_ts = getattr(self._rpd, '_last_release_time', None)

            if press_ts is not None and release_ts is not None:
                duration = release_ts - press_ts
            else:
                # Fallback: measure elapsed time around wait_for_click_up
                start = time.time()
                # If release already happened, wait_for_click_up() returns immediately
                self._rpd.wait_for_click_up()
                end = time.time()
                duration = end - start

            if duration <= self.config.tolerance:
                if stop_event and stop_event.is_set():
                    return False
                self._progress_sleep(random.uniform(self.config.pause_time[0], self.config.pause_time[1]) if self.config.pause_time else 0, stop_event)
                return True
            else:
                if stop_event and stop_event.is_set():
                    return False
                self._progress_sleep(random.uniform(self.config.pause_time[0], self.config.pause_time[1]) if self.config.pause_time else 0, stop_event)
                return False
        else:
            if stop_event and stop_event.is_set():
                return False
            self._progress_sleep(random.uniform(self.config.pause_time[0], self.config.pause_time[1]) if self.config.pause_time else 0, stop_event)
            return False


class TestResponderTiming(unittest.TestCase):
    def test_fast_release_within_tolerance_returns_true(self):
        ctrl = FakeControllerForClickTest(tone_duration=0.12, tolerance=0.2)

        # Thread: press shortly after tone starts, release quickly
        def presser():
            time.sleep(0.02)  # press during tone
            ctrl._rpd.ui_button_pressed()
            time.sleep(0.02)  # release quickly (within tolerance)
            ctrl._rpd.ui_button_released()

        t = threading.Thread(target=presser)
        t.start()

        result = ctrl.clicktone(freq=1000, current_level_dBHL=-20, earside='right')
        t.join()
        self.assertTrue(result)

    def test_slow_release_exceeds_tolerance_returns_false(self):
        ctrl = FakeControllerForClickTest(tone_duration=0.12, tolerance=0.05)

        def presser():
            time.sleep(0.02)  # press during tone
            ctrl._rpd.ui_button_pressed()
            time.sleep(0.1)   # release too late (after tolerance)
            ctrl._rpd.ui_button_released()

        t = threading.Thread(target=presser)
        t.start()

        result = ctrl.clicktone(freq=1000, current_level_dBHL=-20, earside='right')
        t.join()
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
