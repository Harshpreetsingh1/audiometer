# 🎯 PC Audiometer - Quick Reference Guide

## 🚀 Start Application

```bash
python main_ui.py
```

## 📋 What Was Fixed

| Issue | Status | File |
|-------|--------|------|
| Audio stops mid-test | ✓ FIXED | `responder.py` |
| UI freezes/hangs | ✓ FIXED | `main_ui.py` |
| Button not detected | ✓ FIXED | `responder.py`, `main_ui.py` |
| Inconsistent behavior | ✓ FIXED | `controller.py` |

## 🔌 Hardware Setup

1. Connect USB headphones to PC
2. Run `python main_ui.py`
3. Select USB headphones from dropdown
4. Click "START TEST"

## 🎵 During Test

1. **Listen** for beeping tones that increase in volume
2. **Click** "I HEAR THE TONE!" button when you hear the sound
3. Audio will:
   - **Stop increasing** if you click (confirms that level)
   - **Keep increasing** if you don't click (too quiet)
4. Test continues until all frequencies tested
5. Results saved automatically

## 📊 Results Location

```
audiometer/results/
├── result_2025-12-10_14-30-45.csv        ← Raw data
└── result_2025-12-10_14-30-45.csv.pdf    ← Audiogram
```

## ⚙️ Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run GUI
python main_ui.py
```

## 📱 Test Parameters (If Needed)

Edit these in `ascending_method.py` or via command-line:

```bash
python ascending_method.py --device 5 --beginning-fam-level 30
```

**Available options:**
- `--device`: Audio device ID
- `--beginning-fam-level`: Starting volume (dBHL)
- `--tone-duration`: Duration of each tone (seconds)
- `--small-level-increment`: Volume step size (dB)

## 🆘 Common Issues

| Problem | Fix |
|---------|-----|
| No audio devices | Check USB headphone cable |
| Audio stops playing | Restart and try again |
| Button not working | Click and hold firmly |
| Test freezes | Click STOP, restart app |

## 📁 Project Structure

```
audiometer/
├── main_ui.py                    ← GUI (THIS IS YOUR MAIN APP)
├── ascending_method.py           ← Test logic
├── requirements.txt              ← Dependencies
├── PC_AUDIOMETER_SOLUTION.md     ← Full documentation
├── BUG_FIXES.md                  ← Technical details
└── audiometer/
    ├── controller.py             ← Audio control [FIXED]
    ├── responder.py              ← Button handler [FIXED]
    ├── tone_generator.py         ← Audio output
    ├── audiogram.py              ← Result visualization
    └── results/                  ← Your test results
```

## ✅ Verification

```bash
# Test imports
python -c "from main_ui import *; print('✓ Ready to test')"

# Run tests
cd tests
python run_all_tests.py
```

## 💡 Tips

1. **Best results:** Take test in quiet room with comfortable headphones
2. **Button response:** Click firmly and release quickly
3. **Multiple tests:** New results automatically saved with timestamp
4. **View results:** Click "View Results" in GUI or check `audiometer/results/`

## 🔄 Workflow

```
Start App
   ↓
Select USB Headphones
   ↓
Click START TEST
   ↓
Wait for tone → Click when you hear it
   ↓
Repeat for all frequencies
   ↓
Test Complete → Results Saved
   ↓
View Audiogram PDF
```

## 📈 Understanding Your Results

**CSV Result Example:**
```
Level/dB,Frequency/Hz,Earside
25,1000,right        ← You heard 25dB at 1000Hz in right ear
30,1500,right
35,2000,right
...
```

**Audiogram PDF:**
- X-axis: Frequencies (Hz)
- Y-axis: Loudness level (dBHL)
- Points show your hearing threshold at each frequency
- Lower = Better hearing

## 🎓 For Developers

Want to modify the test?

1. **Change frequencies:** Edit `controller.py` config
2. **Adjust tone duration:** Use `--tone-duration` parameter
3. **Custom starting volume:** Use `--beginning-fam-level` parameter

Example:
```python
# In ascending_method.py, modify run() method to test only:
self.ctrl.config.freqs = [1000, 2000, 4000]  # Only these
self.ctrl.config.earsides = ['right']  # Only right ear
```

## 🎯 System Requirements

- Windows 7+, macOS 10.12+, or Linux (Ubuntu 18.04+)
- Python 3.8+
- USB headphones
- 100 MB free disk space

## 📞 Support

Check these files for more help:
- `PC_AUDIOMETER_SOLUTION.md` - Full technical guide
- `BUG_FIXES.md` - Detailed explanations of fixes
- `TESTING_AND_DEPLOYMENT.md` - Testing procedures

---

**Ready to test your hearing? Just run:**
```bash
python main_ui.py
```
