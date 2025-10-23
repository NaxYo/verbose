# Verbose

**Press a key. Speak. Press again. Text appears.**

Voice-to-text for Linux. 100% local, no subscriptions.

```bash
# Install it
sudo apt install python3-evdev python3-pyaudio python3-yaml python3-gi
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp && mkdir build && cd build && cmake .. && make -j$(nproc) && cd ..
bash ./models/download-ggml-model.sh base && cd ..

# Run it
python3 verbose.py

# Use it
# Press F9, speak "hello world", press F9 again
# Text appears at your cursor
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

**TL;DR**: Install deps, build whisper.cpp, run it.

**Full guide**: [docs/INSTALLATION.md](docs/INSTALLATION.md)

**Troubleshooting**: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

**Configuration**: [docs/CONFIGURATION.md](docs/CONFIGURATION.md)

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
- Inspired by Talon Voice and Whisprflow (but free and local)
- Designed with [Claude Code](https://claude.com/claude-code)

## Support

Issues? Check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

Still stuck? [Open an issue](https://github.com/yourusername/verbose/issues).
