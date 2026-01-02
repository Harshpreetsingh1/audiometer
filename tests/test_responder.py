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

    def test_registers_media_keys_with_hook_api(self):
        """If keyboard provides a hook() API, responder should register two handlers and receive events."""
        from types import SimpleNamespace
        captured = []

        def hook(handler, suppress=False):
            # Record the handler and suppression request, and return the handler as the handle
            captured.append((handler, suppress))
            return handler

        def unhook(h):
            try:
                captured.remove((h, True))
            except ValueError:
                pass

        mock_keyboard = SimpleNamespace(hook=hook, unhook=unhook)

        with patch.dict('sys.modules', {'keyboard': mock_keyboard}):
            responder = Responder(self.tone_duration)

            # Expect two handlers registered via hook()
            self.assertEqual(len(responder._handlers), 2)
            # Both handlers should have been requested with suppression=True
            self.assertTrue(all(suppress for (_h, suppress) in captured))

            # Simulate a press event (down) on the first handler
            handler_func = captured[0][0]
            handler_func(SimpleNamespace(event_type='down'))
            self.assertTrue(responder.click_down())

            # Simulate release via second handler
            handler_func_release = captured[1][0]
            handler_func_release(SimpleNamespace(event_type='up'))
            self.assertTrue(responder.click_up())

    def test_registers_without_suppress_kwarg(self):
        """If on_press_key/on_release_key exist but don't accept suppress kwarg, responder should fall back to non-suppress registration."""
        from types import SimpleNamespace
        called = {'press': False, 'release': False}

        def on_press_key(name, cb, *args, **kwargs):
            if 'suppress' in kwargs:
                # Simulate API that does not accept suppress kwarg
                raise TypeError("suppress not supported")
            called['press'] = True
            return f"press_{name}"

        def on_release_key(name, cb, *args, **kwargs):
            if 'suppress' in kwargs:
                raise TypeError("suppress not supported")
            called['release'] = True
            return f"release_{name}"

        def unhook(h):
            # No-op
            return None

        mock_keyboard = SimpleNamespace(
            on_press_key=on_press_key,
            on_release_key=on_release_key,
            unhook=unhook
        )

        with patch.dict('sys.modules', {'keyboard': mock_keyboard}):
            responder = Responder(self.tone_duration)

            # Should have registered handlers even if suppress wasn't supported
            self.assertTrue(called['press'])
            self.assertTrue(called['release'])
            # Should have recorded that suppression isn't supported
            self.assertFalse(responder._suppress_supported)


if __name__ == '__main__':
    unittest.main()
