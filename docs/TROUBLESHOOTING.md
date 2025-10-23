# Troubleshooting

## F9 key not working / No keyboard detected

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

## ydotool error: "failed to open uinput device"

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

## ModuleNotFoundError: No module named 'evdev'

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

## Model not found error

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

## ALSA/JACK warnings on startup

**Symptom:**
```
ALSA lib pcm.c:2721:(snd_pcm_open_noupdate) Unknown PCM cards.pcm.side
Cannot connect to server socket err = No such file or directory
jack server is not running or cannot be started
```

**These are harmless** - PyAudio probes for various audio backends. The program works fine regardless.

## No text appears after transcription

**Possible causes:**
1. **Permission issue** - Check `/dev/uinput` permissions (see above)
2. **Short recording** - Speak for at least 2-3 seconds
3. **Microphone issue** - Check levels with `alsamixer`
4. **Blank audio detected** - Whisper filtered it out, try speaking louder

## Transcription returns blank or "[BLANK_AUDIO]"

**Solutions:**
- Speak louder and more clearly
- Check microphone input levels: `alsamixer` (F4 for capture, unmute with M)
- Try a different microphone
- Increase recording time to 3-5 seconds minimum
- Test microphone: `arecord -d 3 test.wav && aplay test.wav`

## System tray icon not showing

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

## Service not starting on boot

**Check service status:**
```bash
systemctl --user status verbose
journalctl --user -u verbose -n 50
```

**Common issues:**
1. Service file not installed - Run `./install-service.sh`
2. Path incorrect in service file - Should use `%h/tools/verbose/verbose.py`
3. Dependencies not met - Check all installation steps completed
