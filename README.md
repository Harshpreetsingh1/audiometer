# Audiometry Pro

A professional PC-based audiometer application for conducting hearing tests. Built with Python and PyWebView for a modern, cross-platform experience.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)

## Features

- 🎧 **Pure Tone Audiometry** - Standard ascending method testing
- 📊 **Real-time Audiogram** - Visual threshold plotting
- 🔊 **USB Audio Support** - Works with calibrated audiometer hardware
- ⚡ **Quick Mode** - Fast 4-frequency screening
- 📁 **CSV Export** - Automatic result saving
- 🖥️ **Modern UI** - Dark theme with responsive design

## Quick Start

### Option 1: Run from Source

```powershell
# Clone the repository
git clone https://github.com/yourusername/audiometer.git
cd audiometer

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the application
python webview_app.py
```

### Option 2: Install from Setup

1. Download `Audiometry_Setup.exe` from [Releases](https://github.com/yourusername/audiometer/releases)
2. Run the installer
3. Launch from desktop shortcut

## Usage

1. **Select Audio Device** - Choose your calibrated USB audiometer
2. **Enter Patient Info** - Name, age, and ID
3. **Start Test** - Click START TEST button
4. **Patient Response** - Press the yellow button (or spacebar) when tone is heard
5. **View Results** - Audiogram displays automatically after completion

## Building the Executable

### Prerequisites

```powershell
pip install pyinstaller
```

### Build Steps

```powershell
# Build the executable
.\build.bat

# Output: dist\Audiometry_Pro.exe
```

## Creating the Installer

### Prerequisites

- Install [Inno Setup](https://jrsoftware.org/isdl.php) (free)

### Build Steps

1. First build the executable with `.\build.bat`
2. Open `setup.iss` in Inno Setup Compiler
3. Click **Compile** (or press F9)
4. Output: `Output\Audiometry_Setup.exe`

### Silent Installation

For IT deployment to multiple PCs:

```powershell
# Silent install (shows progress)
Audiometry_Setup.exe /SILENT

# Very silent (no UI at all)
Audiometry_Setup.exe /VERYSILENT
```

## Project Structure

```
audiometer/
├── webview_app.py          # Main application entry point
├── audiometer_ui.html      # Frontend UI
├── ascending_method.py     # Core audiometry logic
├── audiometer/             # Audio engine modules
│   ├── tone_generator.py
│   ├── controller.py
│   └── audiogram.py
├── build.bat               # PyInstaller build script
├── setup.iss               # Inno Setup installer script
└── requirements.txt        # Python dependencies
```

## Requirements

- Python 3.8+
- Windows 10/11
- USB audio device (for accurate audiometry)

### Python Dependencies

- `pywebview` - Desktop GUI framework
- `sounddevice` - Audio playback
- `numpy` - Signal generation

## Test Modes

| Mode | Frequencies | Duration |
|------|------------|----------|
| **Quick** | 500, 1000, 2000, 4000 Hz | ~5 min |
| **Mini** | 1000, 4000 Hz | ~2 min |
| **Full** | 125-8000 Hz (7 frequencies) | ~10 min |

## Results

Test results are saved to:
```
audiometer/results/[PatientName]_[DateTime].csv
```

## License

MIT License - See [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## Support

For issues or questions, please open a [GitHub Issue](https://github.com/yourusername/audiometer/issues).
