#!/usr/bin/env python3
import sounddevice as sd

devices = sd.query_devices()
print("Audio output devices:")
for i, d in enumerate(devices):
    if d['max_output_channels'] > 0:
        print(f"{i}: {d['name']}")
