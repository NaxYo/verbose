# Verbose

A simple voice-to-text daemon for Linux. Press a hotkey, speak, press again - text appears where your cursor is.

**Alternative to proprietary dictation tools like Talon, Whisprflow, etc.**

## Features

- ✅ Global hotkey toggle for recording (configurable)
- ✅ System tray indicator (gray idle / red recording)
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
sudo apt install -y portaudio19-dev xdotool gir1.2-appindicator3-0.1

# Build dependencies for whisper.cpp
sudo apt install -y cmake build-essential
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
2. **Red microphone icon** appears in system tray
3. Speak clearly for a few seconds
4. Press the hotkey again to stop
5. Text automatically appears at your cursor position

### Tips:
- Speak for at least 2-3 seconds for best results
- The transcription happens in the background (non-blocking)
- Works in any application: terminal, browser, text editor, etc.
- Use X11 (xdotool) - Wayland support may vary

### Running on startup:
Add to your startup applications or create a systemd user service (see CLAUDE.md for details).

**Requirements:** Python 3.6+, X11 (for xdotool text insertion)

## Configuration

All configuration is optional - the program works with sensible defaults. To customize:

### config.yaml
Copy from `config.sample.yaml` and edit:
- `hotkey`: Key combination to toggle recording (default: `<ctrl>+<alt>+v`)
- `whisper_model`: Model size - tiny/base/small/medium/large (default: `base`)
- `whisper_cpp_path`: Path to whisper.cpp binary (default: `./whisper.cpp/build/bin/whisper-cli`)
- `sample_rate`: Audio sample rate (default: `16000`)
- `channels`: Audio channels (default: `1`)

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

## Troubleshooting

### ALSA warnings on startup
These are normal and can be ignored. They're just audio system probing messages.

### No text appears
- Ensure you're using X11 (check with `echo $XDG_SESSION_TYPE`)
- For Wayland, try using `ydotool` instead of `xdotool` (requires code modification)
- Make sure you spoke for at least 2-3 seconds

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
- Wayland support (ydotool integration)
- Better error handling and logging
- Performance optimizations
- Additional text expansion features

See CLAUDE.md for development documentation.
