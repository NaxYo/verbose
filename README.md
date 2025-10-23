# Verbose

A simple voice-to-text daemon for Linux. Press a hotkey, speak, press again - text appears where your cursor is.

**Alternative to proprietary dictation tools like Talon, Whisprflow, etc.**

## Features

- ✅ Global hotkey toggle for recording (configurable)
- ✅ Escape key to cancel at any time (recording, processing, or typing)
- ✅ System tray indicator with 3 states and customizable icons (gray idle / red recording / orange processing)
- ✅ Local transcription via whisper.cpp (privacy-first, no cloud)
- ✅ Dictionary for word corrections (e.g., "cloud code" → "Claude Code")
- ✅ Shortcuts for phrase expansion (e.g., "my address" → full address)
- ✅ Automatic text insertion at cursor position
- ✅ Works with any application (terminal, browser, IDE, etc.)
- ✅ Minimal dependencies, simple Python implementation

## Installation

Follow these steps in order for a smooth installation:

### Step 1: Install System Dependencies

```bash
# Install all required packages
sudo apt update
sudo apt install -y \
    python3-evdev \
    python3-pyaudio \
    python3-yaml \
    python3-gi \
    gir1.2-gtk-3.0 \
    gir1.2-appindicator3-0.1 \
    portaudio19-dev \
    ydotool \
    cmake \
    build-essential \
    git
```

**Why system packages?** Modern Ubuntu (22.04+) blocks `pip install` by default (PEP 668). Using system packages avoids this issue entirely.

### Step 2: Configure Permissions

Two permission fixes are required for keyboard capture and text insertion:

#### Add user to input group (for keyboard capture via evdev)
```bash
sudo usermod -a -G input $USER
```

#### Create udev rule for uinput (for text insertion via ydotool)
```bash
# Create the udev rule
echo 'KERNEL=="uinput", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"' | sudo tee /etc/udev/rules.d/99-uinput.rules

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Load uinput kernel module
sudo modprobe uinput
```

**Important:** After these steps, **log out and log back in** for the group membership to take effect.

#### Verify permissions after logging back in
```bash
# Should show "input" in the list
groups

# Should show group "input" with 0660 permissions
ls -l /dev/uinput
```

### Step 3: Build whisper.cpp

```bash
# Clone whisper.cpp repository
git clone https://github.com/ggerganov/whisper.cpp.git

# Build with cmake
cd whisper.cpp
mkdir -p build
cd build
cmake ..
make -j$(nproc)
cd ../..

# Download the base model (~142MB)
cd whisper.cpp
bash ./models/download-ggml-model.sh base
cd ..

# Verify installation
ls -lh whisper.cpp/build/bin/whisper-cli
ls -lh whisper.cpp/models/ggml-base.bin
```

**Model options:**
- `tiny` - Fastest, least accurate (~75MB)
- `base` - **Recommended** - Good balance (~142MB)
- `small` - More accurate, slower (~466MB)

### Step 4: Test the Installation

```bash
python3 verbose.py
```

You should see:
```
Using keyboard: [Your Keyboard Name]
Verbose started. Press <f9> to toggle recording.
```

**Test the workflow:**
1. Press **F9** (system tray icon turns red)
2. Speak for 3-5 seconds
3. Press **F9** again (icon turns orange while processing)
4. Text should appear at your cursor position

**Press ESC** at any time to cancel.

### Step 5: (Optional) Install as System Service

To automatically start Verbose when you log in:

```bash
./install-service.sh
```

**Service management:**
```bash
systemctl --user status verbose     # Check status
systemctl --user stop verbose       # Stop service
systemctl --user restart verbose    # Restart service
systemctl --user disable verbose    # Disable auto-start
journalctl --user -u verbose -f     # View logs
```

To uninstall the service:
```bash
./uninstall-service.sh
```

### Step 6: (Optional) Customize Configuration

All configuration is optional - defaults work out of the box.

```bash
# Copy the sample config
cp config.sample.yaml config.yaml

# Edit to your preferences
nano config.yaml
```

**Note:**
- The config file is gitignored, so your customizations won't conflict with updates
- All sections (hotkey, whisper_model, dictionary, shortcuts, etc.) are optional
- You can include only the parts you want to customize

## Usage

Start the daemon:
```bash
python3 verbose.py
```

You'll see: `Verbose started. Press <f9> to toggle recording.`

### How to use:
1. Press your hotkey (default: **F9**) to start recording
2. **Red microphone icon** appears in system tray (recording)
3. Speak clearly for a few seconds
4. Press the hotkey again to stop
5. **Orange microphone icon** appears (processing transcription)
6. Text automatically appears at your cursor position
7. **Gray microphone icon** returns (idle, ready for next recording)

**Pro tip:** Press **Escape** at any time to cancel the current operation (recording, processing, or typing) and return to idle state.

### Tips:
- Speak for at least 2-3 seconds for best results
- The transcription happens in the background (non-blocking)
- Works in any application: terminal, browser, text editor, etc.
- Uses kernel-level input (evdev + ydotool) - works on both X11 and Wayland

### Running on startup:

To automatically start Verbose when you log in, run the installation script:

```bash
./install-service.sh
```

This installs Verbose as a systemd user service. Useful commands:
- `systemctl --user status verbose` - Check status
- `systemctl --user stop verbose` - Stop service
- `systemctl --user restart verbose` - Restart service
- `systemctl --user disable verbose` - Disable auto-start
- `journalctl --user -u verbose -f` - View logs

To uninstall:
```bash
./uninstall-service.sh
```

**Requirements:** Python 3.6+, input group membership

## Configuration

All configuration is optional - the program works with sensible defaults. Everything is configured through a single `config.yaml` file.

### Quick Start

```bash
# Copy the sample config
cp config.sample.yaml config.yaml

# Edit only the sections you want to customize
nano config.yaml
```

### Configuration Sections

All sections are **completely optional**. Include only what you want to customize.

#### Main Settings
- `hotkey`: Key combination to toggle recording (default: `<f9>`)
- `whisper_model`: Model size - tiny/base/small/medium/large (default: `base`)
- `whisper_cpp_path`: Path to whisper.cpp binary (default: `./whisper.cpp/build/bin/whisper-cli`)
- `sample_rate`: Audio sample rate (default: `16000`)
- `channels`: Audio channels (default: `1`)
- `avoid_newlines`: Strip newlines from output (default: `false`) - useful for CLI tools like Claude Code

#### Dictionary (Word Corrections)
Fix words the model commonly misinterprets:
```yaml
dictionary:
  "cloud code": "Claude Code"
  "postgres": "PostgreSQL"
```
- Uses word-boundary matching (won't replace partial words)
- Entire section is optional

#### Shortcuts (Phrase Expansions)
Expand spoken phrases to longer text:
```yaml
shortcuts:
  "my email": "you@example.com"
  "my address": "Unit 3, 123 Main St..."
```
- Case-insensitive matching
- Entire section is optional

### Example Minimal Config

You can have a config with just one field:
```yaml
hotkey: "<ctrl>+<alt>+v"
```

Or just dictionary:
```yaml
dictionary:
  "cloud code": "Claude Code"
```

**Note:** The config file is gitignored, so your customizations won't conflict with updates.

## Custom Icons

You can customize the system tray icons by replacing the SVG files in the `icons/` folder:
- `idle.svg` - Shown when listening for hotkey
- `recording.svg` - Shown when actively recording
- `processing.svg` - Shown when processing transcription

See `icons/README.md` for icon design guidelines.

## Troubleshooting

### F9 key not working / No keyboard detected

**Symptom:** Pressing F9 does nothing, or you see "Warning: No keyboard device found!"

**Causes:**
1. Not in the `input` group
2. Gaming mouse or other device detected as keyboard instead

**Solutions:**
```bash
# 1. Verify you're in the input group
groups | grep input

# If not, add yourself and log out/in
sudo usermod -a -G input $USER

# 2. Run the debug script to see which keyboard is detected
python3 debug-evdev.py
```

The script shows all devices and which one is selected. If a mouse is selected instead of your keyboard, this is a bug - please report it with the device names shown.

### ydotool error: "failed to open uinput device"

**Symptom:**
```
terminate called after throwing an instance of 'std::runtime_error'
  what():  failed to open uinput device
```

**Cause:** `/dev/uinput` doesn't have proper permissions

**Solution:**
```bash
# Create udev rule (from Step 2 of installation)
echo 'KERNEL=="uinput", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"' | sudo tee /etc/udev/rules.d/99-uinput.rules

# Reload udev and load module
sudo udevadm control --reload-rules
sudo udevadm trigger
sudo modprobe uinput

# Verify permissions
ls -l /dev/uinput
# Should show: crw-rw---- 1 root input ...
```

**Note:** You do NOT need to run `ydotoold` daemon. Modern ydotool works without it.

### ModuleNotFoundError: No module named 'evdev'

**Symptom:** `ModuleNotFoundError: No module named 'evdev'` when running verbose.py

**Cause:** Python dependencies not installed

**Solution:**
```bash
# Use system packages (recommended for Ubuntu 22.04+)
sudo apt install -y python3-evdev python3-pyaudio python3-yaml python3-gi

# Alternative: Use pip in a virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Model not found error

**Symptom:** `Warning: Model file not found at /home/.../whisper.cpp/models/ggml-base.bin`

**Cause:** whisper.cpp model not downloaded

**Solution:**
```bash
cd whisper.cpp
bash ./models/download-ggml-model.sh base
cd ..

# Verify
ls -lh whisper.cpp/models/ggml-base.bin
```

### ALSA/JACK warnings on startup

**Symptom:**
```
ALSA lib pcm.c:2721:(snd_pcm_open_noupdate) Unknown PCM cards.pcm.side
Cannot connect to server socket err = No such file or directory
jack server is not running or cannot be started
```

**These are harmless** - PyAudio probes for various audio backends. The program works fine regardless.

### No text appears after transcription

**Possible causes:**
1. **Permission issue** - Check `/dev/uinput` permissions (see above)
2. **Short recording** - Speak for at least 2-3 seconds
3. **Microphone issue** - Check levels with `alsamixer`
4. **Blank audio detected** - Whisper filtered it out, try speaking louder

### Transcription returns blank or "[BLANK_AUDIO]"

**Solutions:**
- Speak louder and more clearly
- Check microphone input levels: `alsamixer` (F4 for capture, unmute with M)
- Try a different microphone
- Increase recording time to 3-5 seconds minimum
- Test microphone: `arecord -d 3 test.wav && aplay test.wav`

### System tray icon not showing

**Possible causes:**
1. System tray extension not enabled (GNOME)
2. AppIndicator support missing

**Solutions:**
```bash
# Install AppIndicator if missing
sudo apt install gir1.2-appindicator3-0.1

# For GNOME, install AppIndicator extension
# Use GNOME Extensions app or visit: https://extensions.gnome.org/
```

### Service not starting on boot

**Check service status:**
```bash
systemctl --user status verbose
journalctl --user -u verbose -n 50
```

**Common issues:**
1. Service file not installed - Run `./install-service.sh`
2. Path incorrect in service file - Should use `%h/tools/verbose/verbose.py`
3. Dependencies not met - Check all installation steps completed

## License

MIT License - feel free to modify and distribute.

## Contributing

This is a minimal MVP. Contributions welcome for:
- Better error handling and logging
- Performance optimizations
- Additional text expansion features
- Multi-language support

See CLAUDE.md for development documentation.
