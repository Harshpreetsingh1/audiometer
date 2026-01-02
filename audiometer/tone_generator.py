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
        
        # Request channels based on device capability (prefer stereo)
        req_channels = 2
        device_supports_stereo = True
        
        try:
            if device is not None:
                devinfo = sd.query_devices(device)
                max_out = int(devinfo.get('max_output_channels', 2))
                if max_out < 2:
                    device_supports_stereo = False
                    req_channels = max_out
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
            channels=req_channels,
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
        
        # Stereo Masking Matrix: Pre-calculated channel mask for channel isolation
        # Will be set in start() based on earside parameter
        # Initialize to zero (no output) until start() is called
        # Left Ear: [1.0, 0.0] -> signal only in left channel
        # Right Ear: [0.0, 1.0] -> signal only in right channel
        # Initialize mask as float32 for safe broadcasting and low memory usage
        self.channel_mask = np.array([0.0, 0.0], dtype=np.float32)
        
        self._stream.start()

    def _callback(self, outdata, frames, time, status):
        """Callback function for audio output with Stereo Masking Matrix isolation.
        
        CRITICAL: This function uses a mathematically robust Stereo Masking Matrix
        approach to ensure audio is written ONLY to the target channel. The mono
        signal is multiplied by the channel_mask to create true stereo separation.
        """
        assert frames > 0
        # Safely accumulate callback status; in rare race conditions the
        # attribute may not yet exist or may have been cleaned up during GC.
        try:
            self._callback_status |= status
        except Exception:
            try:
                # Initialize fallback status if necessary
                self._callback_status = status
            except Exception:
                pass
        
        # Get current tone parameters (thread-safe)
        try:
            target_gain, slope, freq = self._callback_parameters
        except Exception:
            # In rare race conditions the parameters may not yet be initialized;
            # fallback to safe defaults (silence).
            target_gain = 0
            slope = 0
            freq = 0
        
        # Generate mono tone signal (1D array)
        k = np.arange(self._index, self._index + frames)
        ramp = np.arange(frames) * slope + self._last_gain + slope
        assert slope != 0 or (target_gain == 0 and self._last_gain == 0)
        
        if slope > 0:
            gain = np.minimum(target_gain, ramp)
        else:
            gain = np.maximum(target_gain, ramp)
        
        # Generate raw mono signal (1D array)
        signal = gain * np.sin(2 * np.pi * freq * k / samplerate)
        
        # CRITICAL: Stereo Masking Matrix approach
        # Validate output buffer has 2 channels (stereo)
        nch = outdata.shape[1]
        
        if nch == 2:
            # Stereo output: Use channel_mask to create true stereo separation
            # Ensure mono_signal is column vector (N, 1) for proper broadcasting
            # mono_signal[:, np.newaxis] creates shape (frames, 1)
            # self.channel_mask has shape (2,)
            # Broadcasting: (frames, 1) * (2,) -> (frames, 2)
            # If channel_mask is not set (all zeros), fall back to _channel
            if np.allclose(self.channel_mask, 0.0):
                if self._channel == 0:
                    mask = np.array([1.0, 0.0], dtype=np.float32)
                else:
                    mask = np.array([0.0, 1.0], dtype=np.float32)
            else:
                mask = self.channel_mask

            stereo_signal = signal[:, np.newaxis] * mask
            outdata[:] = stereo_signal
            
            # Debug: Check if sound is actually being generated (first ~1 second only)
            # Print every ~0.1 seconds (4410 samples) to avoid flooding console
            if self._index < samplerate:  # First second only
                max_amp = np.max(np.abs(outdata))
                # Print at intervals of ~0.1 seconds (4410 samples at 44.1kHz)
                print_interval = samplerate // 10  # 4410 samples
                if print_interval > 0:
                    # Check if we've crossed a print interval boundary
                    prev_index = self._index - frames
                    if (prev_index // print_interval) < (self._index // print_interval):
                        print(f"DEBUG: Callback active. Frame {self._index}, Max amp: {max_amp:.6f}, "
                              f"freq={freq:.1f}, channel_mask={self.channel_mask}")
        elif nch == 1:
            # Mono device fallback (should not happen, but handle gracefully)
            logging.warning("Mono output detected (device reports 1 channel) - "
                          "strict stereo separation not possible. Playing to single channel.")
            print("DEBUG: WARNING - Mono output detected, playing to single channel")
            outdata[:, 0] = signal
        else:
            # Invalid channel count
            outdata.fill(0)
            logging.error(f"Invalid number of channels: {nch}. Expected 2 (stereo).")
            print(f"DEBUG: ERROR - Invalid number of channels: {nch}. Expected 2 (stereo).")
        
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
        
        # Set target channel and channel_mask based on earside (Stereo Masking Matrix)
        if earside == 'left':
            self._channel = 0  # Left channel
            self.channel_mask = np.array([1.0, 0.0], dtype=np.float32)  # Signal only in left channel
            print(f"DEBUG: AudioStream.start() - Left ear, channel_mask={self.channel_mask}")
        elif earside == 'right':
            self._channel = 1  # Right channel
            self.channel_mask = np.array([0.0, 1.0], dtype=np.float32)  # Signal only in right channel
            print(f"DEBUG: AudioStream.start() - Right ear, channel_mask={self.channel_mask}")
        else:
            raise ValueError(f"earside must be 'left' or 'right', got '{earside}'")
        
        print(f"DEBUG: AudioStream.start() - freq={freq} Hz, gain_db={gain_db:.2f} dB, target_gain={target_gain:.6f}")

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