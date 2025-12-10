"""Unit tests for the controller module."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from audiometer import controller


class TestControllerConfig(unittest.TestCase):
    """Test controller configuration."""

    @patch('sys.argv', ['test_script.py'])
    def test_config_defaults(self):
        """Test that config uses sensible defaults."""
        with patch('os.path.exists', return_value=True):
            config = controller.config()

            self.assertEqual(config.device, None)
            self.assertEqual(config.beginning_fam_level, 40)
            self.assertEqual(config.tone_duration, 2)
            self.assertEqual(config.conduction, 'air')
            self.assertEqual(config.masking, 'off')

    @patch('sys.argv', ['test_script.py', '--device', '2'])
    def test_config_device_argument(self):
        """Test that device argument is parsed correctly."""
        with patch('os.path.exists', return_value=True):
            config = controller.config()
            self.assertEqual(config.device, 2)

    @patch('sys.argv', ['test_script.py', '--beginning-fam-level', '30'])
    def test_config_beginning_fam_level(self):
        """Test familiarization level argument."""
        with patch('os.path.exists', return_value=True):
            config = controller.config()
            self.assertEqual(config.beginning_fam_level, 30)


class TestControllerDBHL(unittest.TestCase):
    """Test dBHL to dBFS conversion."""

    @patch('audiometer.tone_generator.AudioStream')
    @patch('audiometer.responder.Responder')
    @patch('sys.argv', ['test_script.py'])
    def test_dbhl2dbfs_conversion(self, mock_responder, mock_audio):
        """Test dBHL to dBFS conversion."""
        mock_responder.return_value = MagicMock()
        mock_audio.return_value = MagicMock()

        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', MagicMock()):
                with patch('csv.writer'):
                    ctrl = controller.Controller()
                    
                    # Test known conversion
                    result = ctrl.dBHL2dBFS(1000, 0)  # 0 dBHL at 1000 Hz
                    
                    # Should be non-zero (depends on calibration)
                    self.assertIsNotNone(result)
                    self.assertIsInstance(result, (int, float))


class TestControllerClicktone(unittest.TestCase):
    """Test clicktone method."""

    @patch('audiometer.tone_generator.AudioStream')
    @patch('audiometer.responder.Responder')
    @patch('sys.argv', ['test_script.py'])
    @patch('time.sleep')
    def test_clicktone_no_button_press(self, mock_sleep, mock_responder, mock_audio):
        """Test clicktone when no button is pressed."""
        mock_resp_instance = MagicMock()
        mock_resp_instance.click_down.return_value = False
        mock_resp_instance.clear = MagicMock()
        mock_responder.return_value = mock_resp_instance

        mock_audio_instance = MagicMock()
        mock_audio.return_value = mock_audio_instance

        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', MagicMock()):
                with patch('csv.writer'):
                    ctrl = controller.Controller()
                    result = ctrl.clicktone(1000, 50, 'right')

                    # Should return False when button not pressed
                    self.assertFalse(result)

    @patch('audiometer.tone_generator.AudioStream')
    @patch('audiometer.responder.Responder')
    @patch('sys.argv', ['test_script.py'])
    @patch('time.sleep')
    @patch('time.time')
    def test_clicktone_with_button_press(self, mock_time, mock_sleep, mock_responder, mock_audio):
        """Test clicktone when button is pressed quickly."""
        mock_resp_instance = MagicMock()
        mock_resp_instance.click_down.return_value = True
        mock_resp_instance.wait_for_click_up = MagicMock()
        mock_resp_instance.clear = MagicMock()
        mock_responder.return_value = mock_resp_instance

        mock_audio_instance = MagicMock()
        mock_audio.return_value = mock_audio_instance

        # Mock time to simulate quick button press (within tolerance)
        mock_time.side_effect = [0, 1.0]  # 1 second press (tolerance = 1.5)

        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', MagicMock()):
                with patch('csv.writer'):
                    ctrl = controller.Controller()
                    result = ctrl.clicktone(1000, 50, 'right')

                    # Should return True for quick press
                    self.assertTrue(result)


class TestAudiblTone(unittest.TestCase):
    """Test audibletone method."""

    @patch('audiometer.tone_generator.AudioStream')
    @patch('audiometer.responder.Responder')
    @patch('sys.argv', ['test_script.py'])
    @patch('time.sleep')
    def test_audibletone_button_pressed_immediately(self, mock_sleep, mock_responder, mock_audio):
        """Test audibletone when button is pressed at first level."""
        mock_resp_instance = MagicMock()
        mock_resp_instance.click_down.return_value = True
        mock_resp_instance.wait_for_click_up = MagicMock()
        mock_resp_instance.clear = MagicMock()
        mock_responder.return_value = mock_resp_instance

        mock_audio_instance = MagicMock()
        mock_audio.return_value = mock_audio_instance

        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', MagicMock()):
                with patch('csv.writer'):
                    with patch('builtins.print'):
                        ctrl = controller.Controller()
                        result = ctrl.audibletone(1000, 40, 'right')

                        # Should return the starting level
                        self.assertEqual(result, 40)

    @patch('audiometer.tone_generator.AudioStream')
    @patch('audiometer.responder.Responder')
    @patch('sys.argv', ['test_script.py'])
    @patch('time.sleep')
    def test_audibletone_increases_level(self, mock_sleep, mock_responder, mock_audio):
        """Test audibletone increases level when button not pressed."""
        mock_resp_instance = MagicMock()
        # First call: not pressed, second call: pressed
        mock_resp_instance.click_down.side_effect = [False, True]
        mock_resp_instance.wait_for_click_up = MagicMock()
        mock_resp_instance.clear = MagicMock()
        mock_responder.return_value = mock_resp_instance

        mock_audio_instance = MagicMock()
        mock_audio.return_value = mock_audio_instance

        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', MagicMock()):
                with patch('csv.writer'):
                    with patch('builtins.print'):
                        ctrl = controller.Controller()
                        result = ctrl.audibletone(1000, 40, 'right')

                        # Should return increased level
                        self.assertEqual(result, 50)


if __name__ == '__main__':
    unittest.main()
