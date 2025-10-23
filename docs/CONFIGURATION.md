# Configuration Guide

Verbose supports **multiple configurations** with different hotkeys. This allows you to have separate setups for different use cases (e.g., coding vs. writing).

## Quick Start

```bash
# Create a config for coding/prompting
cp configs/sample.yaml configs/coding.yaml
# Edit: set hotkey to <f9>, enable avoid_newlines, add tech terms to dictionary

# Create a config for writing/emails
cp configs/sample.yaml configs/writing.yaml
# Edit: set hotkey to <f10>, add personal shortcuts
```

## How Multiple Configs Work

- Put `.yaml` files in the `configs/` directory
- Each config file becomes a separate configuration
- Each config MUST have a unique hotkey
- Press the hotkey to record using that config's settings
- Any hotkey can stop recording, but transcription uses the starting config

**Example:**
- Press **F9** (coding config) → transcription strips newlines, uses coding dictionary
- Press **F10** (writing config) → transcription keeps newlines, uses personal shortcuts

## Configuration Options

All sections within each config are **completely optional**. Include only what you need.

### Main Settings
- `hotkey`: **REQUIRED** - Must be unique per config (e.g., `<f9>`, `<f10>`)
- `whisper_model`: Model size - tiny/base/small/medium/large (default: `base`)
- `whisper_cpp_path`: Path to whisper.cpp binary (default: `./whisper.cpp/build/bin/whisper-cli`)
- `sample_rate`: Audio sample rate (default: `16000`)
- `channels`: Audio channels (default: `1`)
- `avoid_newlines`: Strip newlines from output (default: `false`) - useful for CLI tools

### Dictionary (Word Corrections)
Fix words the model commonly misinterprets:
```yaml
dictionary:
  "cloud code": "Claude Code"
  "postgres": "PostgreSQL"
```
- Uses word-boundary matching (won't replace partial words)
- Entire section is optional

### Shortcuts (Phrase Expansions)
Expand spoken phrases to longer text:
```yaml
shortcuts:
  "my email": "you@example.com"
  "my address": "Unit 3, 123 Main St..."
```
- Case-insensitive matching
- Entire section is optional

## Example Configs

### Minimal config (just hotkey and one setting)
```yaml
# configs/simple.yaml
hotkey: "<f11>"
avoid_newlines: true
```

### Full config (all options)
```yaml
# configs/complete.yaml
hotkey: "<f9>"
whisper_model: "base"
avoid_newlines: true

dictionary:
  "cloud code": "Claude Code"

shortcuts:
  "my email": "you@example.com"
```

## Custom Icons

You can customize the system tray icons by replacing the SVG files in the `icons/` folder:
- `idle.svg` - Shown when listening for hotkey
- `recording.svg` - Shown when actively recording
- `processing.svg` - Shown when processing transcription

See `icons/README.md` for icon design guidelines.

## Notes

- Config files in `configs/` are gitignored (except `sample.yaml`)
- Duplicate hotkeys trigger a desktop notification
- If no configs exist, Verbose uses default settings with F9 hotkey
