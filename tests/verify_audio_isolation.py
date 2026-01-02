import unittest
import numpy as np
from unittest.mock import patch

from audiometer.tone_generator import AudioStream


class FakeOutputStream:
    def __init__(self, device, callback, channels, samplerate):
        # Store callback for manual invocation if needed
        self._callback = callback
        self.channels = channels
        self.samplerate = samplerate
    def start(self):
        # Do not call callback automatically
        return
    def stop(self):
        return


class TestAudioIsolation(unittest.TestCase):
    def setUp(self):
        # Patch sounddevice OutputStream so no real audio device is touched
        self.patcher = patch('audiometer.tone_generator.sd.OutputStream', new=FakeOutputStream)
        self.patcher.start()

        # Create a stream instance that will not touch sound hardware
        self.stream = AudioStream(device=None, attack=30, release=40)

    def tearDown(self):
        try:
            self.stream.close()
        except Exception:
            pass
        self.patcher.stop()

    def _call_callback(self, stream, frames=64):
        outdata = np.zeros((frames, 2), dtype=np.float32)
        # status can be 0 or a CallbackFlags instance; use 0 here
        stream._index = 0
        # Use a CallbackFlags instance for status to avoid type errors
        status = stream._callback_status.__class__() if hasattr(stream, '_callback_status') else 0
        stream._callback(outdata, frames, None, status)
        return outdata

    def test_left_channel_silences_right(self):
        self.stream.start(freq=1000, gain_db=-10, earside='left')
        out = self._call_callback(self.stream, frames=128)
        # Right channel (index 1) must be all zeros
        self.assertTrue(np.allclose(out[:, 1], 0.0), "Right channel should be silent for left ear")
        # Left channel should contain non-zero signal
        self.assertTrue(np.any(np.abs(out[:, 0]) > 0), "Left channel should contain signal")

    def test_right_channel_silences_left(self):
        self.stream.start(freq=1000, gain_db=-10, earside='right')
        out = self._call_callback(self.stream, frames=128)
        # Left channel (index 0) must be all zeros
        self.assertTrue(np.allclose(out[:, 0], 0.0), "Left channel should be silent for right ear")
        self.assertTrue(np.any(np.abs(out[:, 1]) > 0), "Right channel should contain signal")


if __name__ == '__main__':
    unittest.main()
