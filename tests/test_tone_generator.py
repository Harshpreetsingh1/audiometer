"""Unit tests for the tone generator module."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from audiometer import tone_generator


class TestToneGenerator(unittest.TestCase):
    """Test tone generation functions."""

    def test_db2lin_conversion(self):
        """Test dB to linear conversion."""
        # 0 dB should be 1.0
        self.assertAlmostEqual(tone_generator._db2lin(0), 1.0)
        
        # -20 dB should be 0.1
        self.assertAlmostEqual(tone_generator._db2lin(-20), 0.1, places=5)
        
        # 20 dB should be 10.0
        self.assertAlmostEqual(tone_generator._db2lin(20), 10.0)

    def test_seconds2samples_conversion(self):
        """Test seconds to samples conversion."""
        samplerate = 44100
        
        # 1 second should be 44100 samples
        samples = tone_generator._seconds2samples(1)
        self.assertEqual(samples, samplerate)
        
        # 0.5 seconds should be 22050 samples
        samples = tone_generator._seconds2samples(0.5)
        self.assertEqual(samples, samplerate * 0.5)

    @patch('audiometer.tone_generator.sd.OutputStream')
    def test_audiostream_init(self, mock_stream_class):
        """Test AudioStream initialization."""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        audio = tone_generator.AudioStream(device=None, attack=30, release=40)

        # Verify OutputStream was created
        mock_stream_class.assert_called_once()
        
        # Verify attack and release values
        self.assertGreater(audio._attack, 0)
        self.assertGreater(audio._release, 0)

    @patch('audiometer.tone_generator.sd.OutputStream')
    @patch('audiometer.tone_generator.sd.query_devices')
    def test_audiostream_respects_device_channels(self, mock_query, mock_stream_class):
        """AudioStream should request mono if device only has one output channel."""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream
        mock_query.return_value = {'max_output_channels': 1}

        audio = tone_generator.AudioStream(device=0, attack=30, release=40)

        # Ensure we requested a mono stream
        mock_stream_class.assert_called_once()
        args, kwargs = mock_stream_class.call_args
        self.assertEqual(kwargs.get('channels'), 1)

    @patch('audiometer.tone_generator.sd.OutputStream')
    def test_audiostream_init_invalid_attack(self, mock_stream_class):
        """Test AudioStream raises error for invalid attack value."""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        with self.assertRaises(ValueError):
            tone_generator.AudioStream(device=None, attack=0, release=40)

    @patch('audiometer.tone_generator.sd.OutputStream')
    def test_audiostream_init_invalid_release(self, mock_stream_class):
        """Test AudioStream raises error for invalid release value."""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        with self.assertRaises(ValueError):
            tone_generator.AudioStream(device=None, attack=30, release=-5)

    @patch('audiometer.tone_generator.sd.OutputStream')
    def test_audiostream_start(self, mock_stream_class):
        """Test AudioStream start method."""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        audio = tone_generator.AudioStream(device=None, attack=30, release=40)
        audio.start(freq=1000, gain_db=-20, earside='left')

        # Verify frequency and target gain were set
        self.assertEqual(audio._freq, 1000)
        self.assertGreater(audio._target_gain, 0)

    @patch('audiometer.tone_generator.sd.OutputStream')
    def test_audiostream_start_invalid_earside(self, mock_stream_class):
        """Test AudioStream start raises error for invalid earside."""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        audio = tone_generator.AudioStream(device=None, attack=30, release=40)

        with self.assertRaises(ValueError):
            audio.start(freq=1000, gain_db=-20, earside='center')

    @patch('audiometer.tone_generator.sd.OutputStream')
    def test_audiostream_start_left_channel(self, mock_stream_class):
        """Test AudioStream sets left channel correctly."""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        audio = tone_generator.AudioStream(device=None, attack=30, release=40)
        audio.start(freq=1000, gain_db=-20, earside='left')

        self.assertEqual(audio._channel, 0)

    @patch('audiometer.tone_generator.sd.OutputStream')
    def test_audiostream_start_right_channel(self, mock_stream_class):
        """Test AudioStream sets right channel correctly."""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        audio = tone_generator.AudioStream(device=None, attack=30, release=40)
        audio.start(freq=1000, gain_db=-20, earside='right')

        self.assertEqual(audio._channel, 1)

    @patch('audiometer.tone_generator.sd.OutputStream')
    def test_audiostream_context_manager(self, mock_stream_class):
        """Test AudioStream as context manager."""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        with tone_generator.AudioStream(device=None, attack=30, release=40) as audio:
            self.assertIsNotNone(audio)

        mock_stream.stop.assert_called()

    @patch('audiometer.tone_generator.sd.OutputStream')
    def test_callback_writes_only_one_channel_left(self, mock_stream_class):
        """Callback should write only to left channel when earside='left'."""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        audio = tone_generator.AudioStream(device=None, attack=30, release=40)
        # Simulate parameters like after start()
        audio._channel = 0
        audio._callback_parameters = (1.0, 0.1, 1000)
        audio._index = 0
        audio._last_gain = 0

        frames = 16
        outdata = np.zeros((frames, 2), dtype=float)
        audio._callback(outdata, frames, None, tone_generator.sd.CallbackFlags())

        # Left channel should contain signal; right channel should be all zeros
        self.assertTrue((outdata[:, 0] != 0).any())
        self.assertTrue((outdata[:, 1] == 0).all())

    @patch('audiometer.tone_generator.sd.OutputStream')
    def test_callback_writes_only_one_channel_right(self, mock_stream_class):
        """Callback should write only to right channel when earside='right'."""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        audio = tone_generator.AudioStream(device=None, attack=30, release=40)
        # Simulate parameters like after start()
        audio._channel = 1
        audio._callback_parameters = (1.0, 0.1, 1000)
        audio._index = 0
        audio._last_gain = 0

        frames = 16
        outdata = np.zeros((frames, 2), dtype=float)
        audio._callback(outdata, frames, None, tone_generator.sd.CallbackFlags())

        # Right channel should contain signal; left channel should be all zeros
        self.assertTrue((outdata[:, 1] != 0).any())
        self.assertTrue((outdata[:, 0] == 0).all())


if __name__ == '__main__':
    unittest.main()
