"""Unit tests for responder module (media key based)."""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from audiometer.responder import Responder


class TestResponder(unittest.TestCase):
    def setUp(self):
        self.tone_duration = 2.0

    def test_registers_media_keys_when_keyboard_available(self):
        from types import SimpleNamespace

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
            responder = Responder(self.tone_duration)

            # Should have registered handlers for each media key
            self.assertTrue(called['press'])
            self.assertTrue(called['release'])

            # Closing should not raise
            responder.close()

    def test_media_key_press_counts_as_click(self):
        callbacks = {}

        def on_press_key(name, cb, suppress=True):
            callbacks[f"press_{name}"] = cb
            return f"press_{name}"

        def on_release_key(name, cb, suppress=True):
            callbacks[f"release_{name}"] = cb
            return f"release_{name}"

        # Use a SimpleNamespace to act like a module
        from types import SimpleNamespace

        mock_keyboard = SimpleNamespace(
            on_press_key=on_press_key,
            on_release_key=on_release_key,
            unhook=lambda h: None,
        )

        with patch.dict('sys.modules', {'keyboard': mock_keyboard}):
            responder = Responder(self.tone_duration)

            # Simulate pressing 'volume up'
            callbacks['press_volume up'](Mock())
            self.assertTrue(responder.click_down())

            # Simulate releasing
            callbacks['release_volume up'](Mock())
            self.assertTrue(responder.click_up())

    def test_ui_button_works(self):
        responder = Responder(self.tone_duration)
        responder.ui_button_pressed()
        self.assertTrue(responder.click_down())
        responder.ui_button_released()
        self.assertTrue(responder.click_up())


if __name__ == '__main__':
    unittest.main()
