"""Generation of pure tones with strict stereo channel separation."""
import numpy as np
import sounddevice as sd
import logging

class AudioStream:
    def __init__(self, device, attack, release):
        if attack <= 0 or release <= 0:
            raise ValueError("Attack/release must be positive")
        
        # Get device's native sample rate to avoid resampling errors
        try:
            if device is not None:
                devinfo = sd.query_devices(device, 'output')
                self.samplerate = int(devinfo['default_samplerate']) # type: ignore
            else:
                self.samplerate = 44100 # Fallback for default device
        except Exception:
            self.samplerate = 44100 # Fallback on error

        # Matrix Masking: Default to silence [Left=0, Right=0]
        self.channel_mask = np.array([0.0, 0.0])
        
        # Always request 2 channels for stereo
        self._stream = sd.OutputStream(
            device=device,
            callback=self._callback,
            channels=2,
            samplerate=self.samplerate
        )
        
        self._attack = np.round(self.samplerate * (attack / 1000)).astype(int)
        self._release = np.round(self.samplerate * (release / 1000)).astype(int)
        self._last_gain = 0
        self._index = 0
        self._target_gain = 0
        self._callback_parameters = (0, 0, 0) # target, slope, freq
        self._callback_status = sd.CallbackFlags()
        self._stream.start()

    def _callback(self, outdata, frames, time, status):
        """Matrix Multiplication Callback - Guarantees Isolation"""
        assert frames > 0
        self._callback_status |= status
        
        target_gain, slope, freq = self._callback_parameters
        
        # Generate Mono Sine Wave
        k = np.arange(self._index, self._index + frames)
        ramp = np.arange(frames) * slope + self._last_gain + slope
        
        if slope > 0:
            gain = np.minimum(target_gain, ramp)
        else:
            gain = np.maximum(target_gain, ramp)
        
        # Mono signal: Shape (Frames,)
        signal = gain * np.sin(2 * np.pi * freq * k / self.samplerate)
        
        # BROADCASTING MAGIC: (Frames, 1) * (2,) = (Frames, 2)
        # This multiplies the signal by [1, 0] (Left) or [0, 1] (Right)
        stereo_signal = signal[:, np.newaxis] * self.channel_mask
        
        # Assign to output buffer
        outdata[:] = stereo_signal
        
        self._index += frames
        self._last_gain = gain[-1]

    def start(self, freq, gain_db, earside=None):
        if self._target_gain != 0:
            raise ValueError("Target gain must be zero before start")
            
        # Set the Mask based on ear
        if earside == 'left':
            self.channel_mask = np.array([1.0, 0.0]) # Left ONLY
        elif earside == 'right':
            self.channel_mask = np.array([0.0, 1.0]) # Right ONLY
        else:
            raise ValueError(f"Invalid earside: {earside}")

        target_gain = _db2lin(gain_db)
        slope = target_gain / self._attack
        self._target_gain = target_gain
        self._callback_parameters = target_gain, slope, freq

    def stop(self):
        target_gain = 0
        slope = - self._target_gain / self._release
        self._target_gain = target_gain
        # Keep freq, update gain/slope
        self._callback_parameters = target_gain, slope, self._callback_parameters[2]

    def close(self):
        self._stream.stop()
        self._stream.close()

    def __enter__(self): return self
    def __exit__(self, *args): self.close()

def _db2lin(db_value): return 10 ** (db_value / 20)