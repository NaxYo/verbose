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
from pynput import keyboard
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
        self.audio_frames = []
        self.audio = pyaudio.PyAudio()
        self.stream = None

        # System tray indicator
        self.indicator = AppIndicator3.Indicator.new(
            "verbose",
            "microphone-sensitivity-muted",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.build_menu())

        # Hotkey listener
        self.hotkey = self.parse_hotkey(self.config['hotkey'])
        self.listener = keyboard.GlobalHotKeys({
            self.hotkey: self.toggle_recording
        })

    def load_config(self):
        """Load configuration from config.yaml or use defaults"""
        config_path = Path(__file__).parent / 'config.yaml'
        default_config = {
            'hotkey': '<ctrl>+<alt>+v',
            'whisper_model': 'base',
            'whisper_cpp_path': './whisper.cpp/build/bin/whisper-cli',
            'sample_rate': 16000,
            'channels': 1
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

    def parse_hotkey(self, hotkey_str):
        """Convert hotkey string to pynput format"""
        # Simple parsing - handles <ctrl>+<alt>+key format
        return hotkey_str

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

        # Update indicator to red
        self.indicator.set_icon_full("microphone-sensitivity-high", "")

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

        # Update indicator back to gray
        self.indicator.set_icon_full("microphone-sensitivity-muted", "")

        # Stop audio stream
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

        # Process audio in background thread
        if self.audio_frames:
            threading.Thread(target=self.process_audio, daemon=True).start()

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

                # Insert text at cursor
                self.insert_text(text)

        finally:
            # Clean up temp file
            if os.path.exists(wav_path):
                os.unlink(wav_path)

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
        """Insert text at current cursor position using xdotool"""
        try:
            # Small delay to ensure focus is correct
            subprocess.run(['sleep', '0.1'])

            # Use xdotool to type the text
            subprocess.run(['xdotool', 'type', '--', text])

        except Exception as e:
            print("Text insertion error: " + str(e))

    def run(self):
        """Start the daemon"""
        print("Verbose started. Press " + self.config['hotkey'] + " to toggle recording.")

        # Start hotkey listener
        self.listener.start()

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
        self.listener.stop()
        Gtk.main_quit()


def main():
    """Entry point"""
    daemon = VerboseDaemon()

    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, lambda s, f: daemon.quit())

    daemon.run()


if __name__ == '__main__':
    main()
