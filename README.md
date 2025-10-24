# Verbose

**Press a key. Speak. Press again. Text appears.**

Voice-to-text for Linux. 100% local, no subscriptions.

```bash
# 1. Install Python dependencies
sudo apt install python3-evdev python3-pyaudio python3-yaml python3-gi ydotool

# 2. Get whisper.cpp (OPTION A - Easiest: Download pre-compiled binary)
#    Download from: https://github.com/ggerganov/whisper.cpp/releases
#    Extract to ./whisper.cpp/
#    Download a model: cd whisper.cpp && bash models/download-ggml-model.sh base

# 2. Get whisper.cpp (OPTION B - Compile for better performance)
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp && mkdir build && cd build && cmake .. && make -j$(nproc) && cd ..
bash models/download-ggml-model.sh base && cd ..

# 3. Run it
python3 verbose.py

# 4. Use it - Press F9, speak, press F9 again
```

## What It Does

Local voice-to-text using whisper.cpp. Works in any application - terminals, browsers, IDEs.

No cloud dependencies. No API keys needed.

## Features

- Multiple configs with different hotkeys (F9 for coding, F10 for emails)
- Auto-correct common mistakes ("cloud code" → "Claude Code")
- Phrase shortcuts ("my email" → expands to full address)
- Works on login, lives in system tray
- Cancel anytime with ESC

## How It Works

1. **Press F9** → Red icon appears
2. **Speak** → "echo hello world"
3. **Press F9** → Orange icon while processing
4. **Watch it type** → Text appears exactly where your cursor was

Press ESC anytime to cancel.

## Setup

### Quick Start (Pre-compiled Binary - Recommended)

1. **Install system dependencies:**
```bash
sudo apt install python3-evdev python3-pyaudio python3-yaml python3-gi ydotool portaudio19-dev
sudo usermod -a -G input $USER  # Required for keyboard/ydotool access
# Log out and back in for group change to take effect
```

2. **Set up uinput permissions** (required for ydotool):
```bash
echo 'KERNEL=="uinput", GROUP="input", MODE="0660"' | sudo tee /etc/udev/rules.d/80-uinput.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

3. **Get whisper.cpp:**
   - Download the latest release from [whisper.cpp releases](https://github.com/ggerganov/whisper.cpp/releases)
   - Extract to `./whisper.cpp/` in the verbose directory
   - Make sure the binary is at `./whisper.cpp/build/bin/whisper-cli`

4. **Download a model:**
```bash
cd whisper.cpp
bash models/download-ggml-model.sh base  # or tiny/small/medium/large-v1
cd ..
```

5. **Run it:**
```bash
python3 verbose.py
```

### Alternative: Compile for Better Performance

If pre-compiled binaries don't work or you want CPU-optimized builds:

```bash
# Install build dependencies
sudo apt install cmake build-essential

# Clone and build
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
mkdir build && cd build
cmake ..
make -j$(nproc)
cd ..

# Download model
bash models/download-ggml-model.sh base
cd ..
```

### Auto-start on Login

```bash
./install-service.sh
```

This installs Verbose as a systemd user service. See [Auto-start section](#running-on-startup) for details.

## Multiple Configs Example

```yaml
# configs/coding.yaml - F9 for CLI safety
hotkey: "<f9>"
avoid_newlines: true  # Prevents accidental command execution
dictionary:
  "cloud code": "Claude Code"
  "postgres": "PostgreSQL"

# configs/writing.yaml - F10 for natural text
hotkey: "<f10>"
avoid_newlines: false  # Keeps paragraph breaks
shortcuts:
  "my email": "you@example.com"
```

Each hotkey loads its own config. Press F9 for coding, F10 for emails. Simple.

## Requirements

Ubuntu 22.04+ (or any Linux with evdev and ydotool). ~200MB disk space. That's it.

## Contributing

Contributions welcome! Here's where help is needed:

### Packaging & Distribution
The project currently requires manual installation. I don't know how to package for Linux distributions - if you do, help would be appreciated:
- Snap package
- Flatpak
- AUR (Arch)
- Debian/Ubuntu .deb
- AppImage

Open an issue if you'd like to help with any of these.

### Other Contributions
- Bug fixes and improvements
- Better error handling
- Documentation improvements
- Multi-language support

Read [CLAUDE.md](CLAUDE.md) for architecture details. Keep changes simple and focused.

## Development

Single Python file. ~500 lines. Built with Claude Code.

## License

MIT - Do whatever you want with it.

## Credits

- Built with [whisper.cpp](https://github.com/ggerganov/whisper.cpp) by [@ggerganov](https://github.com/ggerganov)
- Inspired by Talon Voice and Wispr Flow (but free and local)
- Designed with [Claude Code](https://claude.com/claude-code)

## Support

Issues? Check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

Still stuck? [Open an issue](https://github.com/yourusername/verbose/issues).
