#!/usr/bin/env python3
"""
Verbose - Simple voice-to-text daemon for Linux
"""

import os
import sys
import yaml
import wave
import tempfile
import subprocess
import threading
import signal
from pathlib import Path

import pyaudio
import evdev
from evdev import ecodes
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GLib


class VerboseDaemon:
    """Main daemon for voice-to-text recording and transcription"""

    def __init__(self):
        self.configs = self.load_configs()  # Dict of config_name -> config_data
        self.is_recording = False
        self.is_processing = False
        self.is_cancelled = False
        self.active_config_name = None  # Track which config triggered recording
        self.audio_frames = []
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.typing_process = None  # Track ydotool process for cancellation

        # Icon paths (relative to script directory)
        script_dir = Path(__file__).parent
        self.icon_dir = str(script_dir / "icons")
        self.ICON_IDLE = str(script_dir / "icons" / "idle")
        self.ICON_RECORDING = str(script_dir / "icons" / "recording")
        self.ICON_PROCESSING = str(script_dir / "icons" / "processing")

        # System tray indicator - use icon theme path
        self.indicator = AppIndicator3.Indicator.new(
            "verbose",
            "idle",  # Just the name, not full path
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_icon_theme_path(self.icon_dir)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.build_menu())

        # Find keyboard device for evdev
        self.keyboard_device = self.find_keyboard()

        # Build hotkey map: hotkey_code -> config_name
        self.hotkey_map = {}
        for config_name, config_data in self.configs.items():
            hotkey_code = self.parse_hotkey(config_data['hotkey'])
            if hotkey_code in self.hotkey_map:
                # Duplicate hotkey detected
                self.show_notification(
                    "Verbose Configuration Error",
                    "Duplicate hotkey '{}' in configs '{}' and '{}'. Skipping '{}'.".format(
                        config_data['hotkey'],
                        self.hotkey_map[hotkey_code],
                        config_name,
                        config_name
                    )
                )
                print("Warning: Duplicate hotkey '{}' in configs '{}' and '{}'. Skipping '{}'.".format(
                    config_data['hotkey'],
                    self.hotkey_map[hotkey_code],
                    config_name,
                    config_name
                ))
            else:
                self.hotkey_map[hotkey_code] = config_name

        self.hotkey_thread = None

    def load_configs(self):
        """Load all configuration files from configs/ directory"""
        configs_dir = Path(__file__).parent / 'configs'
        configs = {}

        # Default config values
        default_config = {
            'hotkey': '<f9>',
            'whisper_model': 'base',
            'whisper_cpp_path': './whisper.cpp/build/bin/whisper-cli',
            'sample_rate': 16000,
            'channels': 1,
            'avoid_newlines': False,
            'whisper_timeout': 300,  # 5 minutes for long recordings
            'debug_keep_temp_files': False,  # Keep temp files on failure for debugging
            'dictionary': {},
            'shortcuts': {}
        }

        # If configs directory doesn't exist, create it with a default config
        if not configs_dir.exists():
            print("configs/ directory not found, creating with default config...")
            configs_dir.mkdir()
            configs['default'] = default_config
            return configs

        # Load all .yaml files from configs/
        yaml_files = list(configs_dir.glob('*.yaml'))

        # Filter out sample.yaml
        yaml_files = [f for f in yaml_files if f.stem != 'sample']

        if not yaml_files:
            print("No config files found in configs/, using defaults")
            configs['default'] = default_config
            return configs

        for config_file in yaml_files:
            config_name = config_file.stem  # Filename without extension
            try:
                with open(config_file) as f:
                    loaded_config = yaml.safe_load(f) or {}

                    # Extract dictionary and shortcuts
                    dictionary = loaded_config.pop('dictionary', {})
                    shortcuts = loaded_config.pop('shortcuts', {})

                    # Merge with defaults
                    final_config = {**default_config, **loaded_config}
                    final_config['dictionary'] = dictionary
                    final_config['shortcuts'] = shortcuts

                    configs[config_name] = final_config
                    print("Loaded config '{}' with hotkey '{}'".format(
                        config_name, final_config['hotkey']
                    ))
            except Exception as e:
                print("Error loading {}: {}".format(config_file, str(e)))

        if not configs:
            print("No valid configs loaded, using defaults")
            configs['default'] = default_config

        return configs

    def find_keyboard(self):
        """Find keyboard device using evdev"""
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        keyboards = []

        for device in devices:
            caps = device.capabilities()
            if ecodes.EV_KEY in caps:
                keys = caps[ecodes.EV_KEY]
                # Check for function keys and letter keys
                has_f_keys = any(k in keys for k in [ecodes.KEY_F1, ecodes.KEY_F9, ecodes.KEY_F10])
                has_letters = ecodes.KEY_A in keys or ecodes.KEY_Q in keys
                has_numbers = ecodes.KEY_1 in keys or ecodes.KEY_2 in keys

                # Check if it has letter keys AND function keys or numbers (actual keyboard)
                if has_letters and (has_f_keys or has_numbers):
                    keyboards.append(device)

        if not keyboards:
            print("Warning: No keyboard device found!")
            return None

        # Sort keyboards - prefer ones with "keyboard" or "kbd" in the name, avoid "mouse" and "gaming"
        def keyboard_priority(device):
            name_lower = device.name.lower()
            # Exclude devices with "mouse" in the name
            if 'mouse' in name_lower or 'gaming' in name_lower:
                return 999  # Low priority
            # Prefer devices with "keyboard" or "kbd" in the name
            if 'keyboard' in name_lower or 'kbd' in name_lower:
                return 0  # High priority
            return 100  # Medium priority

        keyboards.sort(key=keyboard_priority)
        print("Using keyboard: " + keyboards[0].name)
        return keyboards[0]

    def parse_hotkey(self, hotkey_str):
        """Convert hotkey string like '<f9>' or '<alt>+<space>' to evdev key code"""
        # Map common key names to evdev codes
        key_map = {
            'f1': ecodes.KEY_F1, 'f2': ecodes.KEY_F2, 'f3': ecodes.KEY_F3,
            'f4': ecodes.KEY_F4, 'f5': ecodes.KEY_F5, 'f6': ecodes.KEY_F6,
            'f7': ecodes.KEY_F7, 'f8': ecodes.KEY_F8, 'f9': ecodes.KEY_F9,
            'f10': ecodes.KEY_F10, 'f11': ecodes.KEY_F11, 'f12': ecodes.KEY_F12,
            'space': ecodes.KEY_SPACE, 'enter': ecodes.KEY_ENTER,
            'tab': ecodes.KEY_TAB, 'esc': ecodes.KEY_ESC,
            'caps_lock': ecodes.KEY_CAPSLOCK, 'scroll_lock': ecodes.KEY_SCROLLLOCK,
            'pause': ecodes.KEY_PAUSE, 'print_screen': ecodes.KEY_SYSRQ,
            'ctrl': ecodes.KEY_LEFTCTRL, 'alt': ecodes.KEY_LEFTALT,
            'shift': ecodes.KEY_LEFTSHIFT, 'cmd': ecodes.KEY_LEFTMETA,
        }

        # Parse simple format: <key> or <mod>+<key>
        parts = hotkey_str.replace('<', '').replace('>', '').lower().split('+')

        if len(parts) == 1:
            # Single key
            key_name = parts[0]
            return key_map.get(key_name, ecodes.KEY_F9)  # Default to F9
        else:
            # For now, just return the last key (the trigger key)
            # TODO: Handle modifier keys properly
            key_name = parts[-1]
            return key_map.get(key_name, ecodes.KEY_F9)

    def build_menu(self):
        """Build system tray menu"""
        menu = Gtk.Menu()

        item_quit = Gtk.MenuItem(label='Quit Verbose')
        item_quit.connect('activate', self.quit)
        menu.append(item_quit)

        menu.show_all()
        return menu

    def show_notification(self, title, message):
        """Show desktop notification using notify-send"""
        try:
            subprocess.run(['notify-send', title, message], check=False)
        except Exception as e:
            print("Failed to show notification: " + str(e))

    def toggle_recording(self, config_name):
        """Toggle recording on/off using the specified config"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording(config_name)

    def cancel_operation(self):
        """Cancel current operation (recording, processing, or typing)"""
        self.is_cancelled = True

        # If currently recording, stop it
        if self.is_recording:
            self.is_recording = False
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            self.audio_frames = []

        # If currently typing, kill the ydotool process
        if self.typing_process:
            try:
                self.typing_process.kill()
                self.typing_process.wait(timeout=1)
            except:
                pass
            self.typing_process = None

        # Return to idle state (processing will finish in background but result will be ignored)
        self.is_processing = False
        self.indicator.set_icon_full("idle", "")

    def start_recording(self, config_name):
        """Start recording audio using the specified config"""
        self.active_config_name = config_name
        self.is_recording = True
        self.is_cancelled = False  # Reset cancel flag when starting new recording
        self.audio_frames = []

        # Update indicator to recording state (red)
        self.indicator.set_icon_full("recording", "")

        # Get active config
        config = self.configs[config_name]

        # Start audio stream
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=config['channels'],
            rate=config['sample_rate'],
            input=True,
            frames_per_buffer=1024,
            stream_callback=self.audio_callback
        )
        self.stream.start_stream()

    def audio_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio stream"""
        if self.is_recording:
            self.audio_frames.append(in_data)
        return (in_data, pyaudio.paContinue)

    def stop_recording(self):
        """Stop recording and process audio"""
        self.is_recording = False

        # Stop audio stream
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

        # Process audio in background thread
        if self.audio_frames:
            # Update indicator to processing state (orange)
            self.is_processing = True
            self.indicator.set_icon_full("processing", "")
            threading.Thread(target=self.process_audio, daemon=True).start()
        else:
            # No audio recorded, go back to idle
            self.indicator.set_icon_full("idle", "")

    def process_audio(self):
        """Transcribe audio and insert text using the active config"""
        # Check if cancelled before starting
        if self.is_cancelled:
            self.is_processing = False
            return

        # Get the active config
        config = self.configs[self.active_config_name]

        # Save audio to temporary WAV file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            wav_path = f.name

        try:
            wf = wave.open(wav_path, 'wb')
            wf.setnchannels(config['channels'])
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(config['sample_rate'])
            wf.writeframes(b''.join(self.audio_frames))
            wf.close()

            # Check if cancelled before transcribing
            if self.is_cancelled:
                return

            # Transcribe with whisper.cpp
            text = self.transcribe(wav_path, config)

            # Check if cancelled after transcription
            if self.is_cancelled or not text:
                # Keep temp file if debug mode is enabled and transcription failed
                if config.get('debug_keep_temp_files', False) and not text:
                    debug_path = '/tmp/verbose_debug_{}.wav'.format(os.path.basename(wav_path))
                    import shutil
                    shutil.copy(wav_path, debug_path)
                    msg = "Transcription failed. Audio saved to: " + debug_path
                    print(msg)
                    GLib.idle_add(self.show_notification, "Verbose Debug", msg)
                return

            # Apply dictionary corrections (fix misinterpreted words)
            text = self.apply_dictionary(text, config)

            # Apply shortcuts (expand spoken phrases)
            text = self.apply_shortcuts(text, config)

            # Clean up newlines and spacing
            import re

            if config.get('avoid_newlines', False):
                # Replace all newlines with spaces, then collapse multiple spaces
                text = text.replace('\n', ' ').replace('\r', ' ')
                text = re.sub(r' +', ' ', text)
            else:
                # Keep newlines only after sentence-ending punctuation (. ! ?)
                # Replace other newlines with spaces
                # First, normalize newlines
                text = text.replace('\r\n', '\n').replace('\r', '\n')

                # Replace newlines that don't follow sentence-ending punctuation with spaces
                # Keep newlines that follow . ! ? (with optional quotes/brackets)
                text = re.sub(r'(?<![.!?])\n', ' ', text)

                # Clean up: strip spaces from each line and collapse multiple spaces
                text = '\n'.join(line.strip() for line in text.split('\n'))
                text = re.sub(r' +', ' ', text)

            # Check if cancelled before inserting text
            if self.is_cancelled:
                return

            # Insert text at cursor
            self.insert_text(text)

        finally:
            # Clean up temp file
            if os.path.exists(wav_path):
                os.unlink(wav_path)

            # Return to idle state (only if not already cancelled)
            if not self.is_cancelled:
                self.is_processing = False
                GLib.idle_add(lambda: self.indicator.set_icon_full("idle", ""))

    def transcribe(self, audio_file, config):
        """Transcribe audio using whisper.cpp with the specified config"""
        # Resolve paths relative to this script's location
        script_dir = Path(__file__).parent.resolve()
        whisper_path = Path(config['whisper_cpp_path'])

        # If relative path, make it relative to script location
        if not whisper_path.is_absolute():
            whisper_path = (script_dir / whisper_path).resolve()
        else:
            whisper_path = whisper_path.expanduser()

        model = config['whisper_model']

        # Determine model path (go up to whisper.cpp root: build/bin/main -> build/bin -> build -> whisper.cpp)
        model_dir = whisper_path.parent.parent.parent / 'models'
        model_file = model_dir / ('ggml-' + model + '.bin')

        if not model_file.exists():
            print("Warning: Model file not found at " + str(model_file))
            return None

        try:
            result = subprocess.run(
                [
                    str(whisper_path),
                    '-m', str(model_file),
                    '--output-txt',
                    audio_file
                ],
                capture_output=True,
                text=True,
                timeout=config.get('whisper_timeout', 300)
            )

            # Read output text file - whisper adds .txt to the input filename
            # So /tmp/abc.wav becomes /tmp/abc.wav.txt
            txt_file = Path(audio_file + '.txt')

            if txt_file.exists():
                text = txt_file.read_text().strip()
                txt_file.unlink()

                # Remove [BLANK_AUDIO] markers (can appear at end of transcription)
                text = text.replace('[BLANK_AUDIO]', '').strip()

                # Return text if not empty after filtering
                if text:
                    return text

            return None

        except subprocess.TimeoutExpired:
            error_msg = "Whisper transcription timed out after {}s. Your recording may be too long. Increase whisper_timeout in config.".format(config.get('whisper_timeout', 300))
            print(error_msg)
            GLib.idle_add(self.show_notification, "Verbose Transcription Timeout", error_msg)
            return None
        except Exception as e:
            error_msg = "Transcription error: " + str(e)
            print(error_msg)
            GLib.idle_add(self.show_notification, "Verbose Transcription Failed", error_msg)
            return None

    def apply_dictionary(self, text, config):
        """Apply word corrections from dictionary (fix misinterpreted words)"""
        import re
        for wrong, correct in config['dictionary'].items():
            # Case-insensitive word replacement
            # Use word boundaries to avoid partial matches
            pattern = re.compile(r'\b' + re.escape(wrong) + r'\b', re.IGNORECASE)
            text = pattern.sub(correct, text)

        return text

    def apply_shortcuts(self, text, config):
        """Apply phrase expansions from shortcuts"""
        for phrase, replacement in config['shortcuts'].items():
            # Case-insensitive phrase replacement
            text = text.replace(phrase, replacement)
            text = text.replace(phrase.lower(), replacement)
            text = text.replace(phrase.capitalize(), replacement)

        return text

    def insert_text(self, text):
        """Insert text using ydotool (works with all applications including terminals)"""
        try:
            # Use ydotool to type text (works at kernel level like evdev)
            # Store process so it can be killed if cancelled
            # Use --key-delay 5 for faster typing (default is 12ms, 5ms is a good balance)
            self.typing_process = subprocess.Popen(['ydotool', 'type', '--key-delay', '5', text])
            self.typing_process.wait()
            self.typing_process = None

        except subprocess.CalledProcessError as e:
            print("Text insertion failed: " + str(e))
            self.typing_process = None
        except Exception as e:
            print("Text insertion error: " + str(e))
            self.typing_process = None

    def listen_for_hotkey(self):
        """Background thread to listen for hotkey presses using evdev"""
        if not self.keyboard_device:
            return

        try:
            for event in self.keyboard_device.read_loop():
                if event.type == ecodes.EV_KEY:
                    key_event = evdev.categorize(event)
                    # Only trigger on key press (not release)
                    if key_event.keystate == evdev.KeyEvent.key_down:
                        # Check if this key code matches any configured hotkey
                        if event.code in self.hotkey_map:
                            config_name = self.hotkey_map[event.code]
                            # Use GLib to call toggle_recording in main thread
                            GLib.idle_add(self.toggle_recording, config_name)
                        elif event.code == ecodes.KEY_ESC:
                            # Escape key cancels current operation
                            GLib.idle_add(self.cancel_operation)
        except Exception as e:
            print("Hotkey listener error: " + str(e))

    def run(self):
        """Start the daemon"""
        print("Verbose started with {} configuration(s):".format(len(self.configs)))
        for config_name, config_data in self.configs.items():
            print("  - '{}': {}".format(config_name, config_data['hotkey']))

        # Start hotkey listener in background thread
        self.hotkey_thread = threading.Thread(target=self.listen_for_hotkey, daemon=True)
        self.hotkey_thread.start()

        # Run GTK main loop
        try:
            Gtk.main()
        except KeyboardInterrupt:
            self.quit()

    def quit(self, *args):
        """Clean shutdown"""
        print("\nShutting down...")

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

        self.audio.terminate()

        if self.keyboard_device:
            self.keyboard_device.close()

        Gtk.main_quit()


def main():
    """Entry point"""
    daemon = VerboseDaemon()

    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, lambda s, f: daemon.quit())

    daemon.run()


if __name__ == '__main__':
    main()
