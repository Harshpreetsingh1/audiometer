"""Generation of pure tones with strict stereo channel separation.

This module ensures that audio output is properly isolated to either the left
or right channel only, preventing audio leakage between ears during hearing tests.
"""

import numpy as np
import sounddevice as sd
import logging

samplerate = 44100


class AudioStream:
    """Audio stream with strict stereo channel separation.
    
    Ensures that tones are played ONLY in the specified ear (left or right)
    with the other channel explicitly silenced to prevent audio leakage.
    """
    
    def __init__(self, device, attack, release):
        if attack <= 0 or release <= 0:
            raise ValueError("attack and release have to be positive "
                             "and different from zero")
        
        # CRITICAL: Always request 2 channels (stereo) for proper ear separation
        # If device doesn't support stereo, we'll handle it gracefully but warn
        req_channels = 2
        device_supports_stereo = True
        
        try:
            if device is not None:
                devinfo = sd.query_devices(device)
                max_out = int(devinfo.get('max_output_channels', 2))
                if max_out < 2:
                    device_supports_stereo = False
                    logging.warning(
                        f"Selected audio device only supports {max_out} output channel(s). "
                        "Strict stereo separation may not be possible. "
                        "Ear-specific testing may be limited."
                    )
        except Exception as e:
            logging.warning(f"Could not query device capabilities: {e}. Assuming stereo support.")
        
        # Initialize stream with 2 channels (stereo) - sounddevice will handle
        # devices that don't support it, but we always request stereo
        self._stream = sd.OutputStream(
            device=device,
            callback=self._callback,
            channels=req_channels,  # Always 2 for stereo
            samplerate=samplerate
        )
        
        self._attack = np.round(_seconds2samples(attack / 1000)).astype(int)
        self._release = np.round(_seconds2samples(release / 1000)).astype(int)
        self._last_gain = 0
        self._channel = 0  # 0 = left, 1 = right
        self._index = 0
        target_gain = 0
        slope = 0
        freq = 0
        self._callback_parameters = target_gain, slope, freq
        self._target_gain = target_gain
        self._callback_status = sd.CallbackFlags()
        self._stream.start()

    def _callback(self, outdata, frames, time, status):
        """Callback function for audio output with strict channel isolation.
        
        CRITICAL: This function ensures that audio is written ONLY to the
        target channel (left=0 or right=1) and the other channel is
        explicitly set to zero (silence) to prevent audio leakage.
        """
        assert frames > 0
        self._callback_status |= status
        
        # Get current tone parameters (thread-safe)
        target_gain, slope, freq = self._callback_parameters
        
        # Generate tone signal
        k = np.arange(self._index, self._index + frames)
        ramp = np.arange(frames) * slope + self._last_gain + slope
        assert slope != 0 or (target_gain == 0 and self._last_gain == 0)
        
        if slope > 0:
            gain = np.minimum(target_gain, ramp)
        else:
            gain = np.maximum(target_gain, ramp)
        
        signal = gain * np.sin(2 * np.pi * freq * k / samplerate)
        
        # CRITICAL: Strict stereo separation
        # Get number of channels in output buffer
        nch = outdata.shape[1]
        
        # Zero out ALL channels first to ensure clean state
        outdata.fill(0)
        
        # Write signal ONLY to the target channel (left=0 or right=1)
        if nch >= 2:
            # Stereo output: write to target channel only
            if self._channel == 0:
                # Left ear: write to channel 0, channel 1 stays zero
                outdata[:, 0] = signal
                # Explicitly ensure channel 1 is zero (already done by fill(0), but be explicit)
                outdata[:, 1] = 0
            elif self._channel == 1:
                # Right ear: write to channel 1, channel 0 stays zero
                outdata[:, 0] = 0  # Explicitly zero left channel
                outdata[:, 1] = signal
            else:
                # Invalid channel - zero everything
                outdata.fill(0)
                logging.error(f"Invalid channel {self._channel}. Expected 0 (left) or 1 (right).")
        elif nch == 1:
            # Mono fallback: write to single channel
            # This should not happen if device reports stereo support, but handle gracefully
            logging.warning("Mono output detected - strict stereo separation not possible")
            outdata[:, 0] = signal
        else:
            # No channels? Zero everything
            outdata.fill(0)
            logging.error(f"Invalid number of channels: {nch}")
        
        self._index += frames
        self._last_gain = gain[-1]

    def start(self, freq, gain_db, earside=None):
        """Start playing a tone in the specified ear.
        
        Args:
            freq: Frequency in Hz
            gain_db: Gain in dBFS
            earside: 'left' or 'right' - determines which channel receives the signal
        """
        if self._target_gain != 0:
            raise ValueError("Before calling start(), "
                             "target_gain must be zero")
        if gain_db == -np.inf:
            raise ValueError("gain_db must be a finite value")
        
        target_gain = _db2lin(gain_db)
        slope = target_gain / self._attack
        self._target_gain = target_gain
        self._freq = freq
        self._callback_parameters = target_gain, slope, freq
        
        # Set target channel based on earside
        if earside == 'left':
            self._channel = 0  # Left channel
        elif earside == 'right':
            self._channel = 1  # Right channel
        else:
            raise ValueError(f"earside must be 'left' or 'right', got '{earside}'")

    def stop(self):
        """Stop playing the tone with release envelope."""
        if self._target_gain == 0:
            raise ValueError("Before calling stop(),"
                             "target_gain must be different from zero")
        target_gain = 0
        slope = - self._target_gain / self._release
        self._target_gain = target_gain
        self._callback_parameters = target_gain, slope, self._freq

    def close(self):
        """Close the audio stream and log any callback errors."""
        if self._callback_status:
            logging.warning(str(self._callback_status))
        self._stream.stop()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def _db2lin(db_value):
    """Convert dB to linear gain."""
    return 10 ** (db_value / 20)


def _seconds2samples(seconds):
    """Convert seconds to number of samples at the current sample rate."""
    return samplerate * seconds
