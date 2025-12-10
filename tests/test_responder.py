"""Unit tests for the responder module (GPIO-based)."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from audiometer.responder import Responder


class TestResponder(unittest.TestCase):
    """Test Responder class with mocked GPIO."""

    def setUp(self):
        """Set up test fixtures."""
        self.tone_duration = 2.0

    @patch('audiometer.responder.GPIO')
    def test_responder_init(self, mock_gpio):
        """Test Responder initialization with GPIO."""
        mock_gpio.setmode = Mock()
        mock_gpio.setup = Mock()
        mock_gpio.add_event_detect = Mock()
        mock_gpio.BCM = 'BCM'
        mock_gpio.IN = 'IN'
        mock_gpio.PUD_UP = 'PUD_UP'
        mock_gpio.BOTH = 'BOTH'

        responder = Responder(self.tone_duration)

        # Verify GPIO setup was called
        mock_gpio.setmode.assert_called_once_with('BCM')
        mock_gpio.setup.assert_called_once_with(17, 'IN', pull_up_down='PUD_UP')
        mock_gpio.add_event_detect.assert_called_once()
        
        self.assertEqual(responder._timeout, self.tone_duration)
        self.assertEqual(responder._button_pin, 17)

    @patch('audiometer.responder.GPIO')
    def test_click_down_button_pressed(self, mock_gpio):
        """Test click_down returns True when button is pressed."""
        mock_gpio.setmode = Mock()
        mock_gpio.setup = Mock()
        mock_gpio.add_event_detect = Mock()
        mock_gpio.BCM = 'BCM'
        mock_gpio.IN = 'IN'
        mock_gpio.PUD_UP = 'PUD_UP'
        mock_gpio.BOTH = 'BOTH'
        mock_gpio.LOW = 0
        mock_gpio.input = Mock(return_value=0)  # Button pressed (LOW)

        responder = Responder(self.tone_duration)
        result = responder.click_down()

        self.assertTrue(result)
        mock_gpio.input.assert_called_with(17)

    @patch('audiometer.responder.GPIO')
    def test_click_down_button_released(self, mock_gpio):
        """Test click_down returns False when button is released."""
        mock_gpio.setmode = Mock()
        mock_gpio.setup = Mock()
        mock_gpio.add_event_detect = Mock()
        mock_gpio.BCM = 'BCM'
        mock_gpio.IN = 'IN'
        mock_gpio.PUD_UP = 'PUD_UP'
        mock_gpio.BOTH = 'BOTH'
        mock_gpio.LOW = 0
        mock_gpio.HIGH = 1
        mock_gpio.input = Mock(return_value=1)  # Button released (HIGH)

        responder = Responder(self.tone_duration)
        result = responder.click_down()

        self.assertFalse(result)

    @patch('audiometer.responder.GPIO')
    def test_click_up_button_released(self, mock_gpio):
        """Test click_up returns True when button is released."""
        mock_gpio.setmode = Mock()
        mock_gpio.setup = Mock()
        mock_gpio.add_event_detect = Mock()
        mock_gpio.BCM = 'BCM'
        mock_gpio.IN = 'IN'
        mock_gpio.PUD_UP = 'PUD_UP'
        mock_gpio.BOTH = 'BOTH'
        mock_gpio.HIGH = 1
        mock_gpio.input = Mock(return_value=1)  # Button released (HIGH)

        responder = Responder(self.tone_duration)
        result = responder.click_up()

        self.assertTrue(result)

    @patch('audiometer.responder.GPIO')
    def test_close_cleanup(self, mock_gpio):
        """Test GPIO cleanup on close."""
        mock_gpio.setmode = Mock()
        mock_gpio.setup = Mock()
        mock_gpio.add_event_detect = Mock()
        mock_gpio.cleanup = Mock()
        mock_gpio.BCM = 'BCM'
        mock_gpio.IN = 'IN'
        mock_gpio.PUD_UP = 'PUD_UP'
        mock_gpio.BOTH = 'BOTH'

        responder = Responder(self.tone_duration)
        responder.close()

        mock_gpio.cleanup.assert_called_once_with(17)

    @patch('audiometer.responder.GPIO')
    def test_context_manager(self, mock_gpio):
        """Test Responder as context manager."""
        mock_gpio.setmode = Mock()
        mock_gpio.setup = Mock()
        mock_gpio.add_event_detect = Mock()
        mock_gpio.cleanup = Mock()
        mock_gpio.BCM = 'BCM'
        mock_gpio.IN = 'IN'
        mock_gpio.PUD_UP = 'PUD_UP'
        mock_gpio.BOTH = 'BOTH'

        with Responder(self.tone_duration) as responder:
            self.assertIsNotNone(responder)

        mock_gpio.cleanup.assert_called_once()

    def test_responder_without_gpio(self):
        """Test Responder fallback when GPIO is not available."""
        with patch.dict('sys.modules', {'RPi.GPIO': None}):
            # Reimport to trigger ImportError handling
            responder = Responder(self.tone_duration)
            
            # Should still initialize with safe defaults
            self.assertEqual(responder._timeout, self.tone_duration)
            self.assertEqual(responder._button_pin, 17)
            
            # Methods should return safe defaults
            self.assertFalse(responder.click_down())
            self.assertTrue(responder.click_up())


if __name__ == '__main__':
    unittest.main()
