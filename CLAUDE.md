# CLAUDE.md - Development Documentation

## Project Overview

**Verbose** is a minimalist voice-to-text daemon for Linux, built as an open-source alternative to proprietary tools like Whisprflow and Talon Voice.

### Design Philosophy
- **Start small, no over-engineering** - MVP first, features later
- **Privacy-first** - 100% local processing via whisper.cpp, no cloud APIs
- **Minimal dependencies** - Simple Python script, easy to understand and modify
- **Works everywhere** - Any X11 application (terminal, browser, IDE, etc.)

### Project Stats
- **Language**: Python 3.6+
- **Lines of Code**: ~280 (single file implementation)
- **Dependencies**: 4 Python packages, whisper.cpp binary
- **Platform**: Linux (X11, partial Wayland support possible)

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────┐
│              VerboseDaemon (Main)               │
└─────────────────────────────────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
       ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Hotkey    │ │  System     │ │   Audio     │
│  Listener   │ │  Tray       │ │  Recorder   │
│  (pynput)   │ │ (AppInd3)   │ │ (PyAudio)   │
└─────────────┘ └─────────────┘ └─────────────┘
       │               │               │
       └───────────────┼───────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ Process Audio   │
              │ (Background)    │
              └─────────────────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
       ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  Whisper    │ │ Dictionary  │ │  xdotool    │
│ Transcribe  │ │  & Shortcuts│ │ Text Insert │
│ (whisper.cpp)│ │  (YAML)     │ │ (subprocess)│
└─────────────┘ └─────────────┘ └─────────────┘
```

### Data Flow

1. **User presses hotkey** → GlobalHotKeys listener triggers `toggle_recording()`
2. **Recording starts** → PyAudio stream captures microphone input
3. **User presses hotkey again** → Recording stops, audio frames saved
4. **Background processing**:
   - Audio saved to temporary WAV file (16kHz, mono, 16-bit)
   - whisper.cpp subprocess transcribes audio
   - Output read from `.txt` file
5. **Text processing**:
   - Dictionary corrections applied (word-level regex)
   - Shortcuts expanded (phrase-level string replacement)
6. **Text insertion** → xdotool simulates typing at cursor position
7. **Cleanup** → Temporary files deleted

### Key Design Decisions

#### 1. Single-file implementation
**Rationale**: Easier to understand, modify, and distribute. No package structure needed for ~280 lines.

#### 2. Background transcription
**Rationale**: Whisper can take 1-3 seconds. Threading prevents UI blocking.

#### 3. Temporary WAV files
**Rationale**: whisper.cpp expects file input. Could optimize with stdin in future.

#### 4. xdotool for text insertion
**Pros**: Universal, works everywhere on X11
**Cons**: X11 only (Wayland needs ydotool)
**Alternative considered**: Clipboard paste (rejected - overwrites user clipboard)

#### 5. AppIndicator3 for system tray
**Rationale**: Standard Gnome/Ubuntu tray integration. Cross-desktop compatible.

#### 6. Separate dictionary vs shortcuts
**Rationale**: Different use cases:
- **Dictionary**: Fix model errors (word-level, regex boundaries)
- **Shortcuts**: Expand phrases (phrase-level, string replacement)

## File Structure

```
verbose/
├── verbose.py              # Main daemon (~300 lines)
├── config.sample.yaml      # Config template (committed)
├── dictionary.sample.yaml  # Dictionary template (committed)
├── shortcuts.sample.yaml   # Shortcuts template (committed)
├── config.yaml             # User config (gitignored)
├── dictionary.yaml         # User dictionary (gitignored)
├── shortcuts.yaml          # User shortcuts (gitignored)
├── requirements.txt        # Python dependencies
├── .gitignore             # Ignores local configs
├── README.md              # User documentation
└── CLAUDE.md              # This file (dev docs)
```

## Configuration System

### Local Config Pattern
All config files are **optional** and **gitignored**:
- `.sample.yaml` files are committed to the repo as templates
- Users copy `.sample.yaml` → `.yaml` and customize
- Program uses sensible defaults if no config exists
- Prevents merge conflicts on personal settings

**Benefits:**
- ✅ Works out-of-the-box (no config required)
- ✅ Users can customize without git conflicts
- ✅ Sample files document all options
- ✅ Local configs never accidentally committed

### config.yaml
```yaml
hotkey: "<ctrl>+<alt>+v"              # pynput format
whisper_model: "base"                 # tiny/base/small/medium/large
whisper_cpp_path: "./whisper.cpp/..." # Relative or absolute
sample_rate: 16000                    # Whisper expects 16kHz
channels: 1                           # Mono audio
```

### dictionary.yaml (Word corrections)
```yaml
"designer": "Desygner"  # Fix company name
"postgres": "PostgreSQL" # Fix product name
```
- Uses regex word boundaries (`\b`) to avoid partial matches
- Case-insensitive matching

### shortcuts.yaml (Phrase expansions)
```yaml
"my address": "Unit 3, 123 Main Street..."
"my email": "you@example.com"
```
- Simple string replacement
- Case-insensitive (tries lowercase, capitalize variants)

## Dependencies

### Python Packages
1. **pynput** - Global hotkey detection
   - Alternatives considered: keyboard (requires root), python-xlib (complex)
2. **pyaudio** - Audio recording
   - Requires portaudio19-dev system package
3. **pyyaml** - Configuration parsing
4. **PyGObject** - GTK bindings for AppIndicator3
   - System package: gir1.2-appindicator3-0.1

### System Dependencies
1. **whisper.cpp** - Speech-to-text engine
   - Built from source (cmake, make)
   - Models downloaded separately (~150MB for base)
2. **xdotool** - Text insertion
   - Standard in most distros
3. **portaudio** - Audio backend for PyAudio

## Common Issues & Solutions

### Issue: "Model file not found"
**Root cause**: Path calculation error in verbose.py:189-190
**Solution**: Binary path must be `build/bin/whisper-cli`, then `parent.parent.parent` reaches whisper.cpp root

### Issue: "No output file created by whisper"
**Root cause**: whisper.cpp outputs `file.wav.txt` not `file.txt`
**Solution**: Use `Path(audio_file + '.txt')` not `.with_suffix('.txt')`

### Issue: Deprecation warning for AppIndicator3.Indicator.set_icon
**Root cause**: GTK API change
**Solution**: Use `set_icon_full(icon, "")` instead of `set_icon(icon)`

### Issue: f-string syntax error
**Root cause**: Python 2.7 default on some systems
**Solution**: Use `python3` explicitly, avoid f-strings for compatibility

### Issue: ALSA warnings on startup
**Root cause**: PyAudio probes all audio devices
**Solution**: Harmless, can be ignored (or redirect stderr)

## Development Guide

### Adding a new feature

1. **Keep it simple** - This is an MVP, not a full IDE
2. **Update todos** - If multi-step, use TodoWrite for tracking
3. **Test manually** - No test suite (yet), manual testing expected
4. **Document in CLAUDE.md** - For future maintainers

### Code Style
- **No over-engineering** - Prefer simple solutions
- **Single file** - Keep everything in verbose.py unless absolutely necessary
- **Clear comments** - Explain *why*, not *what*
- **Print statements** - Minimal, only for errors/warnings

### Testing Workflow
```bash
# 1. Start daemon
python3 verbose.py

# 2. Press hotkey, speak, press again
# 3. Check if text appears at cursor

# 4. Check logs for errors
# (stdout has minimal output in production)
```

## Future Enhancements (Not Implemented)

### Wayland Support
Replace xdotool with ydotool:
```python
subprocess.run(['ydotool', 'type', text])
```
Requires ydotool service running.

### Deepgram Remote API (Fallback)
Original plan included Deepgram API as alternative to whisper.cpp:
```python
def transcribe_deepgram(audio_file):
    with open(audio_file, 'rb') as f:
        response = requests.post(
            'https://api.deepgram.com/v1/listen',
            headers={'Authorization': 'Token YOUR_KEY'},
            data=f
        )
    return response.json()['results']['channels'][0]['alternatives'][0]['transcript']
```
**Not implemented** - Local-first approach preferred.

### Systemd User Service
Create `~/.config/systemd/user/verbose.service`:
```ini
[Unit]
Description=Verbose voice-to-text daemon

[Service]
ExecStart=/usr/bin/python3 /home/user/tools/verbose/verbose.py
Restart=always

[Install]
WantedBy=default.target
```

Enable:
```bash
systemctl --user enable verbose.service
systemctl --user start verbose.service
```

### Logging System
Add proper logging instead of print statements:
```python
import logging
logging.basicConfig(
    filename='/tmp/verbose.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

### Model Selection UI
Add system tray menu to switch models on-the-fly without editing config.yaml.

### Audio Visualization
Show waveform or volume meter in system tray during recording.

## Build & Release Process

### Creating a Release
1. Clean up debug code (remove print statements)
2. Update version in verbose.py and README
3. Test on fresh Ubuntu/Debian VM
4. Create GitHub release with:
   - Source tarball
   - Pre-compiled whisper.cpp binary (optional)
   - Installation script (future enhancement)

### Packaging (Future)
- **Debian package**: `.deb` with dependencies
- **Snap/Flatpak**: Sandboxed installation
- **AUR package**: For Arch Linux users

## Performance Notes

### Transcription Speed
- **Tiny model**: ~500ms for 3-second audio
- **Base model**: ~1.5s for 3-second audio
- **Small model**: ~3s for 3-second audio

Trade-off: Speed vs accuracy. Base model is sweet spot for most users.

### Memory Usage
- **Python daemon**: ~50MB
- **Whisper base model**: ~150MB (loaded on first transcription)
- **Total**: ~200MB resident

### CPU Usage
- **Idle**: <1% (just hotkey listener)
- **Recording**: ~5% (audio stream)
- **Transcribing**: 100% of 1 core for 1-3 seconds (whisper.cpp)

## Security Considerations

### Microphone Access
- Only records when user presses hotkey (visual indicator)
- No background recording
- Audio files immediately deleted after transcription

### File System
- Temporary files in `/tmp` (world-readable on most systems)
- Future enhancement: Use `tempfile.mkstemp(dir='/run/user/$UID/')`

### Network
- Zero network access (100% local)
- No telemetry, no phone-home

## Known Limitations

1. **X11 only** - xdotool doesn't work on Wayland (ydotool needed)
2. **English-focused** - Whisper supports many languages, but dictionary/shortcuts are English-centric
3. **No punctuation commands** - Can't say "comma" to insert ","
4. **No editing commands** - Can't say "delete last word"
5. **Single microphone** - No device selection UI

## Contributing Guidelines

### What we're looking for:
- ✅ Bug fixes
- ✅ Performance improvements
- ✅ Better error handling
- ✅ Wayland support
- ✅ Documentation improvements

### What we're NOT looking for:
- ❌ Heavy frameworks (no Electron, no Qt)
- ❌ Feature creep (keep it simple)
- ❌ Cloud dependencies
- ❌ Paid API integrations (unless optional)

### Pull Request Process:
1. Test on Ubuntu 22.04+ and Fedora 38+
2. Update README.md and CLAUDE.md
3. Keep changes minimal and focused
4. Explain "why" in commit messages

## Technical Debt

### Current shortcuts taken for MVP:
1. **No logging system** - Using print() for now
2. **Hardcoded audio format** - Should be configurable
3. **No error recovery** - Crashes on whisper.cpp failure
4. **No model auto-download** - User must manually run script
5. **String concatenation for paths** - Should use pathlib consistently

### Refactoring opportunities:
1. Split into modules (audio, transcription, text_processing, ui)
2. Add type hints (Python 3.6+ compatible)
3. Add docstrings to all methods
4. Create proper config validation
5. Add unit tests for dictionary/shortcuts logic

## License

MIT License - See LICENSE file (to be created)

## Credits

- **whisper.cpp**: Georgi Gerganov (@ggerganov)
- **OpenAI Whisper**: Original model by OpenAI
- **Inspiration**: Talon Voice, Whisprflow (proprietary alternatives)

## Changelog

### v0.1.0 (2025-10-22) - Initial MVP
- Global hotkey toggle
- System tray indicator
- whisper.cpp integration
- Dictionary word corrections
- Phrase shortcuts
- xdotool text insertion
- YAML configuration

---

**Maintained by**: @nax
**Status**: MVP - Production ready for personal use
**Support**: GitHub Issues only (no official support)
