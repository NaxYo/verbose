# Installation Guide

Follow these steps in order for a smooth installation.

## Step 1: Install System Dependencies

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

## Step 2: Configure Permissions

Two permission fixes are required for keyboard capture and text insertion:

### Add user to input group (for keyboard capture via evdev)
```bash
sudo usermod -a -G input $USER
```

### Create udev rule for uinput (for text insertion via ydotool)
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

### Verify permissions after logging back in
```bash
# Should show "input" in the list
groups

# Should show group "input" with 0660 permissions
ls -l /dev/uinput
```

## Step 3: Build whisper.cpp

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

## Step 4: Test the Installation

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

## Step 5: (Optional) Install as System Service

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

## Step 6: (Optional) Create Custom Configurations

Verbose supports multiple configurations with different hotkeys. All configuration is optional - defaults work out of the box.

```bash
# Create your first config (e.g., for coding)
cp configs/sample.yaml configs/coding.yaml
nano configs/coding.yaml  # Set hotkey to <f9>, enable avoid_newlines, add coding dictionary

# Create a second config (e.g., for writing)
cp configs/sample.yaml configs/writing.yaml
nano configs/writing.yaml  # Set hotkey to <f10>, add personal shortcuts
```

**Important:**
- Each config MUST have a unique hotkey
- If duplicate hotkeys are detected, you'll get a desktop notification
- Config files in `configs/` are gitignored (except `sample.yaml`)
- All sections within each config are optional

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.
