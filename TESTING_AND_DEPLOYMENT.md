# Audiometer Testing & Deployment Guide

## System Requirements

- **PC with USB headphones** (Windows, Mac, or Linux)
- **Python 3.8+**
- GPIO Button (optional, for Raspberry Pi deployment)

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies:**
- `numpy>=1.21.0` - Numerical computations
- `sounddevice>=0.4.5` - Audio device control
- `matplotlib>=3.4.0` - Audiogram visualization
- `PySimpleGUI>=4.60.0` - GUI framework

### 2. Verify Audio Devices

Check available USB audio devices:

```bash
python -c "import sounddevice as sd; print(sd.query_devices())"
```

Note the device ID of your USB headphones (e.g., `Device #5`).

## Testing

### Unit Tests

Run the test suite:

```bash
cd tests
python run_all_tests.py
```

**Test Coverage:**
- `test_responder.py` - GPIO button input simulation
- `test_tone_generator.py` - Audio tone generation
- `test_controller.py` - Test logic and dB conversions

Expected output:
```
Tests run: 25+
Successes: 25+
Failures: 0
Errors: 0
```

### Integration Tests

Run a single frequency test:

```bash
python -c "
from ascending_method import AscendingMethod

# Test with device 5 (your USB headphones)
with AscendingMethod(device_id=5) as test:
    test.ctrl.config.freqs = [1000]  # Test only 1kHz
    test.ctrl.config.earsides = ['right']  # Right ear only
    test.run()
"
```

## Deployment & Usage

### Option 1: Command-Line Interface (CLI)

Run the standard ascending method test:

```bash
# Auto-detect USB headphones
python ascending_method.py

# Specify a device ID
python ascending_method.py --device 5

# Enable logging
python ascending_method.py --device 5 --logging

# Custom test parameters
python ascending_method.py --device 5 --beginning-fam-level 30 --tone-duration 2
```

### Option 2: Graphical User Interface (GUI)

Launch the full-featured GUI:

```bash
python main_ui.py
```

**Features:**
- Device selection dropdown
- Visual feedback during testing
- Results management
- Real-time status updates

### Option 3: Raspberry Pi with GPIO Button

For Raspberry Pi deployment with GPIO Pin 17:

1. **Install RPi.GPIO:**
   ```bash
   pip install RPi.GPIO
   ```

2. **Wire the button:**
   - GPIO Pin 17 to Ground (via push button)
   - Internal pull-up resistor enabled in code

3. **Run tests:**
   ```bash
   python ascending_method.py
   ```

The system uses automatic button detection (no arrow keys needed).

## Configuration

### Audio Device Selection

The system automatically detects USB headphones. If you have multiple devices:

```bash
# List all devices
python -c "import sounddevice as sd; print(sd.query_devices())"

# Run with specific device
python ascending_method.py --device 5
```

### Test Parameters

Edit `audiometer/controller.py` or pass arguments:

```bash
python ascending_method.py \
  --device 5 \
  --beginning-fam-level 30 \
  --tone-duration 2 \
  --small-level-increment 5 \
  --large-level-increment 10 \
  --tolerance 1.5
```

**Key Parameters:**
- `--device`: Audio device ID
- `--beginning-fam-level`: Familiarization starting level (dBHL)
- `--tone-duration`: Duration of each tone (seconds)
- `--tolerance`: Button release tolerance (seconds)

## Results

### Output Files

Test results are saved to `audiometer/results/`:

```
result_2025-12-10_14-30-45.csv
result_2025-12-10_15-45-22.csv
...
```

### CSV Format

```
Conduction,air,
Masking,off,
Level/dB,Frequency/Hz,Earside
25,1000,right
30,1500,right
35,2000,right
...
```

### Audiogram Generation

An audiogram PDF is automatically generated after each test:

```
result_2025-12-10_14-30-45.csv.pdf
```

## Troubleshooting

### "No audio output devices found"

Check your USB connection:
```bash
python -c "import sounddevice as sd; print(sd.query_devices())"
```

### "Signal is distorted" Warning

Reduce the starting level:
```bash
python ascending_method.py --beginning-fam-level 20
```

### Button not detected (Raspberry Pi)

Verify GPIO connection:
```python
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
print(GPIO.input(17))  # Should print 1 (released) or 0 (pressed)
```

### Module import errors

Reinstall dependencies:
```bash
pip install --upgrade -r requirements.txt
```

## Architecture

```
main_ui.py              <- GUI Launcher
│
├── ascending_method.py <- Test Controller (Hughson-Westlake)
│   │
│   └── audiometer/
│       ├── controller.py      <- Audio Logic & dB Conversions
│       ├── responder.py       <- Button Input (GPIO or UI)
│       ├── tone_generator.py  <- Audio Output (sounddevice)
│       ├── audiogram.py       <- Result Visualization
│       └── pyxhook/          <- (Legacy, not used)
│
└── tests/
    ├── test_responder.py
    ├── test_controller.py
    ├── test_tone_generator.py
    └── run_all_tests.py

```

## Performance Benchmarks

- **Startup Time:** <1 second
- **Tone Latency:** <50ms
- **Button Detection:** <20ms
- **Full Test Duration:** 10-15 minutes (typical)

## Support

For issues with:
- **Audio Devices:** Check `sounddevice` documentation
- **Raspberry Pi GPIO:** See `RPi.GPIO` documentation  
- **Test Logic:** Review ISO 8253-1 standard
- **Calibration:** Consult `docs/audiometer_doc.ipynb`

## Legal Notice

This software is intended for **research and assessment purposes only**. It is not a medical device and should not be used for clinical diagnosis. Always consult an audiologist for professional hearing evaluation.
