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
        self.config = self.load_config()
        self.dictionary = self.load_dictionary()
        self.shortcuts = self.load_shortcuts()
        self.is_recording = False
        self.is_processing = False
        self.audio_frames = []
        self.audio = pyaudio.PyAudio()
        self.stream = None

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
        self.hotkey_code = self.parse_hotkey(self.config['hotkey'])
        self.hotkey_thread = None

    def load_config(self):
        """Load configuration from config.yaml or use defaults"""
        config_path = Path(__file__).parent / 'config.yaml'
        default_config = {
            'hotkey': '<ctrl>+<alt>+v',
            'whisper_model': 'base',
            'whisper_cpp_path': './whisper.cpp/build/bin/whisper-cli',
            'sample_rate': 16000,
            'channels': 1,
            'avoid_newlines': False
        }

        if config_path.exists():
            try:
                with open(config_path) as f:
                    loaded_config = yaml.safe_load(f) or {}
                    # Merge with defaults (defaults override missing keys)
                    return {**default_config, **loaded_config}
            except Exception as e:
                print("Error loading config.yaml, using defaults: " + str(e))

        return default_config

    def load_dictionary(self):
        """Load word corrections from dictionary.yaml"""
        dict_path = Path(__file__).parent / 'dictionary.yaml'
        if dict_path.exists():
            try:
                with open(dict_path) as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                print("Error loading dictionary.yaml, skipping: " + str(e))
        return {}

    def load_shortcuts(self):
        """Load phrase expansions from shortcuts.yaml"""
        shortcuts_path = Path(__file__).parent / 'shortcuts.yaml'
        if shortcuts_path.exists():
            try:
                with open(shortcuts_path) as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                print("Error loading shortcuts.yaml, skipping: " + str(e))
        return {}

    def find_keyboard(self):
        """Find keyboard device using evdev"""
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for device in devices:
            caps = device.capabilities()
            if ecodes.EV_KEY in caps:
                keys = caps[ecodes.EV_KEY]
                # Check if it has letter keys (actual keyboard)
                if ecodes.KEY_A in keys or ecodes.KEY_Q in keys:
                    print("Using keyboard: " + device.name)
                    return device
        print("Warning: No keyboard device found!")
        return None

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

    def toggle_recording(self):
        """Toggle recording on/off"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        """Start recording audio"""
        self.is_recording = True
        self.audio_frames = []

        # Update indicator to recording state (red)
        self.indicator.set_icon_full("recording", "")

        # Start audio stream
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=self.config['channels'],
            rate=self.config['sample_rate'],
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
        """Transcribe audio and insert text"""
        # Save audio to temporary WAV file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            wav_path = f.name

        try:
            wf = wave.open(wav_path, 'wb')
            wf.setnchannels(self.config['channels'])
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.config['sample_rate'])
            wf.writeframes(b''.join(self.audio_frames))
            wf.close()

            # Transcribe with whisper.cpp
            text = self.transcribe(wav_path)

            if text:
                # Apply dictionary corrections (fix misinterpreted words)
                text = self.apply_dictionary(text)

                # Apply shortcuts (expand spoken phrases)
                text = self.apply_shortcuts(text)

                # Remove newlines if configured
                if self.config.get('avoid_newlines', False):
                    text = text.replace('\n', ' ').replace('\r', ' ')

                # Insert text at cursor
                self.insert_text(text)

        finally:
            # Clean up temp file
            if os.path.exists(wav_path):
                os.unlink(wav_path)

            # Return to idle state
            self.is_processing = False
            GLib.idle_add(lambda: self.indicator.set_icon_full("idle", ""))

    def transcribe(self, audio_file):
        """Transcribe audio using whisper.cpp"""
        # Resolve paths relative to this script's location
        script_dir = Path(__file__).parent.resolve()
        whisper_path = Path(self.config['whisper_cpp_path'])

        # If relative path, make it relative to script location
        if not whisper_path.is_absolute():
            whisper_path = (script_dir / whisper_path).resolve()
        else:
            whisper_path = whisper_path.expanduser()

        model = self.config['whisper_model']

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
                timeout=30
            )

            # Read output text file - whisper adds .txt to the input filename
            # So /tmp/abc.wav becomes /tmp/abc.wav.txt
            txt_file = Path(audio_file + '.txt')

            if txt_file.exists():
                text = txt_file.read_text().strip()
                txt_file.unlink()

                # Filter out blank audio markers and empty results
                if text and text not in ['[BLANK_AUDIO]', '']:
                    return text

            return None

        except Exception as e:
            print("Transcription error: " + str(e))
            return None

    def apply_dictionary(self, text):
        """Apply word corrections from dictionary (fix misinterpreted words)"""
        for wrong, correct in self.dictionary.items():
            # Case-insensitive word replacement
            import re
            # Use word boundaries to avoid partial matches
            pattern = re.compile(r'\b' + re.escape(wrong) + r'\b', re.IGNORECASE)
            text = pattern.sub(correct, text)

        return text

    def apply_shortcuts(self, text):
        """Apply phrase expansions from shortcuts"""
        for phrase, replacement in self.shortcuts.items():
            # Case-insensitive phrase replacement
            text = text.replace(phrase, replacement)
            text = text.replace(phrase.lower(), replacement)
            text = text.replace(phrase.capitalize(), replacement)

        return text

    def insert_text(self, text):
        """Insert text using ydotool (works with all applications including terminals)"""
        try:
            # Small delay to ensure focus is correct
            subprocess.run(['sleep', '0.3'])

            # Use ydotool to type text (works at kernel level like evdev)
            subprocess.run(['ydotool', 'type', text], check=True)

        except subprocess.CalledProcessError as e:
            print("Text insertion failed: " + str(e))
        except Exception as e:
            print("Text insertion error: " + str(e))

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
                        if event.code == self.hotkey_code:
                            # Use GLib to call toggle_recording in main thread
                            GLib.idle_add(self.toggle_recording)
        except Exception as e:
            print("Hotkey listener error: " + str(e))

    def run(self):
        """Start the daemon"""
        print("Verbose started. Press " + self.config['hotkey'] + " to toggle recording.")

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
