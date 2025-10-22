# Verbose

A simple voice-to-text daemon for Linux. Press a hotkey, speak, press again - text appears where your cursor is.

**Alternative to proprietary dictation tools like Talon, Whisprflow, etc.**

## Features

- ✅ Global hotkey toggle for recording (configurable)
- ✅ System tray indicator with 3 states and customizable icons (gray idle / red recording / orange processing)
- ✅ Local transcription via whisper.cpp (privacy-first, no cloud)
- ✅ Dictionary for word corrections (e.g., "designer" → "Desygner")
- ✅ Shortcuts for phrase expansion (e.g., "my address" → full address)
- ✅ Automatic text insertion at cursor position
- ✅ Works with any application (terminal, browser, IDE, etc.)
- ✅ Minimal dependencies, simple Python implementation

## Setup

1. Install system dependencies:
```bash
# Runtime dependencies
sudo apt install -y portaudio19-dev ydotool gir1.2-appindicator3-0.1

# Build dependencies for whisper.cpp
sudo apt install -y cmake build-essential

# Add your user to the input group (for keyboard/ydotool access)
sudo usermod -a -G input $USER
# Then log out and back in for the group change to take effect
```

2. Install Python 3 dependencies:
```bash
pip3 install -r requirements.txt
```

3. Build whisper.cpp:
```bash
# Clone and build whisper.cpp
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
make
./models/download-ggml-model.sh base  # or tiny/small for faster performance
cd ..
```

4. Create your local config files (optional - defaults work out of the box):
```bash
# Copy sample configs and customize them
cp config.sample.yaml config.yaml
cp dictionary.sample.yaml dictionary.yaml
cp shortcuts.sample.yaml shortcuts.yaml

# Then edit the files to your preferences
```

**Note:** The program works without config files using sensible defaults. Config files are gitignored so you can customize without conflicts.

## Usage

Start the daemon:
```bash
python3 verbose.py
```

You'll see: `Verbose started. Press <ctrl>+<alt>+v to toggle recording.`

### How to use:
1. Press your hotkey (default: **Ctrl+Alt+V**) to start recording
2. **Red microphone icon** appears in system tray (recording)
3. Speak clearly for a few seconds
4. Press the hotkey again to stop
5. **Orange microphone icon** appears (processing transcription)
6. Text automatically appears at your cursor position
7. **Gray microphone icon** returns (idle, ready for next recording)

### Tips:
- Speak for at least 2-3 seconds for best results
- The transcription happens in the background (non-blocking)
- Works in any application: terminal, browser, text editor, etc.
- Uses kernel-level input (evdev + ydotool) - works on both X11 and Wayland

### Running on startup:
Add to your startup applications or create a systemd user service (see CLAUDE.md for details).

**Requirements:** Python 3.6+, input group membership

## Configuration

All configuration is optional - the program works with sensible defaults. To customize:

### config.yaml
Copy from `config.sample.yaml` and edit:
- `hotkey`: Key combination to toggle recording (default: `<ctrl>+<alt>+v`)
- `whisper_model`: Model size - tiny/base/small/medium/large (default: `base`)
- `whisper_cpp_path`: Path to whisper.cpp binary (default: `./whisper.cpp/build/bin/whisper-cli`)
- `sample_rate`: Audio sample rate (default: `16000`)
- `channels`: Audio channels (default: `1`)
- `avoid_newlines`: Strip newlines from output (default: `false`) - useful for CLI tools like Claude Code

### dictionary.yaml
Copy from `dictionary.sample.yaml` to fix words the model commonly misinterprets:
- Format: `"wrong": "correct"`
- Example: `"designer": "Desygner"` (fixes company name)
- Uses word-boundary matching (won't replace partial words)

### shortcuts.yaml
Copy from `shortcuts.sample.yaml` to add phrase expansions:
- Format: `"phrase you say": "text that gets inserted"`
- Example: `"my address": "Unit 3, 123 Main St..."`
- Case-insensitive matching

**Note:** All `.yaml` files are gitignored. Use `.sample.yaml` files as templates.

## Custom Icons

You can customize the system tray icons by replacing the SVG files in the `icons/` folder:
- `idle.svg` - Shown when listening for hotkey
- `recording.svg` - Shown when actively recording
- `processing.svg` - Shown when processing transcription

See `icons/README.md` for icon design guidelines.

## Troubleshooting

### ALSA warnings on startup
These are normal and can be ignored. They're just audio system probing messages.

### No text appears
- Ensure you're in the `input` group: `groups | grep input`
- If not, run `sudo usermod -a -G input $USER` and log out/in
- Make sure you spoke for at least 2-3 seconds
- Check that ydotool is installed: `which ydotool`

### Model not found error
- Run `./models/download-ggml-model.sh base` in the whisper.cpp directory
- Check that `whisper_cpp_path` in config.yaml points to the correct binary

### Transcription returns blank
- Speak louder or check microphone input levels with `alsamixer`
- Try a different microphone if available
- Increase recording time before stopping

## License

MIT License - feel free to modify and distribute.

## Contributing

This is a minimal MVP. Contributions welcome for:
- Better error handling and logging
- Performance optimizations
- Additional text expansion features
- Multi-language support

See CLAUDE.md for development documentation.
